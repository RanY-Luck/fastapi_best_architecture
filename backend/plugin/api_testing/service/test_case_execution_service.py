#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API测试用例执行服务
"""

from collections.abc import AsyncIterator
from typing import Any, Optional

from backend.common.log import log


class TestCaseExecutionService:
    """单用例执行服务。"""

    @staticmethod
    async def stream_test_case_execution(
        case_id: int,
        environment_id: Optional[int] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """流式执行测试用例，按事件输出执行过程。"""
        from backend.plugin.api_testing.service.test_case_execution_runner import TestCaseExecutionRunner

        runner = TestCaseExecutionRunner(case_id=case_id, environment_id=environment_id)
        try:
            async for event in runner.run():
                yield event
        except Exception as exc:  # noqa: BLE001
            log.exception("stream_test_case_execution failed: %s", exc)
            yield {
                "type": "error",
                "case_id": case_id,
                "environment_id": environment_id,
                "message": str(exc),
                "error_type": type(exc).__name__,
            }

    @staticmethod
    async def execute_test_case(case_id: int, environment_id: Optional[int] = None) -> dict[str, Any]:
        """执行测试用例并返回最终报告摘要。"""
        from backend.plugin.api_testing.service.test_case_execution_runner import TestCaseExecutionRunner

        runner = TestCaseExecutionRunner(case_id=case_id, environment_id=environment_id)
        async for _event in runner.run():
            pass

        if runner.final_result is None:
            raise RuntimeError("测试执行未产生最终结果")
        return runner.final_result
