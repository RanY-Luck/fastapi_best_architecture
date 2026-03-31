#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API测试用例管理接口
"""
import json
from typing import Any, Dict, Optional
from datetime import datetime
from fastapi import APIRouter, Path, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from backend.common.response.response_schema import response_base, ResponseModel, ResponseSchemaModel
from backend.plugin.api_testing.service.test_case_service import TestCaseService
from backend.plugin.api_testing.service.test_case_execution_service import TestCaseExecutionService
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
        return response_base.success(data=await TestCaseExecutionService.execute_test_case(case_id, environment_id))
    except Exception as e:
        log.error(f"执行测试用例失败: {e}")
        import traceback
        log.error(traceback.format_exc())
        return response_base.fail(data=f"执行测试用例失败: {str(e)}")


@router.post("/{case_id}/execute/stream", summary="流式执行测试用例", response_model=None)
async def execute_test_case_stream(
        case_id: int = Path(..., description="测试用例ID"),
        environment_id: Optional[int] = Query(None, description="环境ID")
) -> StreamingResponse | ResponseSchemaModel:
    """流式返回测试执行事件。"""
    async def _event_generator():
        try:
            async for event in TestCaseExecutionService.stream_test_case_execution(case_id, environment_id):
                payload = json.dumps(make_serializable(event), ensure_ascii=False)
                yield f"{payload}\n".encode()
        except Exception as e:
            log.error(f"流式执行测试用例失败: {e}")
            error_event = {
                "type": "error",
                "timestamp": datetime.now().isoformat(),
                "case_id": case_id,
                "environment_id": environment_id,
                "message": str(e),
                "error_type": type(e).__name__,
            }
            yield f"{json.dumps(error_event, ensure_ascii=False)}\n".encode()

    try:
        return StreamingResponse(
            _event_generator(),
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    except Exception as e:
        log.error(f"流式执行测试用例失败: {e}")
        import traceback
        log.error(traceback.format_exc())
        return response_base.fail(data=f"流式执行测试用例失败: {str(e)}")


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
