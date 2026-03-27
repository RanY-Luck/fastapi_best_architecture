from datetime import datetime
from typing import Literal

from pydantic import Field

from backend.common.schema import SchemaBase

AssistantRouteType = Literal['chat', 'data', 'playwright', 'agent']
AssistantRunStatus = Literal['pending', 'running', 'completed', 'failed']
AssistantMessageRole = Literal['user', 'assistant', 'system']


class ConversationCreateParam(SchemaBase):
    title: str | None = Field(None, description='会话标题')


class ConversationDetail(SchemaBase):
    id: int = Field(description='会话ID')
    title: str = Field(description='会话标题')
    status: str = Field(description='会话状态')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class ChatMessageCreateParam(SchemaBase):
    conversation_id: int | None = Field(None, description='会话ID，为空时自动创建会话')
    content: str = Field(min_length=1, description='用户消息')
    action_name: str | None = Field(None, description='显式动作名称')
    action_params: dict[str, str] = Field(default_factory=dict, description='动作参数')


class MessageDetail(SchemaBase):
    id: int = Field(description='消息ID')
    conversation_id: int = Field(description='会话ID')
    role: AssistantMessageRole = Field(description='消息角色')
    content: str = Field(description='消息内容')
    action_type: AssistantRouteType | None = Field(None, description='动作类型')
    action_status: AssistantRunStatus | None = Field(None, description='动作状态')
    created_time: datetime = Field(description='创建时间')


class ActionRunDetail(SchemaBase):
    id: int = Field(description='执行记录ID')
    conversation_id: int = Field(description='会话ID')
    message_id: int = Field(description='消息ID')
    route_type: AssistantRouteType = Field(description='路由类型')
    target_name: str | None = Field(None, description='目标动作名称')
    status: AssistantRunStatus = Field(description='执行状态')
    celery_task_id: str | None = Field(None, description='Celery任务ID')
    result_summary: str | None = Field(None, description='结果摘要')
    error_summary: str | None = Field(None, description='错误摘要')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')


class ChatSendResult(SchemaBase):
    conversation: ConversationDetail = Field(description='会话信息')
    user_message: MessageDetail = Field(description='用户消息')
    assistant_message: MessageDetail | None = Field(None, description='同步返回的助手消息')
    action_run: ActionRunDetail | None = Field(None, description='动作执行信息')
    accepted: bool = Field(description='是否异步受理')


class ConversationHistoryDetail(SchemaBase):
    conversation: ConversationDetail = Field(description='会话信息')
    messages: list[MessageDetail] = Field(description='消息列表')


class ChatRoutePlan(SchemaBase):
    route_type: AssistantRouteType = Field(description='路由类型')
    target_name: str | None = Field(None, description='目标动作')
    sync_allowed: bool = Field(default=False, description='是否允许同步执行')
    reason: str | None = Field(None, description='判定原因')
