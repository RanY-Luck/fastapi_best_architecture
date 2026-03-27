ACTION_CATALOG: dict[str, dict[str, object]] = {
    'query_device_reports': {
        'keywords': ['设备上报', '上报记录', '设备记录', 'report'],
        'route_type': 'data',
        'target_name': 'query_device_reports',
        'sync_allowed': False,
        'parameter_schema': {
            'device_keyword': {'required': False},
            'time_range': {'required': False},
            'limit': {'required': False},
        },
        'java_api': {
            'method': 'GET',
            'path_setting': 'AI_ASSISTANT_JAVA_API_DEVICE_REPORTS_PATH',
            'request_mode': 'device_reports_query',
            'result_mode': 'raw_json',
        },
    },
    'open_dashboard': {
        'keywords': ['打开首页', '打开控制台', 'dashboard'],
        'route_type': 'playwright',
        'target_name': 'open_dashboard',
        'sync_allowed': False,
        'playwright': {
            'flow_name': 'open_dashboard',
        },
    },
}
