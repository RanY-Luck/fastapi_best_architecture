from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from backend.database.db import async_db_session
from backend.plugin.ai_assistant.model.models import AiActionRun, AiConversation, AiMessage
from backend.plugin.ai_assistant.schema.chat import ActionRunDetail, ConversationDetail, MessageDetail


class ConversationService:
    @staticmethod
    async def create_conversation(*, user_id: int, session_uuid: str, title: str | None = None) -> AiConversation:
        async with async_db_session.begin() as db:
            conversation = AiConversation(
                user_id=user_id,
                session_uuid=session_uuid,
                title=title or '新会话',
                status='active',
            )
            db.add(conversation)
            await db.flush()
            await db.refresh(conversation)
            return conversation

    @staticmethod
    async def get_conversation(*, conversation_id: int, user_id: int) -> AiConversation | None:
        async with async_db_session() as db:
            result = await db.execute(
                select(AiConversation)
                .options(selectinload(AiConversation.messages), selectinload(AiConversation.action_runs))
                .where(AiConversation.id == conversation_id, AiConversation.user_id == user_id)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def add_message(
        *,
        conversation_id: int,
        role: str,
        content: str,
        action_type: str | None = None,
        action_status: str | None = None,
    ) -> AiMessage:
        async with async_db_session.begin() as db:
            message = AiMessage(
                conversation_id=conversation_id,
                role=role,
                content=content,
                action_type=action_type,
                action_status=action_status,
            )
            db.add(message)
            await db.flush()
            await db.refresh(message)
            return message

    @staticmethod
    async def create_action_run(
        *,
        conversation_id: int,
        message_id: int,
        user_id: int,
        session_uuid: str,
        route_type: str,
        target_name: str | None,
        status: str = 'pending',
    ) -> AiActionRun:
        async with async_db_session.begin() as db:
            action_run = AiActionRun(
                conversation_id=conversation_id,
                message_id=message_id,
                user_id=user_id,
                session_uuid=session_uuid,
                route_type=route_type,
                target_name=target_name,
                status=status,
            )
            db.add(action_run)
            await db.flush()
            await db.refresh(action_run)
            return action_run

    @staticmethod
    async def update_action_run(
        *,
        run_id: int,
        status: str,
        celery_task_id: str | None = None,
        result_summary: str | None = None,
        error_summary: str | None = None,
        finished: bool = False,
    ) -> None:
        values: dict[str, Any] = {'status': status}
        if celery_task_id is not None:
            values['celery_task_id'] = celery_task_id
        if result_summary is not None:
            values['result_summary'] = result_summary
        if error_summary is not None:
            values['error_summary'] = error_summary
        if finished:
            values['finished_time'] = datetime.now()
        async with async_db_session.begin() as db:
            await db.execute(update(AiActionRun).where(AiActionRun.id == run_id).values(**values))


def to_conversation_detail(obj: AiConversation) -> ConversationDetail:
    return ConversationDetail.model_validate(obj, from_attributes=True)


def to_message_detail(obj: AiMessage) -> MessageDetail:
    return MessageDetail.model_validate(obj, from_attributes=True)


def to_action_run_detail(obj: AiActionRun) -> ActionRunDetail:
    return ActionRunDetail.model_validate(obj, from_attributes=True)
