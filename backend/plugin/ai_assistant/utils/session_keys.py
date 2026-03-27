def build_room_name(user_id: int | None, session_uuid: str) -> str:
    if user_id is None:
        return session_uuid
    return f'user:{user_id}:session:{session_uuid}'


def build_browser_context_key(user_id: int, session_uuid: str) -> str:
    return f'ai_assistant:{user_id}:{session_uuid}:browser_context'


def build_runtime_prefix(user_id: int, session_uuid: str) -> str:
    return f'ai_assistant:{user_id}:{session_uuid}'
