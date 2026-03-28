#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API测试批量执行服务
"""
import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from sqlalchemy import select

from backend.database.db import async_db_session
from backend.plugin.api_testing.model.models import ApiBatchExecutionReport
from backend.plugin.api_testing.service.project_service import ProjectService
from backend.plugin.api_testing.service.test_case_execution_service import TestCaseExecutionService
from backend.plugin.api_testing.service.test_case_service import TestCaseService
from backend.plugin.api_testing.service.test_suite_service import TestSuiteService


class BatchExecutionService:
    """批量执行服务。"""

    @staticmethod
    async def execute_cases(
        case_ids: list[int],
        execute_case: Callable[[int], Awaitable[dict[str, Any]]],
        max_concurrency: int,
    ) -> dict[str, Any]:
        """执行多个用例并汇总结果。"""
        concurrency = max(1, int(max_concurrency or 1))
        semaphore = asyncio.Semaphore(concurrency)

        async def run_case(case_id: int) -> dict[str, Any]:
            async with semaphore:
                try:
                    result = await execute_case(case_id)
                except Exception as exc:  # noqa: BLE001
                    result = {
                        'case_id': case_id,
                        'success': False,
                        'report_id': None,
                        'duration': 0,
                        'error': str(exc),
                    }
                result.setdefault('case_id', case_id)
                result.setdefault('success', False)
                result.setdefault('report_id', None)
                result.setdefault('duration', 0)
                return result

        results = await asyncio.gather(*(run_case(case_id) for case_id in case_ids))
        success_cases = sum(1 for result in results if result.get('success'))
        return {
            'success': success_cases == len(results),
            'total_cases': len(results),
            'success_cases': success_cases,
            'fail_cases': len(results) - success_cases,
            'results': results,
            'case_report_ids': [result['report_id'] for result in results if result.get('report_id') is not None],
            'max_concurrency': concurrency,
        }

    @staticmethod
    async def execute_project(
        project_id: int,
        *,
        environment_id: int | None = None,
        max_concurrency: int = 5,
    ) -> dict[str, Any]:
        """按项目批量执行。"""
        project = await ProjectService.get_project_by_id(project_id)
        if not project:
            raise ValueError(f'项目不存在: {project_id}')

        test_cases = await TestCaseService.get_test_cases(project_id=project_id, status=1, limit=1000)
        case_ids = [test_case.id for test_case in test_cases]
        if not case_ids:
            raise ValueError('项目下没有可执行的测试用例')

        start_time = datetime.now()
        summary = await BatchExecutionService.execute_cases(
            case_ids=case_ids,
            execute_case=lambda case_id: TestCaseExecutionService.execute_test_case(
                case_id,
                environment_id=environment_id,
            ),
            max_concurrency=max_concurrency,
        )
        end_time = datetime.now()
        return await BatchExecutionService._save_batch_report(
            project_id=project.id,
            suite_id=None,
            target_type='project',
            target_id=project.id,
            name=f'{project.name}_批量执行_{end_time.strftime("%Y%m%d_%H%M%S")}',
            start_time=start_time,
            end_time=end_time,
            summary=summary,
        )

    @staticmethod
    async def execute_suite(
        suite_id: int,
        *,
        environment_id: int | None = None,
        max_concurrency: int = 5,
    ) -> dict[str, Any]:
        """按测试集合批量执行。"""
        suite = await TestSuiteService.get_test_suite_by_id(suite_id)
        if not suite:
            raise ValueError(f'测试集合不存在: {suite_id}')

        case_ids = await TestSuiteService.get_suite_case_ids(suite_id, enabled_only=True)
        if not case_ids:
            raise ValueError('测试集合下没有可执行的测试用例')

        start_time = datetime.now()
        summary = await BatchExecutionService.execute_cases(
            case_ids=case_ids,
            execute_case=lambda case_id: TestCaseExecutionService.execute_test_case(
                case_id,
                environment_id=environment_id,
            ),
            max_concurrency=max_concurrency,
        )
        end_time = datetime.now()
        return await BatchExecutionService._save_batch_report(
            project_id=suite.project_id,
            suite_id=suite.id,
            target_type='suite',
            target_id=suite.id,
            name=f'{suite.name}_批量执行_{end_time.strftime("%Y%m%d_%H%M%S")}',
            start_time=start_time,
            end_time=end_time,
            summary=summary,
        )

    @staticmethod
    async def _save_batch_report(
        *,
        project_id: int,
        suite_id: int | None,
        target_type: str,
        target_id: int,
        name: str,
        start_time: datetime,
        end_time: datetime,
        summary: dict[str, Any],
    ) -> dict[str, Any]:
        """保存批量执行报告并返回统一响应。"""
        duration = int((end_time - start_time).total_seconds() * 1000)

        async with async_db_session() as db:
            batch_report = ApiBatchExecutionReport(
                project_id=project_id,
                suite_id=suite_id,
                name=name,
                target_type=target_type,
                success=summary['success'],
                total_cases=summary['total_cases'],
                success_cases=summary['success_cases'],
                fail_cases=summary['fail_cases'],
                max_concurrency=summary['max_concurrency'],
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                details={
                    'report_ids': summary['case_report_ids'],
                    'results': summary['results'],
                },
            )
            db.add(batch_report)
            await db.commit()
            await db.refresh(batch_report)

            saved_report = await db.scalar(
                select(ApiBatchExecutionReport).where(ApiBatchExecutionReport.id == batch_report.id)
            )

        return {
            'batch_report_id': saved_report.id,
            'name': name,
            'target_type': target_type,
            'target_id': target_id,
            'project_id': project_id,
            'suite_id': suite_id,
            'success': summary['success'],
            'total_cases': summary['total_cases'],
            'success_cases': summary['success_cases'],
            'fail_cases': summary['fail_cases'],
            'max_concurrency': summary['max_concurrency'],
            'duration': duration,
            'report_ids': summary['case_report_ids'],
            'results': summary['results'],
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
        }
