from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from datetime import datetime
from types import SimpleNamespace

import pytest

from backend.plugin.api_testing.utils.sql_executor import SQLQuery
from backend.plugin.api_testing.service.sql_task_service import SqlTaskService


class FakeSession:
    def __init__(self) -> None:
        self.items = {}
        self.counter = 0

    def add(self, obj) -> None:  # noqa: ANN001
        self.counter += 1
        if getattr(obj, 'id', None) is None:
            obj.id = self.counter
        self.items[obj.task_id] = obj

    async def commit(self) -> None:
        return None

    async def refresh(self, obj) -> None:  # noqa: ANN001
        return None

    async def execute(self, statement):  # noqa: ANN001
        task_id = statement.compile().params.get('task_id_1')
        return SimpleNamespace(scalar_one_or_none=lambda: self.items.get(task_id))


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self.session = session

    async def __aenter__(self) -> FakeSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None


@pytest.mark.anyio
async def test_create_sql_task_defaults_to_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession()
    monkeypatch.setattr(
        'backend.plugin.api_testing.service.sql_task_service.async_db_session',
        lambda: FakeSessionManager(session),
    )

    task = await SqlTaskService.create_task(
        SQLQuery(name='users', query='SELECT 1'),
        celery_task_id='celery-1',
    )

    assert task.status == 'pending'
    assert task.result is None
    assert task.celery_task_id == 'celery-1'


@pytest.mark.anyio
async def test_mark_sql_task_running_and_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession()
    monkeypatch.setattr(
        'backend.plugin.api_testing.service.sql_task_service.async_db_session',
        lambda: FakeSessionManager(session),
    )

    task = await SqlTaskService.create_task(
        SQLQuery(name='users', query='SELECT 1'),
        celery_task_id='celery-2',
    )

    await SqlTaskService.mark_running(task.task_id, start_time=datetime(2026, 3, 28, 10, 0, 0))
    await SqlTaskService.mark_completed(
        task.task_id,
        result={'success': True, 'rows': []},
        end_time=datetime(2026, 3, 28, 10, 0, 1),
        duration=1000,
    )

    refreshed = await SqlTaskService.get_by_task_id(task.task_id)

    assert refreshed.status == 'success'
    assert refreshed.result == {'success': True, 'rows': []}
    assert refreshed.duration == 1000

