from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request

from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth, get_token, jwt_decode
from backend.plugin.ai_assistant.schema.chat import (
    ChatMessageCreateParam,
    ChatSendResult,
    ConversationCreateParam,
    ConversationDetail,
    ConversationHistoryDetail,
)
from backend.plugin.ai_assistant.service.chat_service import ChatService

router = APIRouter(dependencies=[DependsJwtAuth])


@router.post('/conversations', summary='创建AI助手会话')
async def create_conversation(request: Request, obj: ConversationCreateParam) -> ResponseSchemaModel[ConversationDetail]:
    token_payload = jwt_decode(get_token(request))
    conversation = await ChatService.create_conversation(
        user_id=request.user.id,
        session_uuid=token_payload.session_uuid,
        obj=obj,
    )
    return response_base.success(data=conversation)


@router.get('/conversations/{conversation_id}', summary='获取AI助手会话历史')
async def get_conversation_history(
    request: Request,
    conversation_id: Annotated[int, Path(description='会话ID')],
) -> ResponseModel | ResponseSchemaModel[ConversationHistoryDetail]:
    history = await ChatService.get_conversation_history(conversation_id=conversation_id, user_id=request.user.id)
    if history is None:
        return response_base.fail(data='会话不存在或无权访问')
    return response_base.success(data=history)


@router.post('/messages', summary='发送AI助手消息')
async def send_message(request: Request, obj: ChatMessageCreateParam) -> ResponseSchemaModel[ChatSendResult]:
    result = await ChatService.send_message(
        token=get_token(request),
        user_id=request.user.id,
        obj=obj,
    )
    return response_base.success(data=result)
