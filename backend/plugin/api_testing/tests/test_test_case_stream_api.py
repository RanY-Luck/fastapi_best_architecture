import json
from collections.abc import AsyncIterator, Callable
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from backend.plugin.api_testing.api.v1.test_case import router
from backend.plugin.api_testing.service.test_case_execution_service import TestCaseExecutionService


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api_testing/test_cases")
    return app


def _stream_expected_events(
    case_id: int,
    environment_id: int,
    expected_events: list[dict[str, Any]],
) -> Callable[[int, Optional[int]], AsyncIterator[dict[str, Any]]]:
    async def fake_stream(inner_case_id: int, inner_environment_id: Optional[int]) -> AsyncIterator[dict[str, Any]]:
        assert inner_case_id == case_id
        assert inner_environment_id == environment_id
        for event in expected_events:
            yield event

    return fake_stream

def test_stream_execute_test_case_yields_ndjson(monkeypatch: pytest.MonkeyPatch) -> None:
    case_id = 123
    environment_id = 456
    expected_events = [
        {"type": "run_start"},
        {"type": "run_end"},
    ]

    fake_stream = _stream_expected_events(case_id, environment_id, expected_events)

    monkeypatch.setattr(
        TestCaseExecutionService,
        "stream_test_case_execution",
        fake_stream,
    )

    app = _build_app()
    url = f"/api_testing/test_cases/{case_id}/execute/stream"
    expected_lines = [json.dumps(event, ensure_ascii=False) for event in expected_events]

    with TestClient(app) as client:
        with client.stream("POST", url, params={"environment_id": environment_id}) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].split(";", 1)[0] == "application/x-ndjson"
            assert response.headers["cache-control"] == "no-cache"
            assert response.headers["x-accel-buffering"] == "no"
            streamed_lines = [
                line.decode("utf-8") if isinstance(line, (bytes, bytearray)) else line
                for line in response.iter_lines()
            ]

    assert streamed_lines == expected_lines


def test_stream_execute_test_case_yields_error_event_when_stream_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    case_id = 123
    environment_id = 456

    async def failing_stream(inner_case_id: int, inner_environment_id: Optional[int]) -> AsyncIterator[dict[str, Any]]:
        assert inner_case_id == case_id
        assert inner_environment_id == environment_id
        yield {"type": "run_start"}
        raise RuntimeError("boom")

    monkeypatch.setattr(
        TestCaseExecutionService,
        "stream_test_case_execution",
        failing_stream,
    )

    app = _build_app()
    url = f"/api_testing/test_cases/{case_id}/execute/stream"

    with TestClient(app) as client:
        with client.stream("POST", url, params={"environment_id": environment_id}) as response:
            assert response.status_code == 200
            streamed_lines = [
                line.decode("utf-8") if isinstance(line, (bytes, bytearray)) else line
                for line in response.iter_lines()
            ]

    events = [json.loads(line) for line in streamed_lines]
    assert events[0]["type"] == "run_start"
    assert events[-1]["type"] == "error"
    assert events[-1]["message"] == "boom"
    assert events[-1]["error_type"] == "RuntimeError"


def test_stream_execute_test_case_preserves_unicode_and_newlines(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_stream(inner_case_id: int, inner_environment_id: Optional[int]) -> AsyncIterator[dict[str, Any]]:
        assert inner_case_id == 1
        assert inner_environment_id is None
        yield {"type": "step_end", "message": "完成\n下一行", "label": "中文"}

    monkeypatch.setattr(
        TestCaseExecutionService,
        "stream_test_case_execution",
        fake_stream,
    )

    app = _build_app()

    with TestClient(app) as client:
        with client.stream("POST", "/api_testing/test_cases/1/execute/stream") as response:
            assert response.status_code == 200
            body_lines = [
                line.decode("utf-8") if isinstance(line, (bytes, bytearray)) else line
                for line in response.iter_lines()
            ]

    assert len(body_lines) == 1
    assert json.loads(body_lines[0])["label"] == "中文"
    assert json.loads(body_lines[0])["message"] == "完成\n下一行"
