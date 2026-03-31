#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API testing test-case execution runner.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
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
from backend.plugin.api_testing.utils.sql_executor import SQLExecutor, SQLQuery


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


async def _process_value(
    value: Any,
    *,
    project_id: int,
    environment_id: Optional[int],
    case_id: int,
    temp_variables: dict[str, Any],
) -> Any:
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


def _make_serializable(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {key: _make_serializable(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(item) for item in obj]
    if hasattr(obj, "model_dump"):
        return _make_serializable(obj.model_dump())
    return obj


def _normalize_step_validations(step: Any) -> list[dict[str, Any]]:
    validations = _get(step, "validate", None)
    if validations is None:
        validations = _get(step, "validations", None)
    return validations or []


def _build_runtime_variables(
    project: Any,
    environment: Any,
    extracted_variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime_variables: dict[str, Any] = {}
    if _get(project, "variables"):
        runtime_variables.update(_get(project, "variables") or {})
    if _get(environment, "variables"):
        runtime_variables.update(_get(environment, "variables") or {})
    if extracted_variables:
        runtime_variables.update(extracted_variables)
    return runtime_variables


@dataclass(slots=True)
class _ExecutionContext:
    case: Any
    project: Any
    environment: Any
    resolved_environment_id: Optional[int]
    base_url: str
    base_headers: dict[str, Any]
    steps: list[Any]
    temp_variables: dict[str, Any]


class TestCaseExecutionRunner:
    def __init__(self, *, case_id: int, environment_id: Optional[int] = None) -> None:
        self.case_id = case_id
        self.environment_id = environment_id
        self.final_result: Optional[dict[str, Any]] = None
        self._context: Any = None

    async def run(self) -> AsyncIterator[dict[str, Any]]:
        ctx = await self._load_context()
        self._context = ctx
        start_time = datetime.now()
        steps = list(_get(ctx, "steps", []) or [])
        resolved_environment_id = _get(ctx, "resolved_environment_id", None)
        test_case_name = _get(_get(ctx, "case", None), "name", None)
        environment_name = _get(_get(ctx, "environment", None), "name", None)

        yield self._event(
            "run_start",
            resolved_environment_id=resolved_environment_id,
            test_case_name=test_case_name,
            environment_name=environment_name,
            total_steps=len(steps),
        )

        step_results: list[dict[str, Any]] = []
        extracted_variables: dict[str, Any] = {}

        for step in steps:
            outcome = await self._execute_step(ctx, step)
            for event in outcome["events"]:
                yield event

            step_result = outcome["step_result"]
            step_results.append(step_result)

            step_variables = step_result.get("variables")
            if isinstance(step_variables, dict):
                extracted_variables.update(step_variables)

        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        success_steps = sum(1 for result in step_results if result.get("success") is True)
        fail_steps = sum(1 for result in step_results if result.get("success") is False)
        success = fail_steps == 0

        final_result = {
            "case_id": self.case_id,
            "environment_id": resolved_environment_id,
            "resolved_environment_id": resolved_environment_id,
            "test_case_name": test_case_name,
            "environment_name": environment_name,
            "success": success,
            "total_steps": len(steps),
            "success_steps": success_steps,
            "fail_steps": fail_steps,
            "duration": duration_ms,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "details": {
                "steps": step_results,
                "environment": {
                    "id": resolved_environment_id,
                    "name": environment_name,
                    "base_url": _get(ctx, "base_url", None),
                    "variables": _make_serializable(
                        _build_runtime_variables(
                            _get(ctx, "project", None),
                            _get(ctx, "environment", None),
                            extracted_variables,
                        )
                    ),
                },
            },
            "steps": step_results,
            "extracted_variables": extracted_variables,
        }

        try:
            saved_report, report_name = await self._persist_report(
                ctx=ctx,
                final_result=final_result,
                start_time=start_time,
                end_time=end_time,
            )
        except Exception as exc:  # noqa: BLE001
            self.final_result = None
            yield self._event("error", message=str(exc), error_type=type(exc).__name__)
            return

        final_result["report_id"] = saved_report.id
        final_result["report_name"] = report_name
        self.final_result = final_result

        yield self._event(
            "run_end",
            report_id=saved_report.id,
            report_name=report_name,
            success=success,
            total_steps=final_result["total_steps"],
            success_steps=success_steps,
            fail_steps=fail_steps,
            duration=duration_ms,
            start_time=final_result["start_time"],
            end_time=final_result["end_time"],
            details=final_result["details"],
            environment_name=final_result["environment_name"],
            resolved_environment_id=resolved_environment_id,
        )

    async def _load_context(self) -> _ExecutionContext:
        test_case = await TestCaseService.get_test_case_by_id(self.case_id)
        if not test_case:
            raise ValueError(f"测试用例不存在: {self.case_id}")

        project = await ProjectService.get_project_by_id(test_case.project_id)
        if not project:
            raise ValueError(f"项目不存在: {test_case.project_id}")

        if self.environment_id is not None:
            environment = await EnvironmentManager.get_environment(self.environment_id)
        else:
            environment = await EnvironmentManager.get_default_environment(project.id)
        if self.environment_id is not None and environment is None:
            raise ValueError(f"环境不存在: {self.environment_id}")

        resolved_environment_id = _get(environment, "id", None)
        environment_variables = _get(environment, "variables", None)
        runtime_base_url = (
            environment_variables.get("base_url")
            if isinstance(environment_variables, dict)
            else None
        )
        base_url = str(runtime_base_url or _get(project, "base_url", "") or "").rstrip("/")
        base_headers: dict[str, Any] = {}
        if isinstance(_get(project, "headers", None), dict):
            base_headers.update(_get(project, "headers", None) or {})
        environment_headers = (
            environment_variables.get("headers")
            if isinstance(environment_variables, dict)
            else None
        )
        if isinstance(environment_headers, dict):
            base_headers.update(environment_headers)

        steps = await TestStepService.get_test_steps(test_case_id=self.case_id, status=1, limit=1000)
        try:
            steps = sorted(steps, key=lambda s: (_get(s, "order") is None, _get(s, "order")))
        except Exception:  # noqa: BLE001
            pass
        if not steps:
            raise ValueError("测试用例没有可执行的测试步骤")

        temp_variables = _build_runtime_variables(project, environment)

        return _ExecutionContext(
            case=test_case,
            project=project,
            environment=environment,
            resolved_environment_id=resolved_environment_id,
            base_url=base_url,
            base_headers=base_headers,
            steps=list(steps),
            temp_variables=temp_variables,
        )

    async def _execute_step(self, ctx: _ExecutionContext, step: Any) -> dict[str, Any]:
        project_id = _get(ctx.project, "id")
        step_start_time = datetime.now()
        step_order = _get(step, "order")
        step_name = _get(step, "name")
        step_success = True
        events: list[dict[str, Any]] = []
        step_assertions: list[dict[str, Any]] = []
        step_sql_results: list[dict[str, Any]] = []
        step_variables: dict[str, Any] = {}

        current_base_url = await _process_value(
            ctx.base_url,
            project_id=project_id,
            environment_id=ctx.resolved_environment_id,
            case_id=self.case_id,
            temp_variables=ctx.temp_variables,
        )
        processed_url = await _process_value(
            _get(step, "url", "") or "",
            project_id=project_id,
            environment_id=ctx.resolved_environment_id,
            case_id=self.case_id,
            temp_variables=ctx.temp_variables,
        )
        if str(processed_url).startswith("http"):
            request_url = str(processed_url)
        else:
            normalized_base_url = str(current_base_url or "").rstrip("/")
            processed_url = str(processed_url or "")
            if normalized_base_url:
                request_url = (
                    f"{normalized_base_url}{processed_url}"
                    if processed_url.startswith("/")
                    else f"{normalized_base_url}/{processed_url}"
                )
            else:
                request_url = processed_url

        headers_payload: dict[str, Any] = {}
        if isinstance(ctx.base_headers, dict):
            headers_payload.update(ctx.base_headers)
        if isinstance(_get(step, "headers", None), dict):
            headers_payload.update(_get(step, "headers", None) or {})

        headers = await _process_value(
            headers_payload,
            project_id=project_id,
            environment_id=ctx.resolved_environment_id,
            case_id=self.case_id,
            temp_variables=ctx.temp_variables,
        )
        params = await _process_value(
            _get(step, "params", None) or {},
            project_id=project_id,
            environment_id=ctx.resolved_environment_id,
            case_id=self.case_id,
            temp_variables=ctx.temp_variables,
        )
        body = await _process_value(
            _get(step, "body", None),
            project_id=project_id,
            environment_id=ctx.resolved_environment_id,
            case_id=self.case_id,
            temp_variables=ctx.temp_variables,
        )
        options = RequestOptions(
            timeout=int(_get(step, "timeout", 30) or 30),
            retry_count=int(_get(step, "retry", 0) or 0),
            retry_interval=int(_get(step, "retry_interval", 1) or 1),
        )

        request_data = {
            "url": request_url,
            "method": str(_get(step, "method", "GET") or "GET"),
            "headers": headers,
            "params": params,
            "json_data": body,
        }

        events.append(
            self._event(
                "step_start",
                step_order=step_order,
                step_name=step_name,
                method=request_data["method"],
                url=request_url,
                message="步骤开始执行",
            )
        )
        events.append(
            self._event(
                "step_request",
                step_order=step_order,
                step_name=step_name,
                request=request_data,
            )
        )

        response_data: dict[str, Any]
        try:
            response = await send_request(
                method=request_data["method"],
                url=request_url,
                params=params if isinstance(params, dict) else None,
                headers=headers if isinstance(headers, dict) else None,
                json_data=body,
                data=None,
                files=_get(step, "files", None),
                auth=_get(step, "auth", None),
                options=options,
            )

            response_data = {
                "status_code": _get(response, "status_code", 0),
                "headers": _get(response, "headers", {}) or {},
                "cookies": _get(response, "cookies", {}) or {},
                "json": _get(response, "json_data", None),
                "body": _get(response, "text", None),
                "text": _get(response, "text", None),
                "elapsed_time": _get(response, "elapsed_time", None),
                "error": _get(response, "error", None),
            }
            if response_data["error"]:
                step_success = False

            events.append(
                self._event(
                    "step_response",
                    step_order=step_order,
                    step_name=step_name,
                    status_code=response_data["status_code"],
                    elapsed_time=response_data.get("elapsed_time"),
                    success=not bool(response_data.get("error")),
                    message=response_data.get("error") or "请求完成",
                )
            )

            for assertion_dict in _normalize_step_validations(step):
                assertion = Assertion(**assertion_dict)
                assertion_result = AssertionEngine.execute_assertion(assertion, response_data)
                serialized_assertion = _make_serializable(assertion_result.model_dump())
                step_assertions.append(serialized_assertion)
                if not assertion_result.success:
                    step_success = False
                events.append(
                    self._event(
                        "step_assertion",
                        step_order=step_order,
                        step_name=step_name,
                        assertion=serialized_assertion["assertion"],
                        success=serialized_assertion["success"],
                        actual=serialized_assertion.get("actual"),
                        message=serialized_assertion.get("message"),
                    )
                )

            sql_queries = _get(step, "sql_queries", None)
            if sql_queries:
                for sql_dict in sql_queries:
                    sql_payload = await _process_value(
                        sql_dict,
                        project_id=project_id,
                        environment_id=ctx.resolved_environment_id,
                        case_id=self.case_id,
                        temp_variables=ctx.temp_variables,
                    )
                    sql_result = await SQLExecutor.execute_query(SQLQuery(**sql_payload))
                    serialized_sql_result = _make_serializable(sql_result.model_dump())
                    step_sql_results.append(serialized_sql_result)
                    if not sql_result.success:
                        step_success = False
                    if sql_result.extracted_variables:
                        ctx.temp_variables.update(sql_result.extracted_variables)
                        step_variables.update(sql_result.extracted_variables)
                    events.append(
                        self._event(
                            "step_sql",
                            step_order=step_order,
                            step_name=step_name,
                            sql_name=serialized_sql_result.get("name")
                            or _get(serialized_sql_result.get("sql"), "name"),
                            success=serialized_sql_result.get("success"),
                            message=serialized_sql_result.get("error"),
                            extracted_variables=serialized_sql_result.get("extracted_variables") or {},
                        )
                    )

            extract_config = _get(step, "extract", None)
            response_json = response_data.get("json")
            if isinstance(extract_config, dict) and response_json:
                for var_name, json_path in extract_config.items():
                    try:
                        from jsonpath_ng import parse

                        jsonpath_expr = parse(json_path)
                        matches = [match.value for match in jsonpath_expr.find(response_json)]
                        if matches:
                            value = matches[0] if len(matches) == 1 else matches
                            ctx.temp_variables[var_name] = value
                            step_variables[var_name] = value
                            events.append(
                                self._event(
                                    "step_extract",
                                    step_order=step_order,
                                    step_name=step_name,
                                    variable_name=var_name,
                                    success=True,
                                    value=value,
                                    message="变量提取成功",
                                )
                            )
                    except Exception as exc:  # noqa: BLE001
                        log.error(f"提取变量 {var_name} 失败: {exc}")
                        step_success = False
                        events.append(
                            self._event(
                                "step_extract",
                                step_order=step_order,
                                step_name=step_name,
                                variable_name=var_name,
                                success=False,
                                value=None,
                                message=str(exc),
                            )
                        )

        except Exception as exc:  # noqa: BLE001
            step_success = False
            log.error(f"执行测试步骤失败: {exc}")
            response_data = {
                "status_code": 0,
                "headers": {},
                "cookies": {},
                "json": None,
                "body": None,
                "text": None,
                "elapsed_time": None,
                "error": str(exc),
            }
            events.append(
                self._event(
                    "step_response",
                    step_order=step_order,
                    step_name=step_name,
                    status_code=0,
                    elapsed_time=None,
                    success=False,
                    message=str(exc),
                )
            )

        step_end_time = datetime.now()
        duration = int((step_end_time - step_start_time).total_seconds() * 1000)
        step_result = {
            "step_id": _get(step, "id"),
            "name": step_name,
            "order": step_order,
            "url": request_url,
            "method": request_data["method"],
            "request_data": request_data,
            "response": response_data,
            "assertions": step_assertions,
            "sql_results": step_sql_results if step_sql_results else None,
            "variables": step_variables if step_variables else None,
            "success": step_success,
            "start_time": step_start_time.isoformat(),
            "end_time": step_end_time.isoformat(),
            "duration": duration,
        }
        events.append(
            self._event(
                "step_end",
                step_order=step_order,
                step_name=step_name,
                success=step_success,
                duration=duration,
                message="步骤执行完成" if step_success else "步骤执行失败",
            )
        )

        return {"events": events, "step_result": step_result}

    async def _persist_report(
        self,
        *,
        ctx: _ExecutionContext,
        final_result: dict[str, Any],
        start_time: datetime,
        end_time: datetime,
    ) -> tuple[Any, str]:
        report_name = (
            f'{_get(ctx.case, "name")}_执行报告_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        )
        saved_report = await TestReportService.create_test_report(
            TestReportCreateRequest(
                test_case_id=self.case_id,
                name=report_name,
                success=bool(final_result["success"]),
                total_steps=int(final_result["total_steps"]),
                success_steps=int(final_result["success_steps"]),
                fail_steps=int(final_result["fail_steps"]),
                start_time=start_time,
                end_time=end_time,
                duration=int(final_result["duration"]),
                details=final_result["details"],
            )
        )
        return saved_report, report_name

    def _event(self, event_type: str, **payload: Any) -> dict[str, Any]:
        return {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "case_id": self.case_id,
            "environment_id": self.environment_id,
            **payload,
        }
