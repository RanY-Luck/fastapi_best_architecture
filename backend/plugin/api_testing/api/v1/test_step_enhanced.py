#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time     : 2025/12/13 11:30
# @Author   : 冉勇
# @File     : test_step_enhanced.py
# @Software : PyCharm
# @Desc     :
"""
完整的测试流程集成方案
包含：配置 -> 执行 -> 报告
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Body, Query, Path
from datetime import datetime
from backend.common.response.response_schema import response_base, ResponseModel, ResponseSchemaModel
from backend.plugin.api_testing.service.test_step_service import TestStepService
from backend.plugin.api_testing.schema.request import TestStepCreateRequest

router = APIRouter()


@router.post("/create-with-templates", response_model=ResponseModel, summary="使用模板创建测试步骤")
async def create_step_with_templates(
        name: str = Body(..., description="步骤名称"),
        test_case_id: int = Body(..., description="测试用例ID"),
        url: str = Body(..., description="请求URL"),
        method: str = Body(..., description="请求方法"),
        headers: Optional[Dict[str, str]] = Body(None, description="请求头"),
        params: Optional[Dict[str, Any]] = Body(None, description="查询参数"),
        body: Optional[Dict[str, Any]] = Body(None, description="请求体"),

        # 使用模板配置
        assertion_templates: Optional[List[str]] = Body(None, description="断言模板ID列表"),
        custom_assertions: Optional[List[Dict[str, Any]]] = Body(None, description="自定义断言"),

        sql_templates: Optional[List[str]] = Body(None, description="SQL模板ID列表"),
        custom_sql_queries: Optional[List[Dict[str, Any]]] = Body(None, description="自定义SQL查询"),

        extract_templates: Optional[List[str]] = Body(None, description="提取模板ID列表"),
        custom_extracts: Optional[Dict[str, str]] = Body(None, description="自定义变量提取"),

        order: int = Body(..., description="步骤顺序"),
        timeout: int = Body(30, description="超时时间"),
        retry: int = Body(0, description="重试次数"),
        retry_interval: int = Body(1, description="重试间隔")
) -> ResponseModel | ResponseSchemaModel:
    """
    使用模板快速创建测试步骤

    支持：
    1. 选择预定义的断言模板
    2. 选择预定义的SQL模板
    3. 选择预定义的变量提取模板
    4. 自定义配置
    """
    try:
        # 1. 构建断言配置
        validate = []

        # 从模板加载断言
        if assertion_templates:
            for template_id in assertion_templates:
                assertion_config = await _load_assertion_template(template_id)
                if assertion_config:
                    validate.append(assertion_config)

        # 添加自定义断言
        if custom_assertions:
            validate.extend(custom_assertions)

        # 2. 构建SQL查询配置
        sql_queries = []

        # 从模板加载SQL
        if sql_templates:
            for template_id in sql_templates:
                sql_config = await _load_sql_template(template_id)
                if sql_config:
                    sql_queries.append(sql_config)

        # 添加自定义SQL
        if custom_sql_queries:
            sql_queries.extend(custom_sql_queries)

        # 3. 构建变量提取配置
        extract = {}

        # 从模板加载提取配置
        if extract_templates:
            for template_id in extract_templates:
                extract_config = await _load_extract_template(template_id)
                if extract_config:
                    extract.update(extract_config)

        # 添加自定义提取
        if custom_extracts:
            extract.update(custom_extracts)

        # 4. 创建测试步骤
        step_data = TestStepCreateRequest(
            name=name,
            test_case_id=test_case_id,
            url=url,
            method=method,
            headers=headers,
            params=params,
            body=body,
            validations=validate,
            sql_queries=sql_queries,
            extract=extract,
            timeout=timeout,
            retry=retry,
            retry_interval=retry_interval,
            order=order,
            status=1
        )

        test_step = await TestStepService.create_test_step(step_data)

        return response_base.success(
            data={
                "step_id": test_step.id,
                "name": test_step.name,
                "config_summary": {
                    "assertions_count": len(validate),
                    "sql_queries_count": len(sql_queries),
                    "extracts_count": len(extract)
                }
            }
        )

    except Exception as e:
        return response_base.fail(data=f"创建测试步骤失败: {str(e)}")


async def _load_assertion_template(template_id: str) -> Optional[Dict[str, Any]]:
    """从模板ID加载断言配置"""
    templates = {
        "assert_status_200": {
            "source": "status_code",
            "type": "equals",
            "expected": 200,
            "message": "验证状态码为200"
        },
        "assert_json_exists": {
            "source": "json",
            "type": "exists",
            "path": "$.data",
            "message": "验证数据存在"
        },
        "assert_json_success": {
            "source": "json",
            "type": "equals",
            "path": "$.code",
            "expected": 0,
            "message": "验证业务状态码成功"
        }
    }
    return templates.get(template_id)


async def _load_sql_template(template_id: str) -> Optional[Dict[str, Any]]:
    """从模板ID加载SQL配置"""
    templates = {
        "mysql_select_by_id": {
            "name": "根据ID查询",
            "query": "SELECT * FROM {{table_name}} WHERE id = {{id}}",
            "extract": {
                "db_id": "0.id"
            },
            "use_default_db": True
        }
    }
    return templates.get(template_id)


async def _load_extract_template(template_id: str) -> Optional[Dict[str, str]]:
    """从模板ID加载变量提取配置"""
    templates = {
        "extract_token": {
            "token": "$.data.token"
        },
        "extract_user_id": {
            "user_id": "$.data.user.id"
        }
    }
    return templates.get(template_id)


# ==================== 2. 增强的测试用例执行接口 ====================
# backend/plugin/api_testing/api/v1/test_case_execution.py

from backend.plugin.api_testing.service.test_case_service import TestCaseService
from backend.plugin.api_testing.service.test_report_service import TestReportService
from backend.plugin.api_testing.service.project_service import ProjectService
from backend.plugin.api_testing.utils.http_client import send_request, RequestOptions
from backend.plugin.api_testing.utils.assertion import AssertionEngine, Assertion
from backend.plugin.api_testing.utils.sql_executor import SQLExecutor, SQLQuery
from backend.plugin.api_testing.schema.request import TestReportCreateRequest
from jsonpath_ng import parse
from backend.common.log import log


@router.post("/{case_id}/execute-enhanced", response_model=ResponseModel, summary="增强执行测试用例")
async def execute_test_case_enhanced(
        case_id: int = Path(..., description="测试用例ID"),
        environment_id: Optional[int] = Query(None, description="环境ID"),
        variables: Optional[Dict[str, Any]] = Body(None, description="额外的变量")
) -> ResponseModel | ResponseSchemaModel:
    """
    增强的测试用例执行

    特性：
    1. 详细的步骤执行信息
    2. 实时变量传递
    3. 完整的断言和SQL结果
    4. 错误时的详细诊断
    """
    try:
        # 1. 获取测试用例和项目
        test_case = await TestCaseService.get_test_case_by_id(case_id)
        if not test_case:
            return response_base.fail(data=f"测试用例不存在: {case_id}")

        project = await ProjectService.get_project_by_id(test_case.project_id)
        if not project:
            return response_base.fail(data=f"项目不存在: {test_case.project_id}")

        # 2. 获取测试步骤
        test_steps = await TestStepService.get_test_steps(
            test_case_id=case_id,
            status=1,
            limit=1000
        )

        if not test_steps:
            return response_base.fail(data="测试用例没有可执行的测试步骤")

        test_steps = sorted(test_steps, key=lambda x: x.order)

        # 3. 初始化执行环境
        execution_context = {
            "project": project,
            "test_case": test_case,
            "variables": variables or {},
            "start_time": datetime.now(),
            "step_results": [],
            "success_count": 0,
            "fail_count": 0
        }

        # 4. 执行每个测试步骤
        for step in test_steps:
            step_result = await _execute_single_step(step, execution_context)
            execution_context["step_results"].append(step_result)

            if step_result["success"]:
                execution_context["success_count"] += 1
            else:
                execution_context["fail_count"] += 1

        # 5. 生成测试报告
        end_time = datetime.now()
        duration = int((end_time - execution_context["start_time"]).total_seconds() * 1000)

        report_name = f"{test_case.name}_执行报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 6. 保存测试报告
        report_data = TestReportCreateRequest(
            test_case_id=case_id,
            name=report_name,
            success=execution_context["fail_count"] == 0,
            total_steps=len(test_steps),
            success_steps=execution_context["success_count"],
            fail_steps=execution_context["fail_count"],
            start_time=execution_context["start_time"],
            end_time=end_time,
            duration=duration,
            details={
                "steps": execution_context["step_results"],
                "environment": {
                    "variables": execution_context["variables"]
                },
                "project": {
                    "id": project.id,
                    "name": project.name
                }
            }
        )

        saved_report = await TestReportService.create_test_report(report_data)

        # 7. 返回执行结果
        return response_base.success(
            data={
                "report_id": saved_report.id,
                "report_name": report_name,
                "execution_summary": {
                    "total_steps": len(test_steps),
                    "success_steps": execution_context["success_count"],
                    "fail_steps": execution_context["fail_count"],
                    "success_rate": f"{(execution_context['success_count'] / len(test_steps) * 100):.2f}%",
                    "duration_ms": duration,
                    "duration_seconds": f"{(duration / 1000):.2f}"
                },
                "variables": execution_context["variables"],
                "steps_detail": [
                    {
                        "order": r["order"],
                        "name": r["name"],
                        "success": r["success"],
                        "duration_ms": r["duration"],
                        "assertions_passed": sum(1 for a in r.get("assertions", []) if a.get("success")),
                        "assertions_total": len(r.get("assertions", [])),
                        "sql_executed": len(r.get("sql_results", []))
                    }
                    for r in execution_context["step_results"]
                ]
            }
        )

    except Exception as e:
        log.error(f"执行测试用例失败: {e}")
        import traceback
        log.error(traceback.format_exc())
        return response_base.fail(data=f"执行测试用例失败: {str(e)}")


async def _execute_single_step(step, context: Dict[str, Any]) -> Dict[str, Any]:
    """执行单个测试步骤"""
    step_start = datetime.now()
    step_success = True

    result = {
        "step_id": step.id,
        "name": step.name,
        "order": step.order,
        "method": step.method,
        "url": step.url,
        "success": True,
        "start_time": step_start.isoformat(),
        "request_data": {},
        "response_data": {},
        "assertions": [],
        "sql_results": [],
        "extracted_variables": {},
        "error": None
    }

    try:
        # 1. 构建完整URL
        url = step.url
        if not url.startswith('http'):
            base_url = context["project"].base_url.rstrip('/')
            url = f"{base_url}{url}" if url.startswith('/') else f"{base_url}/{url}"

        # 2. 处理变量替换（在URL、headers、params、body中）
        url = _replace_variables(url, context["variables"])
        headers = _replace_dict_variables(step.headers or {}, context["variables"])
        params = _replace_dict_variables(step.params or {}, context["variables"])
        body = _replace_dict_variables(step.body or {}, context["variables"])

        # 3. 合并项目级请求头
        if context["project"].headers:
            headers.update(context["project"].headers)

        # 4. 发送HTTP请求
        request_options = RequestOptions(
            timeout=step.timeout,
            retry_count=step.retry,
            retry_interval=step.retry_interval
        )

        response = await send_request(
            method=step.method,
            url=url,
            params=params,
            headers=headers,
            json_data=body,
            options=request_options
        )

        # 5. 记录请求和响应数据
        result["request_data"] = {
            "url": url,
            "method": step.method,
            "headers": headers,
            "params": params,
            "body": body
        }

        result["response_data"] = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "elapsed_time": response.elapsed_time,
            "json": response.json_data,
            "text": response.text if not response.json_data else None
        }

        # 6. 执行断言
        if step.validate:
            for assertion_dict in step.validate:
                try:
                    assertion = Assertion(**assertion_dict)
                    assertion_result = AssertionEngine.execute_assertion(
                        assertion,
                        result["response_data"]
                    )

                    result["assertions"].append(
                        {
                            "assertion": assertion_dict,
                            "success": assertion_result.success,
                            "actual": assertion_result.actual,
                            "message": assertion_result.message
                        }
                    )

                    if not assertion_result.success:
                        step_success = False

                except Exception as e:
                    result["assertions"].append(
                        {
                            "assertion": assertion_dict,
                            "success": False,
                            "error": str(e)
                        }
                    )
                    step_success = False

        # 7. 执行SQL查询
        if step.sql_queries:
            for sql_dict in step.sql_queries:
                try:
                    # 替换SQL中的变量
                    sql_query_str = _replace_variables(sql_dict.get("query", ""), context["variables"])
                    sql_dict["query"] = sql_query_str

                    sql_query = SQLQuery(**sql_dict)
                    sql_result = await SQLExecutor.execute_query(sql_query)

                    result["sql_results"].append(
                        {
                            "name": sql_result.name,
                            "query": sql_result.query,
                            "success": sql_result.success,
                            "data": sql_result.data,
                            "affected_rows": sql_result.affected_rows,
                            "error": sql_result.error,
                            "extracted_variables": sql_result.extracted_variables
                        }
                    )

                    if not sql_result.success:
                        step_success = False

                    # 更新上下文变量
                    if sql_result.extracted_variables:
                        context["variables"].update(sql_result.extracted_variables)
                        result["extracted_variables"].update(sql_result.extracted_variables)

                except Exception as e:
                    result["sql_results"].append(
                        {
                            "name": sql_dict.get("name", "未命名SQL"),
                            "query": sql_dict.get("query", ""),
                            "success": False,
                            "error": str(e)
                        }
                    )
                    step_success = False

        # 8. 提取变量
        if step.extract and response.json_data:
            for var_name, json_path in step.extract.items():
                try:
                    jsonpath_expr = parse(json_path)
                    matches = [match.value for match in jsonpath_expr.find(response.json_data)]

                    if matches:
                        value = matches[0] if len(matches) == 1 else matches
                        context["variables"][var_name] = value
                        result["extracted_variables"][var_name] = value

                except Exception as e:
                    log.error(f"提取变量 {var_name} 失败: {e}")

        # 9. 检查响应错误
        if response.error:
            step_success = False
            result["error"] = response.error

    except Exception as e:
        step_success = False
        result["error"] = str(e)
        log.error(f"执行步骤失败: {e}")

    # 10. 计算执行时间
    step_end = datetime.now()
    result["end_time"] = step_end.isoformat()
    result["duration"] = int((step_end - step_start).total_seconds() * 1000)
    result["success"] = step_success

    return result


def _replace_variables(text: str, variables: Dict[str, Any]) -> str:
    """替换文本中的变量"""
    if not text or not isinstance(text, str):
        return text

    import re
    pattern = r'\{\{(\w+)\}\}'

    def replacer(match):
        var_name = match.group(1)
        return str(variables.get(var_name, match.group(0)))

    return re.sub(pattern, replacer, text)


def _replace_dict_variables(data: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
    """递归替换字典中的变量"""
    if not data:
        return data

    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = _replace_variables(value, variables)
        elif isinstance(value, dict):
            result[key] = _replace_dict_variables(value, variables)
        elif isinstance(value, list):
            result[key] = [
                _replace_variables(item, variables) if isinstance(item, str)
                else _replace_dict_variables(item, variables) if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            result[key] = value

    return result


# ==================== 3. 增强的测试报告展示接口 ====================

@router.get("/{report_id}/detailed", response_model=ResponseModel, summary="获取详细测试报告")
async def get_detailed_report(
        report_id: int = Path(..., description="报告ID")
) -> ResponseModel | ResponseSchemaModel:
    """
    获取详细的测试报告，包含所有执行细节
    """
    try:
        report = await TestReportService.get_test_report_by_id(report_id)
        if not report:
            return response_base.fail(data="报告不存在")

        # 获取测试用例和项目信息
        test_case = await TestCaseService.get_test_case_by_id(report.test_case_id)
        project = await ProjectService.get_project_by_id(test_case.project_id) if test_case else None

        # 构建详细报告数据
        detailed_data = {
            "report_id": report.id,
            "report_name": report.name,
            "project_info": {
                "id": project.id if project else None,
                "name": project.name if project else "未知项目"
            },
            "test_case_info": {
                "id": test_case.id if test_case else None,
                "name": test_case.name if test_case else "未知用例",
                "description": test_case.description if test_case else None
            },
            "execution_summary": {
                "success": report.success == 1,
                "total_steps": report.total_steps,
                "success_steps": report.success_steps,
                "fail_steps": report.fail_steps,
                "success_rate": f"{(report.success_steps / report.total_steps * 100):.2f}%" if report.total_steps > 0 else "0%",
                "duration_ms": report.duration,
                "duration_seconds": f"{(report.duration / 1000):.2f}",
                "start_time": report.start_time.isoformat(),
                "end_time": report.end_time.isoformat()
            },
            "steps": [],
            "statistics": {
                "total_assertions": 0,
                "passed_assertions": 0,
                "failed_assertions": 0,
                "total_sql_queries": 0,
                "successful_sql_queries": 0,
                "failed_sql_queries": 0,
                "total_variables_extracted": 0
            }
        }

        # 处理步骤详情
        steps_data = report.details.get("steps", [])
        for step in steps_data:
            # 统计断言
            assertions = step.get("assertions", [])
            detailed_data["statistics"]["total_assertions"] += len(assertions)
            detailed_data["statistics"]["passed_assertions"] += sum(1 for a in assertions if a.get("success"))
            detailed_data["statistics"]["failed_assertions"] += sum(1 for a in assertions if not a.get("success"))

            # 统计SQL
            sql_results = step.get("sql_results", [])
            detailed_data["statistics"]["total_sql_queries"] += len(sql_results)
            detailed_data["statistics"]["successful_sql_queries"] += sum(1 for s in sql_results if s.get("success"))
            detailed_data["statistics"]["failed_sql_queries"] += sum(1 for s in sql_results if not s.get("success"))

            # 统计提取的变量
            extracted_vars = step.get("extracted_variables", {})
            detailed_data["statistics"]["total_variables_extracted"] += len(extracted_vars)

            # 构建步骤详情
            step_detail = {
                "order": step.get("order"),
                "name": step.get("name"),
                "success": step.get("success"),
                "duration_ms": step.get("duration"),
                "request": {
                    "method": step.get("method"),
                    "url": step.get("url"),
                    "headers": step.get("request_data", {}).get("headers"),
                    "params": step.get("request_data", {}).get("params"),
                    "body": step.get("request_data", {}).get("body")
                },
                "response": {
                    "status_code": step.get("response_data", {}).get("status_code"),
                    "elapsed_time": step.get("response_data", {}).get("elapsed_time"),
                    "headers": step.get("response_data", {}).get("headers"),
                    "body": step.get("response_data", {}).get("json") or step.get("response_data", {}).get("text")
                },
                "assertions": [
                    {
                        "type": a.get("assertion", {}).get("type"),
                        "source": a.get("assertion", {}).get("source"),
                        "path": a.get("assertion", {}).get("path"),
                        "expected": a.get("assertion", {}).get("expected"),
                        "actual": a.get("actual"),
                        "success": a.get("success"),
                        "message": a.get("message")
                    }
                    for a in assertions
                ],
                "sql_queries": [
                    {
                        "name": s.get("name"),
                        "query": s.get("query"),
                        "success": s.get("success"),
                        "data": s.get("data"),
                        "affected_rows": s.get("affected_rows"),
                        "error": s.get("error"),
                        "extracted_variables": s.get("extracted_variables")
                    }
                    for s in sql_results
                ],
                "extracted_variables": extracted_vars,
                "error": step.get("error")
            }

            detailed_data["steps"].append(step_detail)

        # 添加变量信息
        detailed_data["variables"] = report.details.get("environment", {}).get("variables", {})

        return response_base.success(data=detailed_data)

    except Exception as e:
        log.error(f"获取详细报告失败: {e}")
        return response_base.fail(data=f"获取详细报告失败: {str(e)}")
