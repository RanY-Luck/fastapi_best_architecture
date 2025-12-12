#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API测试用例管理接口
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Path, Query
from fastapi.responses import HTMLResponse
from backend.common.response.response_schema import response_base, ResponseModel, ResponseSchemaModel
from backend.plugin.api_testing.service.test_case_service import TestCaseService
from backend.plugin.api_testing.schema.request import (
    TestCaseCreateRequest, TestCaseUpdateRequest, TestCaseResponse
)
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
        total = await TestCaseService.get_test_case_count(name=name, status=status)

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
    from backend.plugin.api_testing.service.test_step_service import TestStepService
    from backend.plugin.api_testing.service.test_report_service import TestReportService
    from backend.plugin.api_testing.service.project_service import ProjectService
    from backend.plugin.api_testing.utils.http_client import send_request, RequestOptions
    from backend.plugin.api_testing.utils.assertion import AssertionEngine, Assertion
    from backend.plugin.api_testing.utils.sql_executor import SQLExecutor, SQLQuery
    from backend.plugin.api_testing.utils.report_generator import TestReport, StepResult
    from backend.plugin.api_testing.schema.request import TestReportCreateRequest
    from jsonpath_ng import parse

    try:
        # 1. 获取测试用例
        test_case = await TestCaseService.get_test_case_by_id(case_id)
        if not test_case:
            return response_base.fail(data=f"测试用例不存在: {case_id}")

        # 2. 获取项目信息
        project = await ProjectService.get_project_by_id(test_case.project_id)
        if not project:
            return response_base.fail(data=f"项目不存在: {test_case.project_id}")

        # 3. 获取测试步骤
        test_steps = await TestStepService.get_test_steps(
            test_case_id=case_id,
            status=1,
            limit=1000
        )

        if not test_steps:
            return response_base.fail(data="测试用例没有可执行的测试步骤")

        test_steps = sorted(test_steps, key=lambda x: x.order)

        # 4. 初始化
        report_name = f"{test_case.name}_执行报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        step_results = []
        variables = {}

        total_steps = len(test_steps)
        success_steps = 0
        fail_steps = 0

        # 5. 执行每个测试步骤
        for step in test_steps:
            step_start_time = datetime.now()
            step_success = True

            try:
                # 构建URL
                url = step.url
                if not url.startswith('http'):
                    base_url = project.base_url.rstrip('/')
                    url = f"{base_url}{url}" if url.startswith('/') else f"{base_url}/{url}"

                # 合并请求头
                headers = {}
                if project.headers:
                    headers.update(project.headers)
                if step.headers:
                    headers.update(step.headers)

                # 请求选项
                request_options = RequestOptions(
                    timeout=step.timeout,
                    retry_count=step.retry,
                    retry_interval=step.retry_interval
                )

                # 发送请求
                response = await send_request(
                    method=step.method,
                    url=url,
                    params=step.params,
                    headers=headers,
                    json_data=step.body,
                    options=request_options
                )

                # 构建数据
                request_data = {
                    "url": url,
                    "method": step.method,
                    "headers": headers,
                    "params": step.params or {},
                    "json_data": step.body
                }

                response_data = {
                    "status_code": response.status_code,
                    "headers": response.headers,
                    "json": response.json_data,
                    "text": response.text,
                    "elapsed_time": response.elapsed_time
                }

                # 执行断言
                assertions = []
                if step.validate:
                    for assertion_dict in step.validate:
                        assertion = Assertion(**assertion_dict)
                        result = AssertionEngine.execute_assertion(assertion, response_data)
                        assertions.append(result.model_dump())
                        if not result.success:
                            step_success = False

                # 执行SQL
                sql_results = []
                if step.sql_queries:
                    for sql_dict in step.sql_queries:
                        sql_query = SQLQuery(**sql_dict)
                        sql_result = await SQLExecutor.execute_query(sql_query)
                        sql_results.append(sql_result.model_dump())
                        if not sql_result.success:
                            step_success = False
                        if sql_result.extracted_variables:
                            variables.update(sql_result.extracted_variables)

                # 提取变量
                step_variables = {}
                if step.extract and response.json_data:
                    for var_name, json_path in step.extract.items():
                        try:
                            jsonpath_expr = parse(json_path)
                            matches = [match.value for match in jsonpath_expr.find(response.json_data)]
                            if matches:
                                value = matches[0] if len(matches) == 1 else matches
                                variables[var_name] = value
                                step_variables[var_name] = value
                        except Exception as e:
                            log.error(f"提取变量 {var_name} 失败: {e}")

                if response.error:
                    step_success = False

            except Exception as e:
                step_success = False
                log.error(f"执行测试步骤失败: {e}")

                request_data = {"url": url if 'url' in locals() else step.url, "method": step.method}
                response_data = {"status_code": 0, "error": str(e)}
                assertions = []
                sql_results = []
                step_variables = {}

            # 记录步骤结果
            step_end_time = datetime.now()
            step_duration = int((step_end_time - step_start_time).total_seconds() * 1000)

            step_result = StepResult(
                name=step.name,
                order=step.order,
                url=url if 'url' in locals() else step.url,
                method=step.method,
                request_data=request_data,
                response=response_data,
                assertions=assertions,
                sql_results=sql_results if sql_results else None,
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

        # 6. 生成报告
        end_time = datetime.now()
        duration = int((end_time - start_time).total_seconds() * 1000)

        # 7. 保存到数据库（序列化处理）
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
                "environment": {"variables": make_serializable(variables)}
            }
        )

        saved_report = await TestReportService.create_test_report(report_create_request)

        # 8. 返回结果
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
                "end_time": end_time.isoformat()
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
