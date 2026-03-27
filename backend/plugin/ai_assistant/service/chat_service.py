from backend.app.task.tasks.ai_assistant.tasks import execute_ai_assistant_run
from backend.common.security.jwt import jwt_decode
from backend.plugin.ai_assistant.schema.chat import (
    ChatMessageCreateParam,
    ChatSendResult,
    ConversationCreateParam,
    ConversationHistoryDetail,
)
from backend.plugin.ai_assistant.schema.session import AssistantSessionResetResult, AssistantSessionStatus
from backend.plugin.ai_assistant.service.agent_service import AgentService
from backend.plugin.ai_assistant.service.browser_service import BrowserService
from backend.plugin.ai_assistant.service.conversation_service import (
    ConversationService,
    to_action_run_detail,
    to_conversation_detail,
    to_message_detail,
)
from backend.plugin.ai_assistant.service.router_service import RouterService


class ChatService:
    @staticmethod
    async def create_conversation(*, user_id: int, session_uuid: str, obj: ConversationCreateParam):
        conversation = await ConversationService.create_conversation(
            user_id=user_id,
            session_uuid=session_uuid,
            title=obj.title,
        )
        return to_conversation_detail(conversation)

    @staticmethod
    async def get_conversation_history(*, conversation_id: int, user_id: int) -> ConversationHistoryDetail | None:
        conversation = await ConversationService.get_conversation(conversation_id=conversation_id, user_id=user_id)
        if conversation is None:
            return None
        ordered_messages = sorted(conversation.messages, key=lambda item: item.created_time)
        return ConversationHistoryDetail(
            conversation=to_conversation_detail(conversation),
            messages=[to_message_detail(message) for message in ordered_messages],
        )

    @staticmethod
    async def send_message(*, token: str, user_id: int, obj: ChatMessageCreateParam) -> ChatSendResult:
        payload = jwt_decode(token)
        session_uuid = payload.session_uuid
        conversation = None
        if obj.conversation_id is not None:
            conversation = await ConversationService.get_conversation(conversation_id=obj.conversation_id, user_id=user_id)
        if conversation is None:
            conversation = await ConversationService.create_conversation(
                user_id=user_id,
                session_uuid=session_uuid,
                title=(obj.content[:20] or '新会话'),
            )

        user_message = await ConversationService.add_message(
            conversation_id=conversation.id,
            role='user',
            content=obj.content,
        )

        if AgentService.should_use_agent(action_name=obj.action_name, content=obj.content):
            route_plan = AgentService.build_agent_route_plan(action_name=obj.action_name, content=obj.content)
        else:
            route_plan = RouterService.resolve_route(content=obj.content, action_name=obj.action_name)

        if route_plan.route_type == 'chat':
            assistant_message = await ConversationService.add_message(
                conversation_id=conversation.id,
                role='assistant',
                content=f'已收到你的消息：{obj.content}',
                action_type='chat',
                action_status='completed',
            )
            return ChatSendResult(
                conversation=to_conversation_detail(conversation),
                user_message=to_message_detail(user_message),
                assistant_message=to_message_detail(assistant_message),
                action_run=None,
                accepted=False,
            )

        action_run = await ConversationService.create_action_run(
            conversation_id=conversation.id,
            message_id=user_message.id,
            user_id=user_id,
            session_uuid=session_uuid,
            route_type=route_plan.route_type,
            target_name=route_plan.target_name,
            status='pending',
        )
        celery_task = execute_ai_assistant_run.delay(
            conversation_id=conversation.id,
            message_id=user_message.id,
            run_id=action_run.id,
            user_id=user_id,
            session_uuid=session_uuid,
            route_type=route_plan.route_type,
            target_name=route_plan.target_name,
            content=obj.content,
            token=token,
            action_params=obj.action_params,
        )
        await ConversationService.update_action_run(
            run_id=action_run.id,
            status='pending',
            celery_task_id=celery_task.id,
        )
        action_run.celery_task_id = celery_task.id
        return ChatSendResult(
            conversation=to_conversation_detail(conversation),
            user_message=to_message_detail(user_message),
            assistant_message=None,
            action_run=to_action_run_detail(action_run),
            accepted=True,
        )

    @staticmethod
    async def get_session_status(*, user_id: int, session_uuid: str) -> AssistantSessionStatus:
        return await BrowserService.get_session_status(user_id=user_id, session_uuid=session_uuid)

    @staticmethod
    async def reset_session(*, user_id: int, session_uuid: str) -> AssistantSessionResetResult:
        return await BrowserService.reset_session(user_id=user_id, session_uuid=session_uuid)
