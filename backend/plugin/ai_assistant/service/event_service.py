from typing import Any

from backend.common.log import log
from backend.common.socketio.server import sio
from backend.plugin.ai_assistant.schema.events import AssistantTaskEventPayload
from backend.plugin.ai_assistant.utils.session_keys import build_room_name
from backend.plugin.ai_assistant.utils.socket_events import (
    AI_ASSISTANT_EVENT_RUN_COMPLETED,
    AI_ASSISTANT_EVENT_RUN_FAILED,
    AI_ASSISTANT_EVENT_RUN_PROGRESS,
    AI_ASSISTANT_EVENT_RUN_STARTED,
)


async def _emit_to_room(*, room: str, event: str, data: dict[str, Any]) -> None:
    await sio.emit(event, data, room=room, namespace='/ws')


async def emit_run_started(*, user_id: int, session_uuid: str, task_id: str, run_id: int, conversation_id: int, message_id: int) -> None:
    payload = AssistantTaskEventPayload(
        event=AI_ASSISTANT_EVENT_RUN_STARTED,
        task_id=task_id,
        run_id=run_id,
        conversation_id=conversation_id,
        message_id=message_id,
        status='running',
        message='任务开始执行',
    )
    await _emit_to_room(room=build_room_name(user_id, session_uuid), event=payload.event, data=payload.model_dump())


async def emit_run_progress(*, user_id: int, session_uuid: str, task_id: str, run_id: int, conversation_id: int, message: str) -> None:
    payload = AssistantTaskEventPayload(
        event=AI_ASSISTANT_EVENT_RUN_PROGRESS,
        task_id=task_id,
        run_id=run_id,
        conversation_id=conversation_id,
        status='running',
        message=message,
    )
    await _emit_to_room(room=build_room_name(user_id, session_uuid), event=payload.event, data=payload.model_dump())


async def emit_run_completed(*, user_id: int, session_uuid: str, task_id: str, run_id: int, conversation_id: int, message_id: int, result_summary: str) -> None:
    payload = AssistantTaskEventPayload(
        event=AI_ASSISTANT_EVENT_RUN_COMPLETED,
        task_id=task_id,
        run_id=run_id,
        conversation_id=conversation_id,
        message_id=message_id,
        status='completed',
        message=result_summary,
    )
    await _emit_to_room(room=build_room_name(user_id, session_uuid), event=payload.event, data=payload.model_dump())


async def emit_run_failed(*, user_id: int, session_uuid: str, task_id: str, run_id: int, conversation_id: int, message_id: int, error_summary: str) -> None:
    payload = AssistantTaskEventPayload(
        event=AI_ASSISTANT_EVENT_RUN_FAILED,
        task_id=task_id,
        run_id=run_id,
        conversation_id=conversation_id,
        message_id=message_id,
        status='failed',
        message=error_summary,
    )
    await _emit_to_room(room=build_room_name(user_id, session_uuid), event=payload.event, data=payload.model_dump())


def log_emit_failure(context: str, error: Exception, extra: dict[str, Any] | None = None) -> None:
    log.error(f'AI助手事件推送失败 [{context}]: {error}; extra={extra or {}}')
