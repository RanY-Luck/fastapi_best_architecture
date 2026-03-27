from fastapi import APIRouter, Request

from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth, get_token, jwt_decode
from backend.plugin.ai_assistant.schema.session import AssistantSessionResetResult, AssistantSessionStatus
from backend.plugin.ai_assistant.service.chat_service import ChatService

router = APIRouter(dependencies=[DependsJwtAuth])


@router.get('/status', summary='获取AI助手运行时状态')
async def get_session_status(request: Request) -> ResponseSchemaModel[AssistantSessionStatus]:
    token_payload = jwt_decode(get_token(request))
    result = await ChatService.get_session_status(user_id=request.user.id, session_uuid=token_payload.session_uuid)
    return response_base.success(data=result)


@router.post('/reset', summary='重置AI助手运行时会话')
async def reset_session(request: Request) -> ResponseSchemaModel[AssistantSessionResetResult]:
    token_payload = jwt_decode(get_token(request))
    result = await ChatService.reset_session(user_id=request.user.id, session_uuid=token_payload.session_uuid)
    return response_base.success(data=result)
