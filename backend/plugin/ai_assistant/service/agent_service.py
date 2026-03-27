import json
from typing import Any

from backend.core.conf import settings
from backend.plugin.ai_assistant.schema.chat import ChatRoutePlan
from backend.plugin.ai_assistant.service.llm_provider_service import LLMProviderService
from backend.plugin.ai_assistant.service.tool_registry import build_langchain_tools, get_enabled_tools


class AgentService:
    SYSTEM_PROMPT = (
        '你是一个企业内部 AI 助手。你的目标是优先理解用户需求，并在需要时调用工具获取真实数据。'
        '如果用户在查询设备上报记录，且问题中包含 IMEI、时间范围、groupId、分页等线索，请优先选择 query_device_reports 工具。'
        '如果没有合适工具或信息不足，就直接自然语言回答或要求补充必要参数。'
    )
    TOOL_RESULT_PROMPT = SYSTEM_PROMPT + ' 你已经获得了工具返回结果，请用中文给出简洁、自然的结论，保留关键查询条件和结果摘要。'

    @staticmethod
    def _normalize_action_params(action_params: dict[str, str] | None) -> dict[str, str]:
        return {str(k): str(v).strip() for k, v in (action_params or {}).items() if str(v).strip()}

    @staticmethod
    def _message_text(message: Any) -> str:
        content = getattr(message, 'content', '')
        return content if isinstance(content, str) else str(content)

    @staticmethod
    def _extract_tool_calls(message: Any) -> list[dict[str, Any]]:
        tool_calls = getattr(message, 'tool_calls', None)
        return tool_calls if isinstance(tool_calls, list) else []

    @staticmethod
    def _format_tool_payload(tool_result: str) -> str:
        try:
            parsed_result = json.loads(tool_result)
            return json.dumps(parsed_result, ensure_ascii=False)
        except json.JSONDecodeError:
            return tool_result

    @classmethod
    async def _summarize_tool_result(cls, *, content: str, tool_name: str, tool_result: str) -> str:
        if not LLMProviderService.is_enabled():
            return tool_result
        messages = LLMProviderService.build_messages(
            system_prompt=cls.TOOL_RESULT_PROMPT,
            conversation_messages=[
                {'role': 'user', 'content': content},
                {'role': 'assistant', 'content': f'工具 {tool_name} 返回：{cls._format_tool_payload(tool_result)}'},
            ],
        )
        ai_message = await LLMProviderService.ainvoke(messages=messages)
        text = cls._message_text(ai_message)
        return text.strip() or tool_result

    @classmethod
    def should_use_agent(cls, *, action_name: str | None, content: str) -> bool:
        rollout = settings.AI_ASSISTANT_AGENT_ROLLOUT_MODE
        if rollout == 'legacy_router' or not LLMProviderService.is_enabled():
            return False
        if action_name and rollout in {'agent_forced_for_explicit_tools', 'agent_primary'}:
            return True
        if rollout == 'agent_primary':
            return True
        lowered = content.lower()
        return '设备' in content or '上报' in content or 'imei' in lowered

    @classmethod
    def build_agent_route(cls, *, action_name: str | None, content: str) -> tuple[str, str | None]:
        if action_name:
            return 'agent', action_name
        tools = get_enabled_tools()
        lowered = content.lower()
        if 'query_device_reports' in tools and ('设备' in content or '上报' in content or 'imei' in lowered):
            return 'agent', 'query_device_reports'
        return 'agent', None

    @classmethod
    def build_agent_route_plan(cls, *, action_name: str | None, content: str) -> ChatRoutePlan:
        route_type, target_name = cls.build_agent_route(action_name=action_name, content=content)
        return ChatRoutePlan(
            route_type=route_type,
            target_name=target_name,
            sync_allowed=False,
            reason='agent_route',
        )

    @classmethod
    async def execute_run(
        cls,
        *,
        content: str,
        user_id: int,
        session_uuid: str,
        token: str,
        action_name: str | None = None,
        action_params: dict[str, str] | None = None,
    ) -> str:
        tools = get_enabled_tools()
        normalized_params = cls._normalize_action_params(action_params)
        selected_tool = action_name if action_name in tools else None

        if selected_tool is not None:
            tool_result = await tools[selected_tool].executor(
                content=content,
                user_id=user_id,
                session_uuid=session_uuid,
                token=token,
                action_params=normalized_params,
            )
            if not LLMProviderService.is_enabled():
                return tool_result
            return await cls._summarize_tool_result(
                content=content,
                tool_name=selected_tool,
                tool_result=tool_result,
            )

        if not LLMProviderService.is_enabled():
            return '已收到你的消息。'

        langchain_tools = build_langchain_tools(
            content=content,
            user_id=user_id,
            session_uuid=session_uuid,
            token=token,
        )
        if not langchain_tools:
            return '当前没有可用工具。'

        messages = LLMProviderService.build_messages(
            system_prompt=cls.SYSTEM_PROMPT,
            conversation_messages=[{'role': 'user', 'content': content}],
        )
        ai_message = await LLMProviderService.ainvoke_with_tools(messages=messages, tools=langchain_tools)
        tool_calls = cls._extract_tool_calls(ai_message)
        if not tool_calls:
            return cls._message_text(ai_message).strip() or '已收到你的消息。'

        tool_call = tool_calls[0]
        tool_name = str(tool_call.get('name', '')).strip()
        tool = tools.get(tool_name)
        if tool is None:
            return cls._message_text(ai_message).strip() or '暂时无法执行该工具请求。'

        tool_args = tool_call.get('args', {})
        normalized_tool_args = {
            str(key): str(value).strip()
            for key, value in tool_args.items()
            if str(value).strip()
        } if isinstance(tool_args, dict) else {}
        tool_result = await tool.executor(
            content=content,
            user_id=user_id,
            session_uuid=session_uuid,
            token=token,
            action_params=normalized_tool_args,
        )
        return await cls._summarize_tool_result(content=content, tool_name=tool_name, tool_result=tool_result)
