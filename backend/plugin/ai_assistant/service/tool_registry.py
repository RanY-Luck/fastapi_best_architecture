from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import Field, create_model

from backend.core.conf import settings
from backend.plugin.ai_assistant.service.data_assistant_service import DataAssistantService

try:
    from langchain_core.tools import StructuredTool
    LANGCHAIN_TOOLS_AVAILABLE = True
except ImportError:
    StructuredTool = None  # type: ignore
    LANGCHAIN_TOOLS_AVAILABLE = False


@dataclass(frozen=True)
class AssistantTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    executor: Callable[..., Awaitable[str]]
    async_only: bool = True


async def _execute_query_device_reports(*, content: str, user_id: int, session_uuid: str, token: str, action_params: dict[str, str]) -> str:
    return await DataAssistantService.execute_action(
        action_name='query_device_reports',
        content=content,
        user_id=user_id,
        session_uuid=session_uuid,
        token=token,
        action_params=action_params,
    )


TOOL_REGISTRY: dict[str, AssistantTool] = {
    'query_device_reports': AssistantTool(
        name='query_device_reports',
        description='查询设备上报记录，适用于按 IMEI、时间范围、groupId、分页条件查询设备上报数据。',
        input_schema={
            'type': 'object',
            'properties': {
                'imei': {'type': 'string'},
                'startTime': {'type': 'string'},
                'endTime': {'type': 'string'},
                'groupId': {'type': 'string'},
                'page': {'type': 'string'},
                'limit': {'type': 'string'},
            },
            'required': ['imei'],
        },
        executor=_execute_query_device_reports,
    )
}


def get_enabled_tools() -> dict[str, AssistantTool]:
    enabled = {name.strip() for name in settings.AI_ASSISTANT_AGENT_ENABLED_TOOLS if name.strip()}
    return {name: tool for name, tool in TOOL_REGISTRY.items() if not enabled or name in enabled}


def _build_args_model(tool: AssistantTool) -> type[Any]:
    properties = tool.input_schema.get('properties', {})
    required = set(tool.input_schema.get('required', []))
    fields: dict[str, tuple[type[Any], Any]] = {}
    for name in properties:
        default = ... if name in required else None
        fields[name] = (str | None, Field(default=default))
    return create_model(f'{tool.name.title().replace("_", "")}Args', **fields)


def build_langchain_tools(*, content: str, user_id: int, session_uuid: str, token: str) -> list[Any]:
    if not LANGCHAIN_TOOLS_AVAILABLE or StructuredTool is None:
        return []
    tools: list[Any] = []
    for assistant_tool in get_enabled_tools().values():
        input_schema = assistant_tool.input_schema

        async def _arun(_assistant_tool: AssistantTool = assistant_tool, **kwargs: Any) -> str:
            normalized_params = {str(key): str(value).strip() for key, value in kwargs.items() if str(value).strip()}
            return await _assistant_tool.executor(
                content=content,
                user_id=user_id,
                session_uuid=session_uuid,
                token=token,
                action_params=normalized_params,
            )

        tools.append(
            StructuredTool.from_function(
                func=None,
                coroutine=_arun,
                name=assistant_tool.name,
                description=assistant_tool.description,
                args_schema=_build_args_model(assistant_tool),
            )
        )
    return tools
