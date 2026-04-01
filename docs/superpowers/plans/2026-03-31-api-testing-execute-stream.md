# API Testing Execute Stream Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new NDJSON streaming execute endpoint for API testing test cases so the frontend can render live run logs while preserving the existing synchronous `/execute` contract.

**Architecture:** Introduce a shared test-case execution runner that emits structured events while collecting the final report payload. The new `/execute/stream` endpoint will serialize those events as `application/x-ndjson`, while the existing `/execute` endpoint will consume the same runner and return only the final summary. Keep request execution, assertions, SQL execution, and variable extraction semantics aligned with the current behavior.

**Tech Stack:** FastAPI, StreamingResponse, async generators, pytest, monkeypatch-based route/service tests

---

### File Map

**Create:**
- `backend/plugin/api_testing/service/test_case_execution_runner.py` - shared execution runner that emits structured events and accumulates final report data
- `backend/plugin/api_testing/tests/test_test_case_execution_runner.py` - service-level tests for event ordering, failure handling, and summary accumulation
- `backend/plugin/api_testing/tests/test_test_case_stream_api.py` - route-level tests for NDJSON streaming behavior and stream error handling

**Modify:**
- `backend/plugin/api_testing/service/test_case_execution_service.py` - consume the new runner for the existing synchronous `/execute` path
- `backend/plugin/api_testing/api/v1/test_case.py` - add `POST /{case_id}/execute/stream` and route serialization helpers

**Check for reuse:**
- `backend/plugin/api_testing/utils/report_generator.py`
- `backend/plugin/api_testing/tests/test_sql_async_api.py`
- `backend/plugin/api_testing/tests/test_batch_execution_service.py`

### Task 1: Add The Streaming Route Contract

**Files:**
- Modify: `backend/plugin/api_testing/api/v1/test_case.py`
- Create: `backend/plugin/api_testing/tests/test_test_case_stream_api.py`

- [ ] **Step 1: Write the failing test**

```python
import json

import pytest
from fastapi.responses import StreamingResponse

from backend.plugin.api_testing.api.v1.test_case import execute_test_case_stream


@pytest.mark.anyio
async def test_execute_test_case_stream_returns_ndjson_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_stream(case_id: int, environment_id: int | None = None):
        assert case_id == 7
        assert environment_id == 3
        yield {"type": "run_start", "case_id": 7}
        yield {"type": "run_end", "case_id": 7, "success": True}

    monkeypatch.setattr(
        "backend.plugin.api_testing.api.v1.test_case.TestCaseExecutionService.stream_test_case_execution",
        fake_stream,
    )

    response = await execute_test_case_stream(case_id=7, environment_id=3)

    assert isinstance(response, StreamingResponse)
    assert response.media_type == "application/x-ndjson"

    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk)

    payloads = [json.loads(line) for line in "".join(chunks).splitlines()]
    assert [item["type"] for item in payloads] == ["run_start", "run_end"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/plugin/api_testing/tests/test_test_case_stream_api.py -q`
