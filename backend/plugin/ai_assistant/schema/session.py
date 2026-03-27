from pydantic import Field

from backend.common.schema import SchemaBase


class AssistantSessionStatus(SchemaBase):
    user_id: int = Field(description='用户ID')
    session_uuid: str = Field(description='会话UUID')
    room_name: str = Field(description='Socket房间名')
    browser_context_key: str = Field(description='浏览器上下文Key')
    playwright_available: bool = Field(description='Playwright是否可用')
    browser_context_active: bool = Field(description='浏览器上下文是否已激活')


class AssistantSessionResetResult(SchemaBase):
    reset: bool = Field(description='是否已重置')
    browser_context_key: str = Field(description='浏览器上下文Key')
