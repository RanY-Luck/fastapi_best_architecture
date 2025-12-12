#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time     : 2025/12/12 11:01
# @Author   : 冉勇
# @File     : request_engine.py
# @Software : PyCharm
# @Desc     : API测试用例执行接口
from typing import Optional
from datetime import datetime
from backend.common.log import log
from fastapi import APIRouter, Path, Query
from starlette.responses import HTMLResponse
from backend.common.response.response_schema import response_base, ResponseModel, ResponseSchemaModel
from backend.plugin.api_testing.schema.request import RequestEngine
from backend.plugin.api_testing.service.test_case_service import TestCaseService
from backend.plugin.api_testing.service.test_step_service import TestStepService
from backend.plugin.api_testing.service.test_report_service import TestReportService
from backend.plugin.api_testing.service.project_service import ProjectService
from backend.plugin.api_testing.utils.report_generator import TestReport, StepResult
from backend.plugin.api_testing.schema.request import TestReportCreateRequest

router = APIRouter()


@router.post("/{case_id}/execute", response_model=ResponseModel, summary="执行测试用例")
async def execute_test_case(
        case_id: int = Path(..., description="测试用例ID"),
        environment_id: Optional[int] = Query(None, description="环境ID")
) -> ResponseModel | ResponseSchemaModel:
    """
    执行测试用例并生成报告

    执行流程：
    1. 获取测试用例和所有测试步骤
    2. 按顺序执行每个测试步骤
    3. 收集执行结果
    4. 生成并保存测试报告
    """

    try:
        # 1. 获取测试用例
        test_case = await TestCaseService.get_test_case_by_id(case_id)
        if not test_case:
            return response_base.fail(data=f"测试用例不存在: {case_id}")

        # 2. 获取项目信息
        project = await ProjectService.get_project_by_id(test_case.project_id)
        if not project:
            return response_base.fail(data=f"项目不存在: {test_case.project_id}")

        # 3. 获取测试步骤（按order排序）
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
            execution_result = await RequestEngine.execute_step(
                step=step,
                base_url=project.base_url,
                global_headers=project.headers,
                variables=variables
            )

            # 转换为StepResult
            step_result = StepResult(
                name=step.name,
                order=step.order,
                url=execution_result.request_data.get('url', step.url),
                method=step.method,
                request_data=execution_result.request_data,
                response=execution_result.response_data,
                assertions=execution_result.assertions,
                sql_results=execution_result.sql_results if execution_result.sql_results else None,
                variables=execution_result.extracted_variables if execution_result.extracted_variables else None,
                success=execution_result.success,
                start_time=execution_result.start_time,
                end_time=execution_result.end_time,
                duration=execution_result.duration
            )

            step_results.append(step_result)

            if execution_result.success:
                success_steps += 1
            else:
                fail_steps += 1

        # 6. 生成测试报告
        end_time = datetime.now()
        duration = int((end_time - start_time).total_seconds() * 1000)

        test_report = TestReport(
            name=report_name,
            project_name=project.name,
            test_case_name=test_case.name,
            description=test_case.description,
            environment=None,
            success=fail_steps == 0,
            total_steps=total_steps,
            success_steps=success_steps,
            fail_steps=fail_steps,
            steps=step_results,
            start_time=start_time,
            end_time=end_time,
            duration=duration
        )

        # 7. 保存测试报告到数据库
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
                "steps": [step.model_dump() for step in step_results],
                "environment": {"variables": variables}
            }
        )

        saved_report = await TestReportService.create_test_report(report_create_request)

        # 8. 返回执行结果
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
        return response_base.fail(data=f"执行测试用例失败: {str(e)}")


@router.get("/{case_id}/execute/preview", summary="执行测试用例并预览HTML报告")
async def execute_and_preview_report(
        case_id: int = Path(..., description="测试用例ID"),
        environment_id: Optional[int] = Query(None, description="环境ID")
):
    """
    执行测试用例并直接返回HTML格式的测试报告用于预览
    """
    from backend.plugin.api_testing.utils.report_generator import report_generator, ReportFormat, TestReport
    from backend.common.log import log

    try:
        # 执行测试用例
        result = await execute_test_case(case_id, environment_id)

        if not result.success:
            error_html = f"""
            <html>
                <body>
                    <h1>测试执行失败</h1>
                    <p>错误信息: {result.data}</p>
                </body>
            </html>
            """
            return HTMLResponse(content=error_html, status_code=500)

        # 获取测试报告ID并从数据库读取完整报告
        from backend.plugin.api_testing.service.test_report_service import TestReportService
        report_id = result.data.get("report_id")
        saved_report = await TestReportService.get_test_report_by_id(report_id)

        if not saved_report:
            return HTMLResponse(content="<html><body><h1>报告不存在</h1></body></html>", status_code=404)

        # 构建TestReport对象
        test_report_data = {
            "name": saved_report.name,
            "project_name": result.data.get("test_case_name", "未知项目"),
            "test_case_name": result.data.get("test_case_name", "未知用例"),
            "description": None,
            "environment": None,
            "success": saved_report.success,
            "total_steps": saved_report.total_steps,
            "success_steps": saved_report.success_steps,
            "fail_steps": saved_report.fail_steps,
            "steps": saved_report.details.get("steps", []),
            "start_time": saved_report.start_time,
            "end_time": saved_report.end_time,
            "duration": saved_report.duration
        }

        test_report = TestReport(**test_report_data)

        # 生成HTML报告
        html_content = report_generator.generate_report(test_report, ReportFormat.HTML)

        return HTMLResponse(content=html_content)

    except Exception as e:
        log.error(f"执行并预览测试报告失败: {e}")
        error_html = f"""
        <html>
            <body>
                <h1>测试执行失败</h1>
                <p>错误信息: {str(e)}</p>
            </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=500)
