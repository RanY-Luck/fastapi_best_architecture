from backend.app.task.celery import celery_app
from backend.common.log import log
from backend.plugin.ai_assistant.service.agent_service import AgentService
from backend.plugin.ai_assistant.service.browser_service import BrowserService
from backend.plugin.ai_assistant.service.conversation_service import ConversationService
from backend.plugin.ai_assistant.service.data_assistant_service import DataAssistantService
from backend.plugin.ai_assistant.service.event_service import (
    emit_run_completed,
    emit_run_failed,
    emit_run_progress,
    emit_run_started,
)


@celery_app.task(name='ai_assistant.execute_run')
async def execute_ai_assistant_run(
    *,
    conversation_id: int,
    message_id: int,
    run_id: int,
    user_id: int,
    session_uuid: str,
    route_type: str,
    target_name: str | None,
    content: str,
    token: str,
    action_params: dict[str, str] | None = None,
) -> str:
    task_id = execute_ai_assistant_run.request.id or ''
    await emit_run_started(
        user_id=user_id,
        session_uuid=session_uuid,
        task_id=task_id,
        run_id=run_id,
        conversation_id=conversation_id,
        message_id=message_id,
    )
    await ConversationService.update_action_run(run_id=run_id, status='running', celery_task_id=task_id)
    try:
        await emit_run_progress(
            user_id=user_id,
            session_uuid=session_uuid,
            task_id=task_id,
            run_id=run_id,
            conversation_id=conversation_id,
            message='开始执行异步动作',
        )
        if route_type == 'agent':
            await emit_run_progress(
                user_id=user_id,
                session_uuid=session_uuid,
                task_id=task_id,
                run_id=run_id,
                conversation_id=conversation_id,
                message='正在分析你的问题并选择工具',
            )
            result_summary = await AgentService.execute_run(
                content=content,
                user_id=user_id,
                session_uuid=session_uuid,
                token=token,
                action_name=target_name,
                action_params=action_params,
            )
        elif route_type == 'data':
            result_summary = await DataAssistantService.execute_action(
                action_name=target_name,
                content=content,
                user_id=user_id,
                session_uuid=session_uuid,
                token=token,
                action_params=action_params,
            )
        elif route_type == 'playwright':
            result_summary = await BrowserService.execute_flow(
                action_name=target_name,
                content=content,
                user_id=user_id,
                session_uuid=session_uuid,
            )
        else:
            raise ValueError(f'不支持的 AI 助手路由类型: {route_type}')
        await ConversationService.update_action_run(
            run_id=run_id,
            status='completed',
            celery_task_id=task_id,
            result_summary=result_summary,
            finished=True,
        )
        await ConversationService.add_message(
            conversation_id=conversation_id,
            role='assistant',
            content=result_summary,
            action_type=route_type,
            action_status='completed',
        )
        await emit_run_completed(
            user_id=user_id,
            session_uuid=session_uuid,
            task_id=task_id,
            run_id=run_id,
            conversation_id=conversation_id,
            message_id=message_id,
            result_summary=result_summary,
        )
        return result_summary
    except Exception as exc:
        error_summary = str(exc)
        log.error(f'AI助手异步动作执行失败 run_id={run_id}: {error_summary}')
        await ConversationService.update_action_run(
            run_id=run_id,
            status='failed',
            celery_task_id=task_id,
            error_summary=error_summary,
            finished=True,
        )
        await emit_run_failed(
            user_id=user_id,
            session_uuid=session_uuid,
            task_id=task_id,
            run_id=run_id,
            conversation_id=conversation_id,
            message_id=message_id,
            error_summary=error_summary,
        )
        raise
