from datetime import datetime

from pydantic import Field

from backend.common.schema import SchemaBase


class AssistantTaskEventPayload(SchemaBase):
    event: str
    task_id: str | None = None
    run_id: int | None = None
    conversation_id: int | None = None
    message_id: int | None = None
    status: str | None = None
    message: str | None = None
    created_time: datetime = Field(default_factory=datetime.now)
