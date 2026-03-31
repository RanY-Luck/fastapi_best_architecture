from datetime import datetime

from celery import shared_task

from backend.plugin.api_testing.service.sql_task_service import SqlTaskService
from backend.plugin.api_testing.utils.sql_executor import SQLExecutor, SQLQuery


@shared_task(name='api_testing_execute_sql')
async def execute_api_testing_sql(task_id: str) -> dict:
    task = await SqlTaskService.get_by_task_id(task_id)
    if not task:
        return {'success': False, 'error': f'SQL任务不存在: {task_id}'}

    running_task = await SqlTaskService.mark_running(task_id, start_time=datetime.now())
    query = SQLQuery(**task.query_payload)

    try:
        result = await SQLExecutor.execute_query_async(query)
        end_time = datetime.now()
        started_at = running_task.start_time if running_task and running_task.start_time else end_time
        duration = int((end_time - started_at).total_seconds() * 1000)
        if result.success:
            await SqlTaskService.mark_completed(
                task_id,
                result=result.model_dump(),
                end_time=end_time,
                duration=duration,
            )
        else:
            await SqlTaskService.mark_failed(
                task_id,
                error=result.error or 'SQL执行失败',
                end_time=end_time,
                duration=duration,
            )
        return result.model_dump()
    except Exception as exc:  # noqa: BLE001
        end_time = datetime.now()
        started_at = running_task.start_time if running_task and running_task.start_time else end_time
        duration = int((end_time - started_at).total_seconds() * 1000)
        await SqlTaskService.mark_failed(task_id, error=str(exc), end_time=end_time, duration=duration)
        return {'success': False, 'error': str(exc)}