Expected: FAIL because `execute_test_case_stream()` and `stream_test_case_execution()` do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
@router.post("/{case_id}/execute/stream", summary="流式执行测试用例")
async def execute_test_case_stream(
    case_id: int = Path(..., description="测试用例ID"),
    environment_id: Optional[int] = Query(None, description="环境ID"),
):
    async def event_iterator():
        async for event in TestCaseExecutionService.stream_test_case_execution(case_id, environment_id):
            yield json.dumps(event, ensure_ascii=False) + "\n"

    return StreamingResponse(
        event_iterator(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/plugin/api_testing/tests/test_test_case_stream_api.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/plugin/api_testing/api/v1/test_case.py backend/plugin/api_testing/tests/test_test_case_stream_api.py
git commit -m "feat: add api testing execute stream route"
```

### Task 2: Introduce A Shared Execution Runner

**Files:**
- Create: `backend/plugin/api_testing/service/test_case_execution_runner.py`
- Create: `backend/plugin/api_testing/tests/test_test_case_execution_runner.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest

from backend.plugin.api_testing.service.test_case_execution_runner import TestCaseExecutionRunner


@pytest.mark.anyio
async def test_runner_emits_run_and_step_events_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_load_context(case_id: int, environment_id: int | None):
        return {
            "test_case": type("Case", (), {"id": 9, "name": "demo", "project_id": 1})(),
            "project": type("Project", (), {"id": 1, "name": "proj", "base_url": "https://example.com", "headers": {}, "variables": {}})(),
            "environment": None,
            "steps": [type("Step", (), {"name": "get user", "order": 1, "url": "/users/1", "method": "GET", "headers": None, "params": None, "body": None, "timeout": 30, "retry": 0, "retry_interval": 1, "validate": [], "sql_queries": [], "extract": None})()],
        }

    async def fake_execute_step(step, context):  # noqa: ANN001
        return {
            "step_result": {"name": step.name, "order": step.order, "success": True, "duration": 12},
            "events": [
                {"type": "step_start", "step_order": 1, "step_name": "get user"},
                {"type": "step_request", "step_order": 1, "step_name": "get user"},
                {"type": "step_response", "step_order": 1, "step_name": "get user", "success": True},
                {"type": "step_end", "step_order": 1, "step_name": "get user", "success": True, "duration": 12},
            ],
        }

    monkeypatch.setattr(TestCaseExecutionRunner, "_load_context", staticmethod(fake_load_context))
    monkeypatch.setattr(TestCaseExecutionRunner, "_execute_step", staticmethod(fake_execute_step))

    runner = TestCaseExecutionRunner(case_id=9, environment_id=None)
    events = [event async for event in runner.run()]

    assert events[0]["type"] == "run_start"
    assert [event["type"] for event in events[1:5]] == ["step_start", "step_request", "step_response", "step_end"]
    assert events[-1]["type"] == "run_end"
    assert runner.final_result["success"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/plugin/api_testing/tests/test_test_case_execution_runner.py -q`
Expected: FAIL because the runner module/class does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
class TestCaseExecutionRunner:
    def __init__(self, case_id: int, environment_id: int | None = None) -> None:
        self.case_id = case_id
        self.environment_id = environment_id
        self.final_result: dict[str, Any] | None = None

    async def run(self) -> AsyncIterator[dict[str, Any]]:
        context = await self._load_context(self.case_id, self.environment_id)
        yield self._build_run_start_event(context)

        step_results = []
        for step in context["steps"]:
            outcome = await self._execute_step(step, context)
            for event in outcome["events"]:
                yield event
            step_results.append(outcome["step_result"])

        self.final_result = self._build_run_end_payload(context, step_results)
        yield self.final_result["event"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/plugin/api_testing/tests/test_test_case_execution_runner.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/plugin/api_testing/service/test_case_execution_runner.py backend/plugin/api_testing/tests/test_test_case_execution_runner.py
git commit -m "feat: add api testing execution runner"
```

### Task 3: Move Existing `/execute` Onto The Runner

**Files:**
- Modify: `backend/plugin/api_testing/service/test_case_execution_service.py`
- Modify: `backend/plugin/api_testing/service/test_case_execution_runner.py`
- Modify: `backend/plugin/api_testing/tests/test_test_case_execution_runner.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest

from backend.plugin.api_testing.service.test_case_execution_service import TestCaseExecutionService


@pytest.mark.anyio
async def test_execute_test_case_returns_runner_final_result(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeRunner:
        def __init__(self, case_id: int, environment_id: int | None = None) -> None:
            self.case_id = case_id
            self.environment_id = environment_id
            self.final_result = {
                "case_id": 11,
                "report_id": 101,
                "success": True,
                "details": {"steps": []},
            }

        async def run(self):
            yield {"type": "run_start"}
            yield {"type": "run_end"}

    monkeypatch.setattr(
        "backend.plugin.api_testing.service.test_case_execution_service.TestCaseExecutionRunner",
        FakeRunner,
    )

    result = await TestCaseExecutionService.execute_test_case(11, 2)

    assert result["case_id"] == 11
    assert result["report_id"] == 101
    assert result["success"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/plugin/api_testing/tests/test_test_case_execution_runner.py -q`
Expected: FAIL because `execute_test_case()` still uses the old inline implementation.

- [ ] **Step 3: Write minimal implementation**

```python
@staticmethod
async def execute_test_case(case_id: int, environment_id: Optional[int] = None) -> dict[str, Any]:
    runner = TestCaseExecutionRunner(case_id=case_id, environment_id=environment_id)
    async for _event in runner.run():
        pass
    if runner.final_result is None:
        raise RuntimeError("测试执行未产生最终结果")
    return runner.final_result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/plugin/api_testing/tests/test_test_case_execution_runner.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/plugin/api_testing/service/test_case_execution_service.py backend/plugin/api_testing/service/test_case_execution_runner.py backend/plugin/api_testing/tests/test_test_case_execution_runner.py
git commit -m "refactor: route test case execute through shared runner"
```

### Task 4: Fill In Per-Step Event Emission And Failure Semantics

**Files:**
- Modify: `backend/plugin/api_testing/service/test_case_execution_runner.py`
- Modify: `backend/plugin/api_testing/tests/test_test_case_execution_runner.py`

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.anyio
async def test_runner_emits_assertion_sql_and_extract_events(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = TestCaseExecutionRunner(case_id=1, environment_id=None)
    monkeypatch.setattr(runner, "_load_context", fake_context_with_assertions_sql_and_extract)
    monkeypatch.setattr(runner, "_send_request", fake_send_request)
    monkeypatch.setattr(runner, "_execute_sql_query", fake_sql_result)

    events = [event async for event in runner.run()]

    assert "step_assertion" in [event["type"] for event in events]
    assert "step_sql" in [event["type"] for event in events]
    assert "step_extract" in [event["type"] for event in events]


@pytest.mark.anyio
async def test_runner_emits_error_when_report_creation_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = TestCaseExecutionRunner(case_id=1, environment_id=None)
    monkeypatch.setattr(runner, "_load_context", fake_context)
    monkeypatch.setattr(runner, "_persist_report", fake_raise_report_error)

    events = [event async for event in runner.run()]

    assert events[-1]["type"] == "error"
    assert all(event["type"] != "run_end" for event in events)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/plugin/api_testing/tests/test_test_case_execution_runner.py -q`
Expected: FAIL because the runner only emits the minimal placeholder events.

- [ ] **Step 3: Write minimal implementation**

```python
for assertion_result in step_assertions:
    yield self._event("step_assertion", step=step, success=assertion_result["success"], assertion=assertion_result["assertion"], actual=assertion_result["actual"], message=assertion_result["message"])

for sql_result in step_sql_results:
    yield self._event("step_sql", step=step, sql_name=sql_result["sql"]["name"], success=sql_result["success"], message=sql_result.get("error"), extracted_variables=sql_result.get("extracted_variables") or {})

for variable_name, value in step_variables.items():
    yield self._event("step_extract", step=step, variable_name=variable_name, success=True, value=value, message="变量提取成功")

try:
    saved_report = await self._persist_report(...)
except Exception as exc:
    self.final_result = None
    yield self._event("error", message=str(exc), error_type=type(exc).__name__)
    return
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/plugin/api_testing/tests/test_test_case_execution_runner.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/plugin/api_testing/service/test_case_execution_runner.py backend/plugin/api_testing/tests/test_test_case_execution_runner.py
git commit -m "feat: emit detailed api testing stream events"
```

### Task 5: Harden NDJSON Serialization And Route Error Behavior

**Files:**
- Modify: `backend/plugin/api_testing/api/v1/test_case.py`
- Modify: `backend/plugin/api_testing/tests/test_test_case_stream_api.py`

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.anyio
async def test_execute_test_case_stream_serializes_unicode_and_newlines(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_stream(case_id: int, environment_id: int | None = None):
        yield {"type": "step_end", "message": "完成\\n下一行", "label": "中文"}

    monkeypatch.setattr(
        "backend.plugin.api_testing.api.v1.test_case.TestCaseExecutionService.stream_test_case_execution",
        fake_stream,
    )

    response = await execute_test_case_stream(case_id=1, environment_id=None)
    body = ""
    async for chunk in response.body_iterator:
        body += chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk

    assert body.endswith("\\n")
    assert json.loads(body.splitlines()[0])["label"] == "中文"


@pytest.mark.anyio
async def test_execute_test_case_stream_wraps_unhandled_generator_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_stream(case_id: int, environment_id: int | None = None):
        raise RuntimeError("boom")
        yield

    monkeypatch.setattr(
        "backend.plugin.api_testing.api.v1.test_case.TestCaseExecutionService.stream_test_case_execution",
        fake_stream,
    )

    response = await execute_test_case_stream(case_id=1, environment_id=None)
    body = ""
    async for chunk in response.body_iterator:
        body += chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk

    payloads = [json.loads(line) for line in body.splitlines()]
    assert payloads[-1]["type"] == "error"
    assert payloads[-1]["message"] == "boom"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/plugin/api_testing/tests/test_test_case_stream_api.py -q`
Expected: FAIL because the route does not yet normalize generator exceptions into terminal NDJSON error events.

- [ ] **Step 3: Write minimal implementation**

```python
async def event_iterator():
    try:
        async for event in TestCaseExecutionService.stream_test_case_execution(case_id, environment_id):
            yield json.dumps(make_serializable(event), ensure_ascii=False) + "\n"
    except Exception as exc:  # noqa: BLE001
        yield json.dumps(
            {
                "type": "error",
                "timestamp": datetime.now().isoformat(),
                "case_id": case_id,
                "environment_id": environment_id,
                "message": str(exc),
                "error_type": type(exc).__name__,
            },
            ensure_ascii=False,
        ) + "\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/plugin/api_testing/tests/test_test_case_stream_api.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/plugin/api_testing/api/v1/test_case.py backend/plugin/api_testing/tests/test_test_case_stream_api.py
git commit -m "fix: harden api testing execute stream serialization"
```

### Task 6: Run Focused Regression Coverage

**Files:**
- Test: `backend/plugin/api_testing/tests/test_test_case_stream_api.py`
- Test: `backend/plugin/api_testing/tests/test_test_case_execution_runner.py`
- Test: `backend/plugin/api_testing/tests/test_sql_async_api.py`
- Test: `backend/plugin/api_testing/tests/test_request_engine.py`
- Test: `backend/plugin/api_testing/tests/test_batch_execution_service.py`

- [ ] **Step 1: Run the new stream route tests**

Run: `pytest backend/plugin/api_testing/tests/test_test_case_stream_api.py -q`
Expected: PASS

- [ ] **Step 2: Run the new runner tests**

Run: `pytest backend/plugin/api_testing/tests/test_test_case_execution_runner.py -q`
Expected: PASS

- [ ] **Step 3: Run regression tests around existing execution helpers**

Run: `pytest backend/plugin/api_testing/tests/test_request_engine.py backend/plugin/api_testing/tests/test_batch_execution_service.py backend/plugin/api_testing/tests/test_sql_async_api.py -q`
Expected: PASS

- [ ] **Step 4: Run a combined focused suite**

Run: `pytest backend/plugin/api_testing/tests/test_test_case_stream_api.py backend/plugin/api_testing/tests/test_test_case_execution_runner.py backend/plugin/api_testing/tests/test_request_engine.py backend/plugin/api_testing/tests/test_batch_execution_service.py backend/plugin/api_testing/tests/test_sql_async_api.py -q`
Expected: PASS

- [ ] **Step 5: Commit final verification updates**

```bash
git add backend/plugin/api_testing/tests
git commit -m "test: cover api testing execute stream flow"
```
