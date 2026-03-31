#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQL执行API
"""
from typing import Any, Dict, List

from fastapi import APIRouter

from backend.common.response.response_schema import response_base, ResponseModel, ResponseSchemaModel
from backend.app.task.tasks.api_testing_sql.tasks import execute_api_testing_sql
from backend.plugin.api_testing.schema.request import SqlTaskStatusResponse, SqlTaskSubmitResponse
from backend.plugin.api_testing.service.sql_task_service import SqlTaskService
from backend.plugin.api_testing.utils.sql_executor import SQLQuery

router = APIRouter()


@router.post('/execute', response_model=Dict[str, Any], summary='异步执行SQL查询')
async def execute_sql_query(query: SQLQuery) -> Dict[str, Any]:
    try:
        task = await SqlTaskService.create_task(query)
        celery_task = execute_api_testing_sql.delay(task.task_id)
        task = await SqlTaskService.bind_celery_task_id(task.task_id, celery_task.id) or task
        response = response_base.success(
            data=SqlTaskSubmitResponse(
                task_id=task.task_id,
                celery_task_id=task.celery_task_id,
                status=task.status,
                name=task.name,
            ).model_dump()
        )
        return response.model_dump()
    except Exception as exc:  # noqa: BLE001
        return response_base.fail(data=f'SQL任务提交失败: {exc}').model_dump()


@router.post('/batch-execute', response_model=Dict[str, Any], summary='批量异步执行SQL查询')
async def execute_batch_sql_queries(queries: List[SQLQuery]) -> Dict[str, Any]:
    try:
        tasks = []
        for query in queries:
            task = await SqlTaskService.create_task(query)
            celery_task = execute_api_testing_sql.delay(task.task_id)
            task = await SqlTaskService.bind_celery_task_id(task.task_id, celery_task.id) or task
            tasks.append(
                SqlTaskSubmitResponse(
                    task_id=task.task_id,
                    celery_task_id=task.celery_task_id,
                    status=task.status,
                    name=task.name,
                ).model_dump()
            )
        return response_base.success(
            data={
                'results': tasks,
                'summary': {'total': len(tasks), 'pending': len(tasks)},
            }
        ).model_dump()
    except Exception as exc:  # noqa: BLE001
        return response_base.fail(data=f'批量SQL任务提交失败: {exc}').model_dump()


@router.get('/tasks/{task_id}', response_model=ResponseModel, summary='获取SQL异步任务状态')
async def get_sql_task_status(task_id: str) -> ResponseModel | ResponseSchemaModel:
    task = await SqlTaskService.get_by_task_id(task_id)
    if not task:
        return response_base.fail(data='SQL任务不存在')

    return response_base.success(
        data=SqlTaskStatusResponse(
            task_id=task.task_id,
            celery_task_id=task.celery_task_id,
            status=task.status,
            name=task.name,
            result=task.result,
            error=task.error,
            duration=task.duration,
            start_time=task.start_time.isoformat() if task.start_time else None,
            end_time=task.end_time.isoformat() if task.end_time else None,
        ).model_dump()
    )
