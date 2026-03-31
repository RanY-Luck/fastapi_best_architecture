from types import SimpleNamespace

import pytest

from backend.plugin.api_testing.api.v1.sql import execute_sql_query, get_sql_task_status
from backend.plugin.api_testing.utils.sql_executor import SQLQuery


@pytest.mark.anyio
async def test_execute_sql_query_returns_task_id(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_create_task(query: SQLQuery):
        assert query.name == 'users'
        return SimpleNamespace(task_id='task-1', celery_task_id=None, status='pending', name='users')

    class FakeDelayResult:
        id = 'celery-1'

    class FakeCeleryTask:
        @staticmethod
        def delay(task_id: str):
            assert task_id == 'task-1'
            return FakeDelayResult()

    async def fake_bind_celery_task_id(task_id: str, celery_task_id: str):
        assert task_id == 'task-1'
        assert celery_task_id == 'celery-1'
        return SimpleNamespace(task_id='task-1', celery_task_id='celery-1', status='pending', name='users')

    monkeypatch.setattr('backend.plugin.api_testing.api.v1.sql.SqlTaskService.create_task', fake_create_task)
    monkeypatch.setattr('backend.plugin.api_testing.api.v1.sql.SqlTaskService.bind_celery_task_id', fake_bind_celery_task_id)
    monkeypatch.setattr('backend.plugin.api_testing.api.v1.sql.execute_api_testing_sql', FakeCeleryTask())

    response = await execute_sql_query(SQLQuery(name='users', query='SELECT 1'))

    assert response['code'] == 200
    assert response['data']['task_id'] == 'task-1'
    assert response['data']['celery_task_id'] == 'celery-1'
    assert response['data']['status'] == 'pending'


@pytest.mark.anyio
async def test_get_sql_task_status_returns_completed_result(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get_by_task_id(task_id: str):
        assert task_id == 'task-1'
        return SimpleNamespace(
            task_id='task-1',
            celery_task_id='celery-1',
            status='success',
            name='users',
            result={'success': True, 'data': [{'id': 1}]},
            error=None,
            duration=120,
            start_time=None,
            end_time=None,
        )

    monkeypatch.setattr('backend.plugin.api_testing.api.v1.sql.SqlTaskService.get_by_task_id', fake_get_by_task_id)

    response = await get_sql_task_status('task-1')

    assert response.code == 200
    assert response.data['status'] == 'success'
    assert response.data['result']['success'] is True
