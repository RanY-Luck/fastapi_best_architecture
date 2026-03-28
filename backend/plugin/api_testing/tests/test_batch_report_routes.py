from datetime import datetime
from types import SimpleNamespace

import pytest


from backend.plugin.api_testing.api.v1.test_report import (
    get_batch_execution_report,
    get_batch_execution_reports,
)


@pytest.mark.anyio
async def test_get_batch_execution_reports_returns_aggregate_items(monkeypatch: pytest.MonkeyPatch) -> None:
    batch_report = SimpleNamespace(
        id=11,
        project_id=3,
        suite_id=7,
        name='nightly-run',
        target_type='suite',
        success=1,
        total_cases=5,
        success_cases=4,
        fail_cases=1,
        max_concurrency=3,
        start_time=datetime(2026, 3, 27, 10, 0, 0),
        end_time=datetime(2026, 3, 27, 10, 1, 0),
        duration=60000,
        details={'report_ids': [101, 102]},
        created_time=datetime(2026, 3, 27, 10, 1, 0),
        project=SimpleNamespace(name='demo-project'),
        suite=SimpleNamespace(name='smoke-suite'),
    )

    async def fake_get_batch_execution_reports(**kwargs):  # noqa: ANN003
        assert kwargs['project_id'] == 3
        assert kwargs['suite_id'] == 7
        assert kwargs['target_type'] == 'suite'
        return [batch_report]

    async def fake_get_batch_execution_report_count(**kwargs):  # noqa: ANN003
        return 1

    monkeypatch.setattr(
        'backend.plugin.api_testing.service.test_report_service.TestReportService.get_batch_execution_reports',
        fake_get_batch_execution_reports,
    )
    monkeypatch.setattr(
        'backend.plugin.api_testing.service.test_report_service.TestReportService.get_batch_execution_report_count',
        fake_get_batch_execution_report_count,
    )

    response = await get_batch_execution_reports(
        project_id=3,
        suite_id=7,
        target_type='suite',
        start_date='2026-03-27',
        end_date='2026-03-27',
        success_only=True,
        skip=0,
        limit=20,
    )

    assert response.code == 200
    assert response.data['total'] == 1
    assert response.data['items'][0]['project_name'] == 'demo-project'
    assert response.data['items'][0]['suite_name'] == 'smoke-suite'
    assert response.data['items'][0]['report_ids'] == [101, 102]


@pytest.mark.anyio
async def test_get_batch_execution_report_returns_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get_batch_execution_report_by_id(report_id: int):
        assert report_id == 99
        return None

    monkeypatch.setattr(
        'backend.plugin.api_testing.service.test_report_service.TestReportService.get_batch_execution_report_by_id',
        fake_get_batch_execution_report_by_id,
    )

    response = await get_batch_execution_report(99)

    assert response.code == 400
    assert response.data == '批量执行报告不存在'
