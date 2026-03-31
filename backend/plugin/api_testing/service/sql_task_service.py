from datetime import datetime
from uuid import uuid4

from sqlalchemy import select

from backend.database.db import async_db_session
from backend.plugin.api_testing.model.models import ApiSqlExecutionTask
from backend.plugin.api_testing.utils.sql_executor import SQLQuery


class SqlTaskService:
    """API Testing SQL异步任务服务"""

    @staticmethod
    async def create_task(sql_query: SQLQuery, celery_task_id: str | None = None) -> ApiSqlExecutionTask:
        async with async_db_session() as db:
            task = ApiSqlExecutionTask(
                task_id=uuid4().hex,
                celery_task_id=celery_task_id,
                name=sql_query.name,
                status='pending',
                query_payload=sql_query.model_dump(),
                result=None,
            )
            db.add(task)
            await db.commit()
            await db.refresh(task)
            return task

    @staticmethod
    async def get_by_task_id(task_id: str) -> ApiSqlExecutionTask | None:
        async with async_db_session() as db:
            result = await db.execute(
                select(ApiSqlExecutionTask).where(ApiSqlExecutionTask.task_id == task_id)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def mark_running(task_id: str, start_time: datetime | None = None) -> ApiSqlExecutionTask | None:
        async with async_db_session() as db:
            result = await db.execute(
                select(ApiSqlExecutionTask).where(ApiSqlExecutionTask.task_id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                return None
            task.status = 'running'
            task.start_time = start_time or datetime.now()
            await db.commit()
            await db.refresh(task)
            return task

    @staticmethod
    async def mark_completed(
        task_id: str,
        *,
        result: dict,
        end_time: datetime | None = None,
        duration: int | None = None,
    ) -> ApiSqlExecutionTask | None:
        async with async_db_session() as db:
            query_result = await db.execute(
                select(ApiSqlExecutionTask).where(ApiSqlExecutionTask.task_id == task_id)
            )
            task = query_result.scalar_one_or_none()
            if not task:
                return None
            task.status = 'success'
            task.result = result
            task.error = None
            task.end_time = end_time or datetime.now()
            task.duration = duration
            await db.commit()
            await db.refresh(task)
            return task

    @staticmethod
    async def mark_failed(
        task_id: str,
        *,
        error: str,
        end_time: datetime | None = None,
        duration: int | None = None,
    ) -> ApiSqlExecutionTask | None:
        async with async_db_session() as db:
            query_result = await db.execute(
                select(ApiSqlExecutionTask).where(ApiSqlExecutionTask.task_id == task_id)
            )
            task = query_result.scalar_one_or_none()
            if not task:
                return None
            task.status = 'failed'
            task.error = error
            task.end_time = end_time or datetime.now()
            task.duration = duration
            await db.commit()
            await db.refresh(task)
            return task
    @staticmethod
    async def bind_celery_task_id(task_id: str, celery_task_id: str) -> ApiSqlExecutionTask | None:
        async with async_db_session() as db:
            query_result = await db.execute(
                select(ApiSqlExecutionTask).where(ApiSqlExecutionTask.task_id == task_id)
            )
            task = query_result.scalar_one_or_none()
            if not task:
                return None
            task.celery_task_id = celery_task_id
            await db.commit()
            await db.refresh(task)
            return task
