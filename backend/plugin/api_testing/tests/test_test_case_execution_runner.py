import pytest
from types import SimpleNamespace


@pytest.mark.anyio
async def test_runner_emits_events_and_populates_final_result(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.plugin.api_testing.service.test_case_execution_runner import TestCaseExecutionRunner

    case_id = 123
    environment_id = 456

    async def fake_load_context(self: TestCaseExecutionRunner) -> dict:
        return {
            "case_id": self.case_id,
            "environment_id": self.environment_id,
            "steps": [
                {"id": 1, "name": "Step 1", "order": 1},
            ],
        }

    async def fake_execute_step(self: TestCaseExecutionRunner, ctx: dict, step: dict) -> dict:
        assert ctx["case_id"] == case_id
        assert step["id"] == 1
        return {
            "events": [
                {"type": "step_start"},
                {"type": "step_request"},
                {"type": "step_response"},
                {"type": "step_end", "success": True},
            ],
            "step_result": {"step_id": step["id"], "success": True},
        }

    async def fake_persist_report(self, **kwargs):  # noqa: ANN001, ANN003
        return SimpleNamespace(id=999), "demo-report"

    monkeypatch.setattr(TestCaseExecutionRunner, "_load_context", fake_load_context)
    monkeypatch.setattr(TestCaseExecutionRunner, "_execute_step", fake_execute_step)
    monkeypatch.setattr(TestCaseExecutionRunner, "_persist_report", fake_persist_report)

    runner = TestCaseExecutionRunner(case_id=case_id, environment_id=environment_id)

    events: list[dict] = []
    async for event in runner.run():
        events.append(event)

    assert [event["type"] for event in events] == [
        "run_start",
        "step_start",
        "step_request",
        "step_response",
        "step_end",
        "run_end",
    ]

    assert runner.final_result is not None
    assert runner.final_result["success"] is True


@pytest.mark.anyio
async def test_load_context_raises_when_explicit_environment_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.plugin.api_testing.service.test_case_execution_runner import TestCaseExecutionRunner

    async def fake_get_test_case(case_id: int):
        return SimpleNamespace(project_id=9)

    async def fake_get_project(project_id: int):
        return SimpleNamespace(id=project_id, base_url="https://project.example", headers={}, variables={})

    async def fake_get_environment(environment_id: int):
        return None

    monkeypatch.setattr(
        "backend.plugin.api_testing.service.test_case_execution_runner.TestCaseService.get_test_case_by_id",
        fake_get_test_case,
    )
    monkeypatch.setattr(
        "backend.plugin.api_testing.service.test_case_execution_runner.ProjectService.get_project_by_id",
        fake_get_project,
    )
    monkeypatch.setattr(
        "backend.plugin.api_testing.service.test_case_execution_runner.EnvironmentManager.get_environment",
        fake_get_environment,
    )

    runner = TestCaseExecutionRunner(case_id=1, environment_id=999)

    with pytest.raises(ValueError, match="环境不存在"):
        await runner._load_context()


@pytest.mark.anyio
async def test_load_context_raises_when_no_enabled_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.plugin.api_testing.service.test_case_execution_runner import TestCaseExecutionRunner

    async def fake_get_test_case(case_id: int):
        return SimpleNamespace(project_id=9)

    async def fake_get_project(project_id: int):
        return SimpleNamespace(id=project_id, base_url="https://project.example", headers={}, variables={})

    async def fake_get_environment(project_id: int):
        return SimpleNamespace(id=3, variables={"base_url": "https://env.example"})

    async def fake_get_steps(**kwargs):
        return []

    monkeypatch.setattr(
        "backend.plugin.api_testing.service.test_case_execution_runner.TestCaseService.get_test_case_by_id",
        fake_get_test_case,
    )
    monkeypatch.setattr(
        "backend.plugin.api_testing.service.test_case_execution_runner.ProjectService.get_project_by_id",
        fake_get_project,
    )
    monkeypatch.setattr(
        "backend.plugin.api_testing.service.test_case_execution_runner.EnvironmentManager.get_default_environment",
        fake_get_environment,
    )
    monkeypatch.setattr(
        "backend.plugin.api_testing.service.test_case_execution_runner.TestStepService.get_test_steps",
        fake_get_steps,
    )

    runner = TestCaseExecutionRunner(case_id=1, environment_id=None)

    with pytest.raises(ValueError, match="没有可执行的测试步骤"):
        await runner._load_context()


@pytest.mark.anyio
async def test_execute_step_merges_base_headers_and_uses_json_body(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.plugin.api_testing.service.test_case_execution_runner import TestCaseExecutionRunner, _ExecutionContext

    observed: dict[str, object] = {}

    async def passthrough(value, **kwargs):  # noqa: ANN001
        return value

    async def fake_send_request(**kwargs):  # noqa: ANN003
        observed.update(kwargs)
        return SimpleNamespace(
            status_code=200,
            error=None,
            elapsed_time=5,
            model_dump=lambda: {"status_code": 200, "error": None, "elapsed_time": 5},
        )

    monkeypatch.setattr(
        "backend.plugin.api_testing.service.test_case_execution_runner._process_value",
        passthrough,
    )
    monkeypatch.setattr(
        "backend.plugin.api_testing.service.test_case_execution_runner.send_request",
        fake_send_request,
    )

    runner = TestCaseExecutionRunner(case_id=1, environment_id=2)
    ctx = _ExecutionContext(
        case=None,
        project=SimpleNamespace(id=8),
        environment=SimpleNamespace(id=2),
        resolved_environment_id=2,
        base_url="https://env.example",
        base_headers={"X-Project": "demo", "Authorization": "Bearer token"},
        steps=[],
        temp_variables={},
    )
    step = {
        "id": 7,
        "name": "Create order",
        "order": 1,
        "method": "POST",
        "url": "/orders",
        "headers": {"X-Step": "yes"},
        "params": {"page": 1},
        "body": {"name": "demo"},
        "timeout": 30,
        "retry": 0,
        "retry_interval": 1,
    }

    result = await runner._execute_step(ctx, step)

    assert observed["url"] == "https://env.example/orders"
    assert observed["headers"] == {
        "X-Project": "demo",
        "Authorization": "Bearer token",
        "X-Step": "yes",
    }
    assert observed["json_data"] == {"name": "demo"}
    assert observed["data"] is None
    assert result["step_result"]["success"] is True


@pytest.mark.anyio
async def test_execute_test_case_returns_runner_final_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Task 3: `execute_test_case()` must consume runner events and return the runner's final_result,
    not a separately computed execution summary.
    """
    from backend.plugin.api_testing.service.test_case_execution_runner import TestCaseExecutionRunner
    from backend.plugin.api_testing.service.test_case_execution_service import TestCaseExecutionService

    created: dict[str, TestCaseExecutionRunner] = {}

    original_init = TestCaseExecutionRunner.__init__

    def capturing_init(self: TestCaseExecutionRunner, *, case_id: int, environment_id: int | None = None) -> None:
        original_init(self, case_id=case_id, environment_id=environment_id)
        created["runner"] = self

    async def fake_run(self: TestCaseExecutionRunner):  # noqa: ANN001
        self.final_result = {"case_id": self.case_id, "success": True, "sentinel": "runner"}
        yield {"type": "run_start", "case_id": self.case_id}
        yield {"type": "run_end", **self.final_result}

    # Patch runner so the service path can be tested without hitting DB/services.
    monkeypatch.setattr(TestCaseExecutionRunner, "__init__", capturing_init)
    monkeypatch.setattr(TestCaseExecutionRunner, "run", fake_run)

    result = await TestCaseExecutionService.execute_test_case(case_id=1, environment_id=None)

    assert "runner" in created
    assert result is created["runner"].final_result
    assert result.get("sentinel") == "runner"


@pytest.mark.anyio
async def test_runner_assertion_sql_and_extract_affect_step_success_and_final_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.plugin.api_testing.service.test_case_execution_runner import TestCaseExecutionRunner, _ExecutionContext

    async def fake_load_context(self: TestCaseExecutionRunner) -> _ExecutionContext:
        return _ExecutionContext(
            case=SimpleNamespace(id=self.case_id, name="Demo Case", project_id=10),
            project=SimpleNamespace(id=10, base_url="https://project.example", headers={}, variables={}),
            environment=SimpleNamespace(id=3, name="dev", variables={"base_url": "https://env.example"}),
            resolved_environment_id=3,
            base_url="https://env.example",
            base_headers={},
            steps=[
                {
                    "id": 1,
                    "name": "Step 1",
                    "order": 1,
                    "method": "GET",
                    "url": "/ping",
                    "headers": {},
                    "params": {},
                    "body": None,
                    "timeout": 30,
                    "retry": 0,
                    "retry_interval": 1,
                    "validate": [
                        {"source": "status_code", "type": "equals", "expected": 200},
                        {"source": "status_code", "type": "equals", "expected": 201},
                    ],
                    "sql_queries": [
                        {"name": "broken", "query": "select 1"},
                    ],
                    "extract": {"token": "$.token"},
                }
            ],
            temp_variables={},
        )

    async def fake_send_request(**kwargs):  # noqa: ANN003
        return SimpleNamespace(
            status_code=200,
            headers={},
            cookies={},
            json_data={"token": "abc"},
            text="ok",
            elapsed_time=5,
            error=None,
            model_dump=lambda: {
                "status_code": 200,
                "headers": {},
                "cookies": {},
                "json_data": {"token": "abc"},
                "text": "ok",
                "elapsed_time": 5,
                "error": None,
            },
        )

    async def fake_execute_query(sql_query):  # noqa: ANN001
        # Simulate SQL failure; runner should mark step failed and include this result.
        return SimpleNamespace(
            success=False,
            extracted_variables=None,
            model_dump=lambda: {"name": sql_query.name, "query": sql_query.query, "success": False},
        )

    async def fake_persist_report(self, **kwargs):  # noqa: ANN001, ANN003
        return SimpleNamespace(id=888), "demo-report"

    monkeypatch.setattr(TestCaseExecutionRunner, "_load_context", fake_load_context)
    monkeypatch.setattr("backend.plugin.api_testing.service.test_case_execution_runner.send_request", fake_send_request)
    monkeypatch.setattr(
        "backend.plugin.api_testing.service.test_case_execution_runner.SQLExecutor.execute_query",
        fake_execute_query,
    )
    monkeypatch.setattr(TestCaseExecutionRunner, "_persist_report", fake_persist_report)

    runner = TestCaseExecutionRunner(case_id=1, environment_id=None)
    events: list[dict] = []
    async for event in runner.run():
        events.append(event)

    step_end = next(e for e in events if e["type"] == "step_end")
    assert step_end["success"] is False
    step_result = runner.final_result["details"]["steps"][0]
    assert any(a.get("success") is False for a in (step_result.get("assertions") or []))
    assert any(r.get("success") is False for r in (step_result.get("sql_results") or []))
    assert step_result.get("variables", {}).get("token") == "abc"
    assert runner.final_result is not None
    assert runner.final_result["success"] is False


@pytest.mark.anyio
async def test_runner_propagates_extracted_variables_to_subsequent_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.plugin.api_testing.service.test_case_execution_runner import TestCaseExecutionRunner, _ExecutionContext

    async def fake_load_context(self: TestCaseExecutionRunner) -> _ExecutionContext:
        return _ExecutionContext(
            case=SimpleNamespace(id=self.case_id, name="Demo Case", project_id=10),
            project=SimpleNamespace(id=10, base_url="https://env.example", headers={}, variables={}),
            environment=SimpleNamespace(id=3, name="dev", variables={"base_url": "https://env.example"}),
            resolved_environment_id=3,
            base_url="https://env.example",
            base_headers={},
            steps=[
                {"id": 1, "name": "Step 1", "order": 1, "method": "GET", "url": "/token", "extract": {"token": "$.token"}},
                {"id": 2, "name": "Step 2", "order": 2, "method": "GET", "url": "/echo/{{token}}"},
            ],
            temp_variables={},
        )

    seen_urls: list[str] = []

    async def fake_send_request(**kwargs):  # noqa: ANN003
        seen_urls.append(str(kwargs.get("url")))
        url = str(kwargs.get("url"))
        if url.endswith("/token"):
            json_data = {"token": "t-123"}
        else:
            json_data = {"ok": True}
        return SimpleNamespace(
            status_code=200,
            headers={},
            cookies={},
            json_data=json_data,
            text="ok",
            elapsed_time=1,
            error=None,
            model_dump=lambda: {
                "status_code": 200,
                "headers": {},
                "cookies": {},
                "json_data": json_data,
                "text": "ok",
                "elapsed_time": 1,
                "error": None,
            },
        )

    monkeypatch.setattr(TestCaseExecutionRunner, "_load_context", fake_load_context)
    monkeypatch.setattr("backend.plugin.api_testing.service.test_case_execution_runner.send_request", fake_send_request)

    runner = TestCaseExecutionRunner(case_id=1, environment_id=None)
    async for _event in runner.run():
        pass

    assert any(url.endswith("/echo/t-123") for url in seen_urls)


@pytest.mark.anyio
async def test_runner_emits_assertion_sql_extract_events_and_run_end_report(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.plugin.api_testing.service.test_case_execution_runner import TestCaseExecutionRunner, _ExecutionContext

    async def fake_load_context(self: TestCaseExecutionRunner) -> _ExecutionContext:
        return _ExecutionContext(
            case=SimpleNamespace(id=self.case_id, name="Demo Case", project_id=10),
            project=SimpleNamespace(id=10, base_url="https://project.example", headers={}, variables={}),
            environment=SimpleNamespace(id=3, name="dev", variables={"base_url": "https://env.example"}),
            resolved_environment_id=3,
            base_url="https://env.example",
            base_headers={},
            steps=[
                {
                    "id": 1,
                    "name": "Step 1",
                    "order": 1,
                    "method": "GET",
                    "url": "/ping",
                    "headers": {},
                    "params": {},
                    "body": None,
                    "timeout": 30,
                    "retry": 0,
                    "retry_interval": 1,
                    "validate": [
                        {"source": "status_code", "type": "equals", "expected": 200},
                    ],
                    "sql_queries": [
                        {"name": "load_user", "query": "select 1"},
                    ],
                    "extract": {"token": "$.token"},
                }
            ],
            temp_variables={},
        )

    async def fake_send_request(**kwargs):  # noqa: ANN003
        return SimpleNamespace(
            status_code=200,
            headers={},
            cookies={},
            json_data={"token": "abc"},
            text="ok",
            elapsed_time=5,
            error=None,
            model_dump=lambda: {
                "status_code": 200,
                "headers": {},
                "cookies": {},
                "json_data": {"token": "abc"},
                "text": "ok",
                "elapsed_time": 5,
                "error": None,
            },
        )

    async def fake_execute_query(sql_query):  # noqa: ANN001
        return SimpleNamespace(
            success=True,
            extracted_variables={"db_token": "sql-1"},
            model_dump=lambda: {
                "sql": {"name": sql_query.name},
                "success": True,
                "extracted_variables": {"db_token": "sql-1"},
            },
        )

    async def fake_create_test_report(report_data):  # noqa: ANN001
        assert report_data.success is True
        return SimpleNamespace(id=321)

    monkeypatch.setattr(TestCaseExecutionRunner, "_load_context", fake_load_context)
    monkeypatch.setattr("backend.plugin.api_testing.service.test_case_execution_runner.send_request", fake_send_request)
    monkeypatch.setattr(
        "backend.plugin.api_testing.service.test_case_execution_runner.SQLExecutor.execute_query",
        fake_execute_query,
    )
    monkeypatch.setattr(
        "backend.plugin.api_testing.service.test_case_execution_runner.TestReportService.create_test_report",
        fake_create_test_report,
    )

    runner = TestCaseExecutionRunner(case_id=1, environment_id=None)
    events = [event async for event in runner.run()]
    event_types = [event["type"] for event in events]

    assert "step_assertion" in event_types
    assert "step_sql" in event_types
    assert "step_extract" in event_types
    assert events[-1]["type"] == "run_end"
    assert events[-1]["report_id"] == 321
    assert runner.final_result is not None
    assert runner.final_result["report_id"] == 321


@pytest.mark.anyio
async def test_runner_emits_error_when_report_creation_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.plugin.api_testing.service.test_case_execution_runner import TestCaseExecutionRunner, _ExecutionContext

    async def fake_load_context(self: TestCaseExecutionRunner) -> _ExecutionContext:
        return _ExecutionContext(
            case=SimpleNamespace(id=self.case_id, name="Demo Case", project_id=10),
            project=SimpleNamespace(id=10, base_url="https://project.example", headers={}, variables={}),
            environment=SimpleNamespace(id=3, name="dev", variables={"base_url": "https://env.example"}),
            resolved_environment_id=3,
            base_url="https://env.example",
            base_headers={},
            steps=[
                {
                    "id": 1,
                    "name": "Step 1",
                    "order": 1,
                    "method": "GET",
                    "url": "/ping",
                }
            ],
            temp_variables={},
        )

    async def fake_send_request(**kwargs):  # noqa: ANN003
        return SimpleNamespace(
            status_code=200,
            headers={},
            cookies={},
            json_data={"ok": True},
            text="ok",
            elapsed_time=5,
            error=None,
            model_dump=lambda: {"status_code": 200, "error": None, "elapsed_time": 5},
        )

    async def fake_create_test_report(report_data):  # noqa: ANN001
        raise RuntimeError("report failed")

    monkeypatch.setattr(TestCaseExecutionRunner, "_load_context", fake_load_context)
    monkeypatch.setattr("backend.plugin.api_testing.service.test_case_execution_runner.send_request", fake_send_request)
    monkeypatch.setattr(
        "backend.plugin.api_testing.service.test_case_execution_runner.TestReportService.create_test_report",
        fake_create_test_report,
    )

    runner = TestCaseExecutionRunner(case_id=1, environment_id=None)
    events = [event async for event in runner.run()]

    assert events[-1]["type"] == "error"
    assert events[-1]["message"] == "report failed"
    assert all(event["type"] != "run_end" for event in events)
