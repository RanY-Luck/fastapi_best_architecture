#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API测试用例执行服务
"""
from datetime import datetime
from typing import Any, Optional

from backend.common.log import log
from backend.plugin.api_testing.schema.request import TestReportCreateRequest
from backend.plugin.api_testing.service.project_service import ProjectService
from backend.plugin.api_testing.service.test_case_service import TestCaseService
from backend.plugin.api_testing.service.test_report_service import TestReportService
from backend.plugin.api_testing.service.test_step_service import TestStepService
from backend.plugin.api_testing.utils.assertion import Assertion, AssertionEngine
from backend.plugin.api_testing.utils.environment import EnvironmentManager, VariableManager
from backend.plugin.api_testing.utils.http_client import RequestOptions, send_request
from backend.plugin.api_testing.utils.report_generator import StepResult
from backend.plugin.api_testing.utils.sql_executor import SQLExecutor, SQLQuery


def make_serializable(obj: Any) -> Any:
    """递归转换对象为可JSON序列化的格式。"""
    if obj is None:
        return None
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {key: make_serializable(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [make_serializable(item) for item in obj]
    if hasattr(obj, 'model_dump'):
        return make_serializable(obj.model_dump())
    return obj


async def resolve_execution_environment(project_id: int, environment_id: Optional[int]):
    """解析执行环境，优先使用显式环境，其次回退到默认环境。"""
    if environment_id is not None:
        return await EnvironmentManager.get_environment(environment_id)
    return await EnvironmentManager.get_default_environment(project_id)


def normalize_step_validations(step) -> list[dict[str, Any]]:  # noqa: ANN001
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


async def process_step_value(
    value: Any,
    *,
    project_id: int,
    environment_id: Optional[int],
    case_id: int,
    temp_variables: dict[str, Any],
) -> Any:
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


class TestCaseExecutionService:
    """单用例执行服务。"""

    @staticmethod
    async def execute_test_case(case_id: int, environment_id: Optional[int] = None) -> dict[str, Any]:
        """执行测试用例并创建报告。"""
        test_case = await TestCaseService.get_test_case_by_id(case_id)
        if not test_case:
            raise ValueError(f'测试用例不存在: {case_id}')

        project = await ProjectService.get_project_by_id(test_case.project_id)
        if not project:
            raise ValueError(f'项目不存在: {test_case.project_id}')

        environment = await resolve_execution_environment(project.id, environment_id)
        if environment_id is not None and not environment:
            raise ValueError(f'环境不存在: {environment_id}')

        test_steps = await TestStepService.get_test_steps(test_case_id=case_id, status=1, limit=1000)
        if not test_steps:
            raise ValueError('测试用例没有可执行的测试步骤')

        test_steps = sorted(test_steps, key=lambda step: step.order)
        resolved_environment_id = environment.id if environment else None
        runtime_base_url = environment.variables.get('base_url') if environment and environment.variables else None
        base_url = (runtime_base_url or project.base_url or '').rstrip('/')
        base_headers: dict[str, Any] = {}
        if project.headers:
            base_headers.update(project.headers)
        if environment and isinstance(environment.variables, dict):
            env_headers = environment.variables.get('headers')
            if isinstance(env_headers, dict):
                base_headers.update(env_headers)

        report_name = f'{test_case.name}_执行报告_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        start_time = datetime.now()
        step_results = []
        extracted_variables: dict[str, Any] = {}
        success_steps = 0
        fail_steps = 0

        for step in test_steps:
            step_start_time = datetime.now()
            step_success = True
            step_assertions = []
            step_sql_results = []
            step_variables: dict[str, Any] = {}
            runtime_variables = build_runtime_variables(project, environment, extracted_variables)
            current_base_url = await process_step_value(
                base_url,
                project_id=project.id,
                environment_id=resolved_environment_id,
                case_id=case_id,
                temp_variables=runtime_variables,
            )
            request_url = step.url
            request_data = {'url': step.url, 'method': step.method}
            response_data = {'status_code': 0, 'error': None}

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
                    normalized_base_url = (current_base_url or '').rstrip('/')
                    request_url = (
                        f'{normalized_base_url}{processed_url}'
                        if processed_url.startswith('/')
                        else f'{normalized_base_url}/{processed_url}'
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

                response = await send_request(
                    method=step.method,
                    url=request_url,
                    params=params,
                    headers=headers,
                    json_data=body,
                    options=RequestOptions(
                        timeout=step.timeout,
                        retry_count=step.retry,
                        retry_interval=step.retry_interval,
                    ),
                )

                request_data = {
                    'url': request_url,
                    'method': step.method,
                    'headers': headers,
                    'params': params,
                    'json_data': body,
                }
                response_data = {
                    'status_code': response.status_code,
                    'headers': response.headers,
                    'cookies': response.cookies,
                    'json': response.json_data,
                    'body': response.text,
                    'text': response.text,
                    'elapsed_time': response.elapsed_time,
                    'error': response.error,
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
                        sql_result = await SQLExecutor.execute_query(SQLQuery(**sql_payload))
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
                        except Exception as exc:  # noqa: BLE001
                            log.error(f'提取变量 {var_name} 失败: {exc}')
                            step_success = False

                if response.error:
                    step_success = False

            except Exception as exc:  # noqa: BLE001
                step_success = False
                log.error(f'执行测试步骤失败: {exc}')
                request_data = {'url': request_url, 'method': step.method}
                response_data = {'status_code': 0, 'error': str(exc)}

            step_end_time = datetime.now()
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
                duration=int((step_end_time - step_start_time).total_seconds() * 1000),
            )
            step_results.append(step_result)

            if step_success:
                success_steps += 1
            else:
                fail_steps += 1

        end_time = datetime.now()
        duration = int((end_time - start_time).total_seconds() * 1000)
        serializable_steps = [make_serializable(step.model_dump()) for step in step_results]
        saved_report = await TestReportService.create_test_report(
            TestReportCreateRequest(
                test_case_id=case_id,
                name=report_name,
                success=fail_steps == 0,
                total_steps=len(test_steps),
                success_steps=success_steps,
                fail_steps=fail_steps,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                details={
                    'steps': serializable_steps,
                    'environment': {
                        'id': resolved_environment_id,
                        'name': environment.name if environment else None,
                        'base_url': base_url,
                        'variables': make_serializable(build_runtime_variables(project, environment, extracted_variables)),
                    },
                },
            )
        )

        return {
            'case_id': case_id,
            'test_case_name': test_case.name,
            'report_id': saved_report.id,
            'report_name': report_name,
            'success': fail_steps == 0,
            'total_steps': len(test_steps),
            'success_steps': success_steps,
            'fail_steps': fail_steps,
            'duration': duration,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'environment_id': resolved_environment_id,
            'environment_name': environment.name if environment else None,
            'details': {
                'steps': serializable_steps,
                'environment': {
                    'id': resolved_environment_id,
                    'name': environment.name if environment else None,
                },
            },
        }
