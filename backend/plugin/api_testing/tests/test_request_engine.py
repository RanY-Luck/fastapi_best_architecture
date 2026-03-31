import asyncio
from types import SimpleNamespace

from backend.plugin.api_testing.schema.request import RequestEngine


def test_execute_step_supports_structured_payloads_and_enabled_flags(monkeypatch):
    captured = {}

    async def fake_send_request(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            status_code=200,
            headers={'content-type': 'application/json'},
            json_data={'ok': True},
            text='{"ok":true}',
            elapsed_time=12,
            error=None,
        )

    monkeypatch.setattr('backend.plugin.api_testing.schema.request.send_request', fake_send_request)

    step = SimpleNamespace(
        url='/orders',
        method='POST',
        headers=[
            {'enabled': False, 'key': 'X-Disabled', 'value': 'off'},
            {'enabled': True, 'key': 'X-Trace', 'value': 'trace-id'},
        ],
        params=[
            {'enabled': False, 'key': 'skip', 'value': 1},
            {'enabled': True, 'key': 'page', 'value': 2},
        ],
        body={
            'mode': 'form-data',
            'items': [
                {'enabled': False, 'key': 'drop', 'value': 'x'},
                {'enabled': True, 'key': 'keyword', 'value': 'demo'},
            ],
        },
        files=[{'enabled': True, 'key': 'file', 'value': '/tmp/demo.txt'}],
        auth={'type': 'apiKey', 'in': 'query', 'key': 'token', 'value': 'abc'},
        extract=[{'enabled': True, 'key': 'order_id', 'value': '$.id'}],
        validate=None,
        sql_queries=None,
        timeout=30,
        retry=0,
        retry_interval=1,
    )

    result = asyncio.run(RequestEngine.execute_step(step, 'https://example.com', {'X-Global': 'yes'}))

    assert result.success is True
    assert captured['url'] == 'https://example.com/orders'
    assert captured['headers'] == {'X-Global': 'yes', 'X-Trace': 'trace-id'}
    assert captured['params'] == {'page': 2, 'token': 'abc'}
    assert captured['json_data'] is None
    assert captured['data'] == {'keyword': 'demo'}
    assert captured['files'] == {'file': '/tmp/demo.txt'}
    assert result.request_data['body_mode'] == 'form-data'


def test_execute_step_filters_disabled_validations_and_sql_queries(monkeypatch):
    async def fake_send_request(**kwargs):
        return SimpleNamespace(
            status_code=200,
            headers={},
            json_data={'count': 1},
            text='ok',
            elapsed_time=5,
            error=None,
        )

    async def fake_execute_assertions(assertions_config, response_data, result):
        result.assertions.append({'count': len(assertions_config)})
        assert assertions_config == [
            {'expected': 1, 'path': '$.count', 'source': 'json', 'type': 'equals'}
        ]
        return True

    async def fake_execute_sql_queries(sql_configs, result, variables):
        result.sql_results.append({'count': len(sql_configs)})
        assert sql_configs == [{'name': 'enabled', 'query': 'select 1'}]
        return True

    monkeypatch.setattr('backend.plugin.api_testing.schema.request.send_request', fake_send_request)
    monkeypatch.setattr(RequestEngine, '_execute_assertions', fake_execute_assertions)
    monkeypatch.setattr(RequestEngine, '_execute_sql_queries', fake_execute_sql_queries)

    step = SimpleNamespace(
        url='/demo',
        method='GET',
        headers=None,
        params=None,
        body=None,
        files=None,
        auth=None,
        extract=None,
        validate=[
            {'enabled': False, 'expected': 0, 'path': '$.skip', 'source': 'json', 'type': 'equals'},
            {'enabled': True, 'expected': 1, 'path': '$.count', 'source': 'json', 'type': 'equals'},
        ],
        sql_queries=[
            {'enabled': False, 'name': 'disabled', 'query': 'select 0'},
            {'enabled': True, 'name': 'enabled', 'query': 'select 1'},
        ],
        timeout=30,
        retry=0,
        retry_interval=1,
    )

    result = asyncio.run(RequestEngine.execute_step(step, 'https://example.com'))

    assert result.success is True
    assert result.assertions == [{'count': 1}]
    assert result.sql_results == [{'count': 1}]


def test_normalize_body_payload_keeps_legacy_json_body():
    mode, json_data, form_data = RequestEngine._normalize_body_payload({'keyword': 'demo'})

    assert mode == 'json'
    assert json_data == {'keyword': 'demo'}
    assert form_data is None
