#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API测试用例管理接口
"""
from typing import Any, Dict, Optional
from datetime import datetime
from fastapi import APIRouter, Path, Query
from fastapi.responses import HTMLResponse
from backend.common.response.response_schema import response_base, ResponseModel, ResponseSchemaModel
from backend.plugin.api_testing.service.test_case_service import TestCaseService
from backend.plugin.api_testing.service.project_service import ProjectService
from backend.plugin.api_testing.service.test_step_service import TestStepService
from backend.plugin.api_testing.service.test_report_service import TestReportService
from backend.plugin.api_testing.schema.request import (
    TestCaseCreateRequest,
    TestCaseUpdateRequest,
    TestCaseResponse,
    TestReportCreateRequest,
)
from backend.plugin.api_testing.utils.environment import EnvironmentManager, VariableManager
from backend.plugin.api_testing.utils.http_client import send_request, RequestOptions
from backend.plugin.api_testing.utils.assertion import AssertionEngine, Assertion
from backend.plugin.api_testing.utils.sql_executor import SQLExecutor, SQLQuery
from backend.plugin.api_testing.utils.report_generator import StepResult
from backend.common.log import log

router = APIRouter()


def make_serializable(obj):
    """递归转换对象为可JSON序列化的格式"""
    if obj is None:
        return None
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_serializable(item) for item in obj]
    elif hasattr(obj, 'model_dump'):
        return make_serializable(obj.model_dump())
    else:
        return obj


async def resolve_execution_environment(project_id: int, environment_id: Optional[int]):
    """解析执行环境，优先使用显式环境，其次回退到默认环境。"""
    if environment_id is not None:
        return await EnvironmentManager.get_environment(environment_id)
    return await EnvironmentManager.get_default_environment(project_id)


def normalize_step_validations(step) -> list[dict[str, Any]]:
    """统一测试步骤中的断言字段。"""
    validations = getattr(step, 'validate', None)
    if validations is None:
        validations = getattr(step, 'validations', None)
    return validations or []


def build_runtime_variables(
        project,
        environment,
        extracted_variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """合并项目、环境和运行时提取变量。"""
    runtime_variables: dict[str, Any] = {}
    if project and project.variables:
        runtime_variables.update(project.variables)
    if environment and environment.variables:
        runtime_variables.update(environment.variables)
    if extracted_variables:
        runtime_variables.update(extracted_variables)
    return runtime_variables


async def process_step_value(value: Any, *, project_id: int, environment_id: Optional[int], case_id: int,
                             temp_variables: dict[str, Any]) -> Any:
    """递归处理步骤中的模板变量。"""
    if isinstance(value, str):
        return await VariableManager.process_template(
            value,
            project_id=project_id,
            environment_id=environment_id,
            case_id=case_id,
            temp_variables=temp_variables,
        )
    if isinstance(value, dict):
        return await VariableManager.process_template_dict(
            value,
            project_id=project_id,
            environment_id=environment_id,
            case_id=case_id,
            temp_variables=temp_variables,
        )
    if isinstance(value, list):
        return await VariableManager.process_template_list(
            value,
            project_id=project_id,
            environment_id=environment_id,
            case_id=case_id,
            temp_variables=temp_variables,
        )
    return value


@router.post("", response_model=ResponseModel, summary="创建测试用例")
async def create_test_case(case_data: TestCaseCreateRequest) -> ResponseModel | ResponseSchemaModel:
    """创建测试用例"""
    try:
        test_case = await TestCaseService.create_test_case(case_data)
        case_response = TestCaseResponse(
            id=test_case.id,
            name=test_case.name,
            project_id=test_case.project_id,
            description=test_case.description,
            pre_script=test_case.pre_script,
            post_script=test_case.post_script,
            status=test_case.status,
            created_time=test_case.created_time.isoformat() if test_case.created_time else "",
            updated_time=test_case.updated_time.isoformat() if test_case.updated_time else ""
        )
        return response_base.success(data=case_response.model_dump())
    except Exception as e:
        return response_base.fail(data=f"创建测试用例失败: {str(e)}")


@router.get("/{case_id}", response_model=ResponseModel, summary="获取测试用例详情")
async def get_test_case(case_id: int = Path(..., description="用例ID")) -> ResponseModel | ResponseSchemaModel:
    """根据ID获取测试用例详情"""
    try:
        test_case = await TestCaseService.get_test_case_by_id(case_id)
        if not test_case:
            return response_base.fail(data="测试用例不存在")

        case_response = TestCaseResponse(
            id=test_case.id,
            name=test_case.name,
            project_id=test_case.project_id,
            description=test_case.description,
            pre_script=test_case.pre_script,
            post_script=test_case.post_script,
            status=test_case.status,
            created_time=test_case.created_time.isoformat() if test_case.created_time else "",
            updated_time=test_case.updated_time.isoformat() if test_case.updated_time else ""
        )
        return response_base.success(data=case_response.model_dump())
    except Exception as e:
        return response_base.fail(data=f"获取测试用例失败: {str(e)}")


@router.get("", response_model=ResponseModel, summary="获取测试用例列表")
async def get_test_cases(
        project_id: Optional[int] = Query(None, description="项目ID"),
        status: Optional[int] = Query(None, description="状态"),
        name: Optional[str] = Query(None, description="用例名称"),
        skip: int = Query(0, description="跳过数量"),
        limit: int = Query(20, description="限制数量")
) -> ResponseModel | ResponseSchemaModel:
    """获取测试用例列表"""
    try:
        test_cases = await TestCaseService.get_test_cases(
            project_id=project_id,
            name=name,
            status=status,
            skip=skip,
            limit=limit
        )
        total = await TestCaseService.get_test_case_count(project_id=project_id, name=name, status=status)

        case_list = []
        for test_case in test_cases:
            project_name = test_case.project.name if test_case.project else None
            case_response = TestCaseResponse(
                id=test_case.id,
                name=test_case.name,
                project_id=test_case.project_id,
                project_name=project_name,
                description=test_case.description,
                pre_script=test_case.pre_script,
                post_script=test_case.post_script,
                status=test_case.status,
                created_time=test_case.created_time.isoformat() if test_case.created_time else "",
                updated_time=test_case.updated_time.isoformat() if test_case.updated_time else ""
            )
            case_list.append(case_response.model_dump())

        return response_base.success(
            data={
                "items": case_list,
                "total": total,
                "skip": skip,
                "limit": limit,
                "project_id": project_id
            }
        )
    except Exception as e:
        return response_base.fail(data=f"获取测试用例列表失败: {str(e)}")


@router.put("/{case_id}", response_model=ResponseModel, summary="更新测试用例")
async def update_test_case(
        case_data: TestCaseUpdateRequest,
        case_id: int = Path(..., description="用例ID")
) -> ResponseModel | ResponseSchemaModel:
    """更新测试用例"""
    try:
        test_case = await TestCaseService.update_test_case(case_id, case_data)
        if not test_case:
            return response_base.fail(data="测试用例不存在")

        case_response = TestCaseResponse(
            id=test_case.id,
            name=test_case.name,
            project_id=test_case.project_id,
            description=test_case.description,
            pre_script=test_case.pre_script,
            post_script=test_case.post_script,
            status=test_case.status,
            created_time=test_case.created_time.isoformat() if test_case.created_time else "",
            updated_time=test_case.updated_time.isoformat() if test_case.updated_time else ""
        )
        return response_base.success(data=case_response.model_dump())
    except Exception as e:
        return response_base.fail(data=f"更新测试用例失败: {str(e)}")


@router.delete("/{case_id}", response_model=ResponseModel, summary="删除测试用例")
async def delete_test_case(case_id: int = Path(..., description="用例ID")) -> ResponseModel | ResponseSchemaModel:
    """删除测试用例"""
    try:
        success = await TestCaseService.delete_test_case(case_id)
        if not success:
            return response_base.fail(data="测试用例不存在或删除失败")

        return response_base.success(data="测试用例删除成功")
    except Exception as e:
        return response_base.fail(data=f"删除测试用例失败: {str(e)}")


# ==================== 测试用例执行功能 ====================

@router.post("/{case_id}/execute", response_model=ResponseModel, summary="执行测试用例")
async def execute_test_case(
        case_id: int = Path(..., description="测试用例ID"),
        environment_id: Optional[int] = Query(None, description="环境ID")
) -> ResponseModel | ResponseSchemaModel:
    """执行测试用例并生成报告"""
    try:
        test_case = await TestCaseService.get_test_case_by_id(case_id)
        if not test_case:
            return response_base.fail(data=f"测试用例不存在: {case_id}")

        project = await ProjectService.get_project_by_id(test_case.project_id)
        if not project:
            return response_base.fail(data=f"项目不存在: {test_case.project_id}")

        environment = await resolve_execution_environment(project.id, environment_id)
        if environment_id is not None and not environment:
            return response_base.fail(data=f"环境不存在: {environment_id}")

        test_steps = await TestStepService.get_test_steps(
            test_case_id=case_id,
            status=1,
            limit=1000
        )
        if not test_steps:
            return response_base.fail(data="测试用例没有可执行的测试步骤")

        test_steps = sorted(test_steps, key=lambda x: x.order)
        resolved_environment_id = environment.id if environment else None
        base_runtime_variables = build_runtime_variables(project, environment)
        runtime_base_url = environment.variables.get("base_url") if environment and environment.variables else None
        base_url = (runtime_base_url or project.base_url or "").rstrip('/')
        base_headers: Dict[str, Any] = {}
        if project.headers:
            base_headers.update(project.headers)
        if environment and isinstance(environment.variables, dict):
            env_headers = environment.variables.get("headers")
            if isinstance(env_headers, dict):
                base_headers.update(env_headers)

        report_name = f"{test_case.name}_执行报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        step_results = []
        extracted_variables: Dict[str, Any] = {}
        total_steps = len(test_steps)
        success_steps = 0
        fail_steps = 0

        for step in test_steps:
            step_start_time = datetime.now()
            step_success = True
            step_assertions = []
            step_sql_results = []
            step_variables: Dict[str, Any] = {}
            runtime_variables = build_runtime_variables(project, environment, extracted_variables)
            current_base_url = await process_step_value(
                base_url,
                project_id=project.id,
                environment_id=resolved_environment_id,
                case_id=case_id,
                temp_variables=runtime_variables,
            )
            request_url = step.url
            request_data = {"url": step.url, "method": step.method}
            response_data = {"status_code": 0, "error": None}

            try:
                processed_url = await process_step_value(
                    step.url,
                    project_id=project.id,
                    environment_id=resolved_environment_id,
                    case_id=case_id,
                    temp_variables=runtime_variables,
                )
                if processed_url.startswith('http'):
                    request_url = processed_url
                else:
                    normalized_base_url = (current_base_url or "").rstrip('/')
                    request_url = (
                        f"{normalized_base_url}{processed_url}"
                        if processed_url.startswith('/')
                        else f"{normalized_base_url}/{processed_url}"
                    )

                headers = await process_step_value(
                    {**base_headers, **(step.headers or {})},
                    project_id=project.id,
                    environment_id=resolved_environment_id,
                    case_id=case_id,
                    temp_variables=runtime_variables,
                )
                params = await process_step_value(
                    step.params or {},
                    project_id=project.id,
                    environment_id=resolved_environment_id,
                    case_id=case_id,
                    temp_variables=runtime_variables,
                )
                body = await process_step_value(
                    step.body,
                    project_id=project.id,
                    environment_id=resolved_environment_id,
                    case_id=case_id,
                    temp_variables=runtime_variables,
                )

                request_options = RequestOptions(
                    timeout=step.timeout,
                    retry_count=step.retry,
                    retry_interval=step.retry_interval
                )

                response = await send_request(
                    method=step.method,
                    url=request_url,
                    params=params,
                    headers=headers,
                    json_data=body,
                    options=request_options
                )

                request_data = {
                    "url": request_url,
                    "method": step.method,
                    "headers": headers,
                    "params": params,
                    "json_data": body
                }
                response_data = {
                    "status_code": response.status_code,
                    "headers": response.headers,
                    "cookies": response.cookies,
                    "json": response.json_data,
                    "body": response.text,
                    "text": response.text,
                    "elapsed_time": response.elapsed_time,
                    "error": response.error,
                }

                for assertion_dict in normalize_step_validations(step):
                    assertion = Assertion(**assertion_dict)
                    result = AssertionEngine.execute_assertion(assertion, response_data)
                    step_assertions.append(result.model_dump())
                    if not result.success:
                        step_success = False

                if step.sql_queries:
                    for sql_dict in step.sql_queries:
                        sql_payload = await process_step_value(
                            sql_dict,
                            project_id=project.id,
                            environment_id=resolved_environment_id,
                            case_id=case_id,
                            temp_variables=runtime_variables,
                        )
                        sql_query = SQLQuery(**sql_payload)
                        sql_result = await SQLExecutor.execute_query(sql_query)
                        step_sql_results.append(sql_result.model_dump())
                        if not sql_result.success:
                            step_success = False
                        if sql_result.extracted_variables:
                            extracted_variables.update(sql_result.extracted_variables)
                            step_variables.update(sql_result.extracted_variables)
                            runtime_variables.update(sql_result.extracted_variables)

                if step.extract and response.json_data:
                    for var_name, json_path in step.extract.items():
                        try:
                            from jsonpath_ng import parse
                            jsonpath_expr = parse(json_path)
                            matches = [match.value for match in jsonpath_expr.find(response.json_data)]
                            if matches:
                                value = matches[0] if len(matches) == 1 else matches
                                extracted_variables[var_name] = value
                                step_variables[var_name] = value
                                runtime_variables[var_name] = value
                        except Exception as e:
                            log.error(f"提取变量 {var_name} 失败: {e}")
                            step_success = False

                if response.error:
                    step_success = False

            except Exception as e:
                step_success = False
                log.error(f"执行测试步骤失败: {e}")
                request_data = {"url": request_url, "method": step.method}
                response_data = {"status_code": 0, "error": str(e)}

            step_end_time = datetime.now()
            step_duration = int((step_end_time - step_start_time).total_seconds() * 1000)
            step_result = StepResult(
                name=step.name,
                order=step.order,
                url=request_url,
                method=step.method,
                request_data=request_data,
                response=response_data,
                assertions=step_assertions,
                sql_results=step_sql_results if step_sql_results else None,
                variables=step_variables if step_variables else None,
                success=step_success,
                start_time=step_start_time,
                end_time=step_end_time,
                duration=step_duration
            )
            step_results.append(step_result)

            if step_success:
                success_steps += 1
            else:
                fail_steps += 1

        end_time = datetime.now()
        duration = int((end_time - start_time).total_seconds() * 1000)
        serializable_steps = [make_serializable(step.model_dump()) for step in step_results]
        report_create_request = TestReportCreateRequest(
            test_case_id=case_id,
            name=report_name,
            success=fail_steps == 0,
            total_steps=total_steps,
            success_steps=success_steps,
            fail_steps=fail_steps,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            details={
                "steps": serializable_steps,
                "environment": {
                    "id": resolved_environment_id,
                    "name": environment.name if environment else None,
                    "base_url": current_base_url if 'current_base_url' in locals() else base_url,
                    "variables": make_serializable(build_runtime_variables(project, environment, extracted_variables)),
                }
            }
        )
        saved_report = await TestReportService.create_test_report(report_create_request)

        return response_base.success(
            data={
                "report_id": saved_report.id,
                "report_name": report_name,
                "success": fail_steps == 0,
                "total_steps": total_steps,
                "success_steps": success_steps,
                "fail_steps": fail_steps,
                "duration": duration,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "environment_id": resolved_environment_id,
                "environment_name": environment.name if environment else None,
            }
        )

    except Exception as e:
        log.error(f"执行测试用例失败: {e}")
        import traceback
        log.error(traceback.format_exc())
        return response_base.fail(data=f"执行测试用例失败: {str(e)}")


@router.get("/{case_id}/execute/preview", summary="执行并预览HTML报告")
async def execute_and_preview_report(
        case_id: int = Path(..., description="测试用例ID"),
        environment_id: Optional[int] = Query(None, description="环境ID")
):
    """执行测试用例并直接返回HTML格式报告"""
    from backend.plugin.api_testing.service.test_report_service import TestReportService
    from backend.plugin.api_testing.utils.report_generator import report_generator, ReportFormat, TestReport

    try:
        # 执行测试用例
        result = await execute_test_case(case_id, environment_id)

        if not result.success:
            error_html = f"""
            <html><body>
                <h1>测试执行失败</h1>
                <p>错误信息: {result.data}</p>
            </body></html>
            """
            return HTMLResponse(content=error_html, status_code=500)

        # 获取报告
        report_id = result.data.get("report_id")
        saved_report = await TestReportService.get_test_report_by_id(report_id)

        if not saved_report:
            return HTMLResponse(content="<html><body><h1>报告不存在</h1></body></html>", status_code=404)

        # 获取项目和测试用例信息
        test_case = await TestCaseService.get_test_case_by_id(case_id)
        from backend.plugin.api_testing.service.project_service import ProjectService
        project = await ProjectService.get_project_by_id(test_case.project_id)

        # 构建报告对象
        test_report = TestReport(
            name=saved_report.name,
            project_name=project.name,
            test_case_name=test_case.name,
            description=test_case.description,
            environment=None,
            success=saved_report.success == 1,
            total_steps=saved_report.total_steps,
            success_steps=int(saved_report.success_steps),
            fail_steps=int(saved_report.fail_steps),
            steps=saved_report.details.get("steps", []),
            start_time=saved_report.start_time,
            end_time=saved_report.end_time,
            duration=saved_report.duration
        )

        # 生成HTML
        html_content = report_generator.generate_report(test_report, ReportFormat.HTML)
        return HTMLResponse(content=html_content)

    except Exception as e:
        log.error(f"执行并预览报告失败: {e}")
        import traceback
        log.error(traceback.format_exc())
        error_html = f"""
        <html><body>
            <h1>测试执行失败</h1>
            <p>错误信息: {str(e)}</p>
            <pre>{traceback.format_exc()}</pre>
        </body></html>
        """
        return HTMLResponse(content=error_html, status_code=500)
