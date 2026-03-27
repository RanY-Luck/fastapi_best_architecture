from fastapi import APIRouter

from backend.core.conf import settings
from backend.plugin.ai_assistant.api.v1.chat import router as chat_router
from backend.plugin.ai_assistant.api.v1.session import router as session_router

v1 = APIRouter(prefix=f'{settings.FASTAPI_API_V1_PATH}/ai_assistant')

v1.include_router(chat_router, prefix='/chat', tags=['AI助手聊天'])
v1.include_router(session_router, prefix='/session', tags=['AI助手会话'])
