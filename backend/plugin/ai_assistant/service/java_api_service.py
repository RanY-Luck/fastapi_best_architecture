import json
from urllib.parse import urljoin

import httpx

from backend.common.log import log
from backend.core.conf import settings
from backend.plugin.ai_assistant.service.action_catalog import ACTION_CATALOG


class JavaApiService:
    """Java后端API调用服务。"""

    @staticmethod
    def _get_base_url() -> str:
        base_url = str(getattr(settings, 'AI_ASSISTANT_JAVA_API_BASE_URL', '') or '').strip()
        if not base_url:
            raise ValueError('未配置 AI_ASSISTANT_JAVA_API_BASE_URL，无法调用 Java API')
        return base_url.rstrip('/') + '/'

    @staticmethod
    def _get_action_config(action_name: str | None) -> dict:
        if not action_name or action_name not in ACTION_CATALOG:
            raise ValueError(f'未找到 Java API 动作映射: {action_name}')
        action_config = ACTION_CATALOG[action_name]
        java_api_config = action_config.get('java_api')
        if not isinstance(java_api_config, dict):
            raise ValueError(f'动作未配置 Java API 信息: {action_name}')
        return java_api_config

    @staticmethod
    def _resolve_path(java_api_config: dict, action_name: str | None) -> str:
        path = java_api_config.get('path')
        if isinstance(path, str) and path.strip():
            return path.lstrip('/')

        path_setting = java_api_config.get('path_setting')
        if isinstance(path_setting, str) and path_setting.strip():
            configured_path = str(getattr(settings, path_setting, '') or '').strip()
            if configured_path:
                return configured_path.lstrip('/')
            raise ValueError(f'未配置 {path_setting}，无法调用动作 {action_name}')

        raise ValueError(f'动作缺少可用的 Java API 路径配置: {action_name}')

    @staticmethod
    def _resolve_authorization_header(token: str) -> str:
        configured_authorization = str(settings.AI_ASSISTANT_JAVA_API_AUTHORIZATION or '').strip()
        if configured_authorization:
            return configured_authorization
        normalized_token = token.strip()
        if normalized_token.lower().startswith('bearer '):
            return normalized_token
        return f'Bearer {normalized_token}'

    @classmethod
    def _build_headers(cls, *, token: str, session_uuid: str, user_id: int) -> dict[str, str]:
        headers = {
            'Authorization': cls._resolve_authorization_header(token),
            'X-Session-UUID': session_uuid,
            'X-User-ID': str(user_id),
        }
        configured_headers = settings.AI_ASSISTANT_JAVA_API_HEADERS
        if isinstance(configured_headers, dict):
            headers.update({str(key): str(value) for key, value in configured_headers.items()})
        return headers

    @staticmethod
    def _build_request_kwargs(*, java_api_config: dict, content: str, action_params: dict[str, str] | None = None) -> dict:
        request_mode = str(java_api_config.get('request_mode', 'none'))
        if request_mode == 'none':
            return {}
        if request_mode == 'message_json':
            return {'json': {'message': content}}
        if request_mode == 'message_query':
            return {'params': {'message': content}}
        if request_mode == 'device_reports_query':
            raw_params = {str(key): str(value).strip() for key, value in (action_params or {}).items() if str(value).strip()}
            params: dict[str, str] = {}
            imei = raw_params.get('imei') or raw_params.get('device_keyword') or content.strip()
            if imei:
                params['imei'] = imei
            if raw_params.get('startTime'):
                params['startTime'] = raw_params['startTime']
            if raw_params.get('endTime'):
                params['endTime'] = raw_params['endTime']
            if raw_params.get('page'):
                params['page'] = raw_params['page']
            if raw_params.get('limit'):
                params['limit'] = raw_params['limit']
            if raw_params.get('groupId'):
                params['groupId'] = raw_params['groupId']
            if raw_params.get('time_range') and ('startTime' not in params or 'endTime' not in params):
                params['time_range'] = raw_params['time_range']
            return {'params': params}
        raise ValueError(f'不支持的 Java API 请求模式: {request_mode}')

    @staticmethod
    def _normalize_response(*, response: httpx.Response, java_api_config: dict) -> str:
        result_mode = str(java_api_config.get('result_mode', 'json'))
        content_type = response.headers.get('content-type', '')

        if 'application/json' in content_type:
            payload = response.json()
            if result_mode == 'raw_json':
                return json.dumps(payload, ensure_ascii=False, indent=2)
            if isinstance(payload, dict):
                if payload.get('msg') and payload.get('data') is None:
                    return str(payload['msg'])
                if 'data' in payload and payload['data'] is not None:
                    return json.dumps(payload['data'], ensure_ascii=False, indent=2)
            return json.dumps(payload, ensure_ascii=False, indent=2)

        return response.text.strip() or f'Java API 调用成功，状态码 {response.status_code}'

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
        java_api_config = cls._get_action_config(action_name)
        method = str(java_api_config.get('method', 'GET')).upper()
        path = cls._resolve_path(java_api_config, action_name)
        url = urljoin(cls._get_base_url(), path)
        timeout = float(settings.AI_ASSISTANT_JAVA_API_TIMEOUT)
        verify_ssl = bool(settings.AI_ASSISTANT_JAVA_API_VERIFY_SSL)

        request_kwargs = cls._build_request_kwargs(
            java_api_config=java_api_config,
            content=content,
            action_params=action_params,
        )
        headers = cls._build_headers(token=token, session_uuid=session_uuid, user_id=user_id)

        log.info(
            f'AI助手调用 Java API action={action_name} method={method} url={url} user_id={user_id} session_uuid={session_uuid}'
        )

        async with httpx.AsyncClient(timeout=timeout, verify=verify_ssl) as client:
            response = await client.request(method=method, url=url, headers=headers, **request_kwargs)
            response.raise_for_status()
            return cls._normalize_response(response=response, java_api_config=java_api_config)
