import json

from backend.plugin.ai_assistant.service.java_api_service import JavaApiService


class DataAssistantService:
    """数据型 AI 助手执行服务。"""

    @staticmethod
    def _normalize_action_params(action_params: dict[str, str] | None) -> dict[str, str]:
        if not action_params:
            return {}
        normalized: dict[str, str] = {}
        for key, value in action_params.items():
            text = str(value).strip()
            if text:
                normalized[str(key)] = text
        return normalized

    @classmethod
    async def execute_action(
        cls,
        *,
        action_name: str | None,
        content: str,
        user_id: int,
        session_uuid: str,
        token: str,
        action_params: dict[str, str] | None = None,
    ) -> str:
        normalized_params = cls._normalize_action_params(action_params)
        if action_name == 'query_device_reports':
            return await cls._execute_query_device_reports(
                content=content,
                user_id=user_id,
                session_uuid=session_uuid,
                token=token,
                action_params=normalized_params,
            )
        raise ValueError(f'未注册的数据动作: {action_name}')

    @classmethod
    async def _execute_query_device_reports(
        cls,
        *,
        content: str,
        user_id: int,
        session_uuid: str,
        token: str,
        action_params: dict[str, str],
    ) -> str:
        payload_text = await JavaApiService.execute_action(
            action_name='query_device_reports',
            content=content,
            user_id=user_id,
            session_uuid=session_uuid,
            token=token,
            action_params=action_params,
        )
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError:
            return payload_text

        result = {
            'action_name': 'query_device_reports',
            'source': 'data_assistant',
            'status': 'completed',
            'query': {
                'imei': action_params.get('imei') or action_params.get('device_keyword', content.strip()),
                'startTime': action_params.get('startTime', ''),
                'endTime': action_params.get('endTime', ''),
                'groupId': action_params.get('groupId', ''),
                'page': action_params.get('page', ''),
                'limit': action_params.get('limit', ''),
                'time_range': action_params.get('time_range', ''),
            },
            'data': payload,
        }
        if isinstance(payload, dict):
            data_section = payload.get('data') if isinstance(payload.get('data'), dict) else payload
            rows = data_section.get('rows') if isinstance(data_section, dict) else None
            if not isinstance(rows, list):
                rows = data_section.get('list') if isinstance(data_section, dict) else None
            if isinstance(rows, list):
                result['data'] = {
                    **data_section,
                    'rows': rows,
                    'count': data_section.get('count', data_section.get('total', len(rows))),
                }
        return json.dumps(result, ensure_ascii=False, indent=2)
