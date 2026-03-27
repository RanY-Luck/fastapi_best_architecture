from typing import Any

from backend.core.conf import settings

try:
    from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
    from langchain_openai import ChatOpenAI
    LANGCHAIN_AVAILABLE = True
except ImportError:
    AIMessage = BaseMessage = HumanMessage = SystemMessage = ToolMessage = Any  # type: ignore
    ChatOpenAI = None  # type: ignore
    LANGCHAIN_AVAILABLE = False


class LLMProviderService:
    @staticmethod
    def is_enabled() -> bool:
        return bool(LANGCHAIN_AVAILABLE and settings.AI_ASSISTANT_LLM_ENABLED and settings.AI_ASSISTANT_LLM_API_KEY.strip())

    @staticmethod
    def create_chat_model() -> Any:
        if not LANGCHAIN_AVAILABLE or ChatOpenAI is None:
            raise RuntimeError('LangChain/OpenAI 依赖未安装，无法初始化 LLM Provider')
        kwargs = {
            'model': settings.AI_ASSISTANT_LLM_MODEL,
            'api_key': settings.AI_ASSISTANT_LLM_API_KEY,
            'timeout': settings.AI_ASSISTANT_LLM_TIMEOUT,
        }
        if settings.AI_ASSISTANT_LLM_BASE_URL.strip():
            kwargs['base_url'] = settings.AI_ASSISTANT_LLM_BASE_URL.strip()
        return ChatOpenAI(**kwargs)

    @classmethod
    def bind_tools(cls, *, tools: list[Any]) -> Any:
        model = cls.create_chat_model()
        return model.bind_tools(tools)

    @classmethod
    async def ainvoke_with_tools(cls, *, messages: list[Any], tools: list[Any]) -> Any:
        model = cls.bind_tools(tools=tools)
        response = await model.ainvoke(messages)
        if LANGCHAIN_AVAILABLE and isinstance(response, AIMessage):
            return response
        return AIMessage(content=str(getattr(response, 'content', response))) if LANGCHAIN_AVAILABLE else response

    @staticmethod
    def build_messages(*, system_prompt: str, conversation_messages: list[dict[str, str]]) -> list[Any]:
        if not LANGCHAIN_AVAILABLE:
            return []
        messages: list[Any] = [SystemMessage(content=system_prompt)]
        for item in conversation_messages:
            role = item.get('role', 'user')
            content = item.get('content', '')
            if role == 'assistant':
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))
        return messages
