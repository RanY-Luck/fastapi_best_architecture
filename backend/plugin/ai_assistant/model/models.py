from datetime import datetime
from typing import List

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, UniversalText, id_key


class AiConversation(Base):
    """AI助手会话表"""
    __tablename__ = 'ai_assistant_conversation'

    id: Mapped[id_key] = mapped_column(init=False)
    user_id: Mapped[int] = mapped_column(index=True, comment='所属用户ID')
    session_uuid: Mapped[str] = mapped_column(String(64), index=True, comment='登录会话UUID')
    title: Mapped[str] = mapped_column(String(255), default='新会话', comment='会话标题')
    status: Mapped[str] = mapped_column(String(32), default='active', comment='会话状态')

    messages: Mapped[List['AiMessage']] = relationship('AiMessage', back_populates='conversation', init=False)
    action_runs: Mapped[List['AiActionRun']] = relationship('AiActionRun', back_populates='conversation', init=False)


class AiMessage(Base):
    """AI助手消息表"""
    __tablename__ = 'ai_assistant_message'

    id: Mapped[id_key] = mapped_column(init=False)
    conversation_id: Mapped[int] = mapped_column(ForeignKey('ai_assistant_conversation.id'), index=True, comment='所属会话ID')
    role: Mapped[str] = mapped_column(String(16), comment='消息角色')
    content: Mapped[str] = mapped_column(UniversalText, comment='消息内容')
    action_type: Mapped[str | None] = mapped_column(String(32), default=None, comment='动作类型')
    action_status: Mapped[str | None] = mapped_column(String(32), default=None, comment='动作状态')

    conversation: Mapped['AiConversation'] = relationship('AiConversation', back_populates='messages', init=False)
    action_runs: Mapped[List['AiActionRun']] = relationship('AiActionRun', back_populates='message', init=False)


class AiActionRun(Base):
    """AI助手动作执行表"""
    __tablename__ = 'ai_assistant_action_run'

    id: Mapped[id_key] = mapped_column(init=False)
    conversation_id: Mapped[int] = mapped_column(ForeignKey('ai_assistant_conversation.id'), index=True, comment='所属会话ID')
    message_id: Mapped[int] = mapped_column(ForeignKey('ai_assistant_message.id'), index=True, comment='所属消息ID')
    user_id: Mapped[int] = mapped_column(index=True, comment='所属用户ID')
    session_uuid: Mapped[str] = mapped_column(String(64), index=True, comment='登录会话UUID')
    route_type: Mapped[str] = mapped_column(String(32), comment='执行路由类型')
    target_name: Mapped[str | None] = mapped_column(String(128), default=None, comment='目标动作名称')
    status: Mapped[str] = mapped_column(String(32), default='pending', comment='执行状态')
    celery_task_id: Mapped[str | None] = mapped_column(String(64), default=None, index=True, comment='Celery任务ID')
    result_summary: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='结果摘要')
    error_summary: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='错误摘要')
    finished_time: Mapped[datetime | None] = mapped_column(default=None, comment='完成时间')

    conversation: Mapped['AiConversation'] = relationship('AiConversation', back_populates='action_runs', init=False)
    message: Mapped['AiMessage'] = relationship('AiMessage', back_populates='action_runs', init=False)
