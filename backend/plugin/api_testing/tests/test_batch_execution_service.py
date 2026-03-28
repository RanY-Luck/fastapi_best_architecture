import asyncio

import pytest


from backend.plugin.api_testing.service.test_batch_execution_service import BatchExecutionService


@pytest.mark.anyio
async def test_execute_cases_aggregates_results_and_honors_concurrency_limit() -> None:
    active = 0
    max_active = 0

    async def execute_case(case_id: int) -> dict:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        return {
            'case_id': case_id,
            'success': case_id != 2,
            'report_id': case_id * 10,
            'duration': case_id * 100,
        }

    result = await BatchExecutionService.execute_cases(
        case_ids=[1, 2, 3],
        execute_case=execute_case,
        max_concurrency=2,
    )

    assert result['total_cases'] == 3
    assert result['success_cases'] == 2
    assert result['fail_cases'] == 1
    assert result['success'] is False
    assert result['case_report_ids'] == [10, 20, 30]
    assert result['results'][1]['case_id'] == 2
    assert max_active <= 2


@pytest.mark.anyio
async def test_execute_cases_defaults_concurrency_to_one() -> None:
    observed = []

    async def execute_case(case_id: int) -> dict:
        observed.append(case_id)
        return {
            'case_id': case_id,
            'success': True,
            'report_id': None,
            'duration': 1,
        }

    result = await BatchExecutionService.execute_cases(
        case_ids=[7, 8],
        execute_case=execute_case,
        max_concurrency=0,
    )

    assert observed == [7, 8]
    assert result['success'] is True
