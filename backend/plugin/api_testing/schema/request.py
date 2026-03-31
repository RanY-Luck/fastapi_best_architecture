#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
请求相关模型
"""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from jsonpath_ng import parse
from pydantic import BaseModel, Field

from backend.common.log import log
from backend.plugin.api_testing.model.models import ApiTestStep
from backend.plugin.api_testing.utils.assertion import Assertion, AssertionEngine
from backend.plugin.api_testing.utils.http_client import RequestOptions, send_request
from backend.plugin.api_testing.utils.sql_executor import SQLExecutor, SQLQuery


class KeyValueItem(BaseModel):
    """支持启用状态的键值对条目"""

    key: str = Field('', description='键')
    value: Any = Field(None, description='值')
    enabled: bool = Field(True, description='是否启用')


class BodyRequestPayload(BaseModel):
    """结构化请求体"""

    mode: Literal['json', 'form-data', 'x-www-form-urlencoded'] = Field(
        'json', description='请求体模式'
    )
    items: List[KeyValueItem] = Field(default_factory=list, description='请求体条目')


class ApiRequestSchema(BaseModel):
    """API请求模型"""

    url: str = Field(..., description='请求URL')
    method: str = Field(..., description='请求方法', examples=['GET', 'POST', 'PUT', 'DELETE'])
    headers: Optional[Dict[str, str]] = Field(None, description='请求头')
    params: Optional[Dict[str, Any]] = Field(None, description='查询参数')
    data: Optional[Dict[str, Any]] = Field(None, description='表单数据')
    json_data: Optional[Dict[str, Any]] = Field(None, description='JSON数据')
    files: Optional[Dict[str, str]] = Field(None, description='上传文件，值为文件路径')
    auth: Optional[List[str]] = Field(None, description='认证信息[用户名, 密码]')
    options: Optional[RequestOptions] = Field(None, description='请求选项')


class ApiResponseSchema(BaseModel):
    """API响应模型"""

    url: str = Field(..., description='请求URL')
    method: str = Field(..., description='请求方法')
    status_code: int = Field(..., description='状态码')
    elapsed_time: float = Field(..., description='请求耗时(毫秒)')
    headers: Dict[str, str] = Field(..., description='响应头')
    cookies: Dict[str, str] = Field(..., description='响应cookies')
    content: str = Field(..., description='原始响应内容')
    text: str = Field(..., description='文本形式的响应')
    json_data: Optional[Dict[str, Any]] = Field(None, description='JSON形式的响应')
    error: Optional[str] = Field(None, description='错误信息')


class TestCaseRequest(BaseModel):
    """测试用例创建请求"""

    name: str = Field(..., description='用例名称')
    project_id: int = Field(..., description='所属项目ID')
    description: Optional[str] = Field(None, description='用例描述')
    pre_script: Optional[str] = Field(None, description='前置脚本')
    post_script: Optional[str] = Field(None, description='后置脚本')


class TestCaseResponse(BaseModel):
    """测试用例响应"""

    id: int
    name: str
    project_id: int
    project_name: Optional[str] = None
    description: Optional[str] = None
    pre_script: Optional[str] = None
    post_script: Optional[str] = None
    status: int
    created_time: str
    updated_time: str


class TestStepRequest(BaseModel):
    """测试步骤创建请求"""

    name: str = Field(..., description='步骤名称')
    test_case_id: int = Field(..., description='所属用例ID')
    url: str = Field(..., description='请求URL')
    method: str = Field(..., description='请求方法')
    headers: Optional[Dict[str, Any] | List[KeyValueItem]] = Field(None, description='请求头')
    params: Optional[Dict[str, Any] | List[KeyValueItem]] = Field(None, description='查询参数')
    body: Optional[Dict[str, Any] | BodyRequestPayload] = Field(None, description='请求体')
    files: Optional[Dict[str, Any] | List[KeyValueItem]] = Field(None, description='上传文件')
    auth: Optional[Dict[str, Any]] = Field(None, description='认证信息')
    extract: Optional[Dict[str, Any] | List[KeyValueItem]] = Field(None, description='提取变量')
    validations: Optional[List[Dict[str, Any]]] = Field(None, description='断言列表')
    sql_queries: Optional[List[Dict[str, Any]]] = Field(None, description='SQL查询列表')
    timeout: int = Field(30, ge=1, le=3600, description='超时时间(秒)，范围1-3600')
    retry: int = Field(0, ge=0, le=10, description='重试次数，范围0-10')
    retry_interval: int = Field(1, ge=1, le=300, description='重试间隔(秒)，范围1-300')
    order: int = Field(..., description='步骤顺序')


class TestStepResponse(BaseModel):
    id: int
    name: str
    test_case_id: int
    test_case_name: Optional[str] = None
    url: str
    method: str
    headers: Optional[Dict[str, Any] | List[KeyValueItem]] = None
    params: Optional[Dict[str, Any] | List[KeyValueItem]] = None
    body: Optional[Dict[str, Any] | BodyRequestPayload] = None
    files: Optional[Dict[str, Any] | List[KeyValueItem]] = None
    auth: Optional[Dict[str, Any]] = None
    extract: Optional[Dict[str, Any] | List[KeyValueItem]] = None
    validations: Optional[List[Dict[str, Any]]] = None
    sql_queries: Optional[List[Dict[str, Any]]] = None
    timeout: int
    retry: int
    retry_interval: int
    order: int
    status: int
    created_time: str
    updated_time: str


class ProjectCreateRequest(BaseModel):
    """API项目创建请求"""

    name: str = Field(..., description='项目名称')
    description: Optional[str] = Field(None, description='项目描述')
    base_url: str = Field(..., description='基础URL')
    headers: Optional[Dict[str, str]] = Field(None, description='全局请求头')
    variables: Optional[Dict[str, Any]] = Field(None, description='全局变量')
    status: int = Field(1, description='状态 1启用 0禁用')


class ProjectUpdateRequest(BaseModel):
    """API项目更新请求"""

    name: Optional[str] = Field(None, description='项目名称')
    description: Optional[str] = Field(None, description='项目描述')
    base_url: Optional[str] = Field(None, description='基础URL')
    headers: Optional[Dict[str, str]] = Field(None, description='全局请求头')
    variables: Optional[Dict[str, Any]] = Field(None, description='全局变量')
    status: Optional[int] = Field(None, description='状态 1启用 0禁用')


class ProjectResponse(BaseModel):
    """API项目响应"""

    id: int
    name: str
    description: Optional[str] = None
    base_url: str
    headers: Optional[Dict[str, str]] = None
    variables: Optional[Dict[str, Any]] = None
    status: int
    created_time: str
    updated_time: str


class TestCaseCreateRequest(BaseModel):
    """测试用例创建请求"""

    name: str = Field(..., description='用例名称')
    project_id: int = Field(..., description='所属项目ID')
    description: Optional[str] = Field(None, description='用例描述')
    pre_script: Optional[str] = Field(None, description='前置脚本')
    post_script: Optional[str] = Field(None, description='后置脚本')
    status: int = Field(1, description='状态 1启用 0禁用')


class TestCaseUpdateRequest(BaseModel):
    """测试用例更新请求"""

    name: Optional[str] = Field(None, description='用例名称')
    description: Optional[str] = Field(None, description='用例描述')
    pre_script: Optional[str] = Field(None, description='前置脚本')
    post_script: Optional[str] = Field(None, description='后置脚本')
    status: Optional[int] = Field(None, description='状态 1启用 0禁用')


class TestSuiteCreateRequest(BaseModel):
    """测试集合创建请求"""

    name: str = Field(..., description='集合名称')
    project_id: int = Field(..., description='所属项目ID')
    description: Optional[str] = Field(None, description='集合描述')
    case_ids: List[int] = Field(default_factory=list, description='集合包含的测试用例ID列表')
    status: int = Field(1, description='状态 1启用 0禁用')


class TestSuiteUpdateRequest(BaseModel):
    """测试集合更新请求"""

    name: Optional[str] = Field(None, description='集合名称')
    description: Optional[str] = Field(None, description='集合描述')
    case_ids: Optional[List[int]] = Field(None, description='集合包含的测试用例ID列表')
    status: Optional[int] = Field(None, description='状态 1启用 0禁用')


class TestSuiteResponse(BaseModel):
    """测试集合响应"""

    id: int
    name: str
    project_id: int
    project_name: Optional[str] = None
    description: Optional[str] = None
    status: int
    case_ids: List[int] = Field(default_factory=list)
    case_count: int
    created_time: str
    updated_time: str


class TestStepCreateRequest(BaseModel):
    """测试步骤创建请求"""

    name: str = Field(..., description='步骤名称')
    test_case_id: int = Field(..., description='所属用例ID')
    url: str = Field(..., description='请求URL')
    method: str = Field(..., description='请求方法')
    headers: Optional[Dict[str, Any] | List[KeyValueItem]] = Field(None, description='请求头')
    params: Optional[Dict[str, Any] | List[KeyValueItem]] = Field(None, description='查询参数')
    body: Optional[Dict[str, Any] | BodyRequestPayload] = Field(None, description='请求体')
    files: Optional[Dict[str, Any] | List[KeyValueItem]] = Field(None, description='上传文件')
    auth: Optional[Dict[str, Any]] = Field(None, description='认证信息')
    extract: Optional[Dict[str, Any] | List[KeyValueItem]] = Field(None, description='提取变量')
    validations: Optional[List[Dict[str, Any]]] = Field(None, description='断言列表')
    sql_queries: Optional[List[Dict[str, Any]]] = Field(None, description='SQL查询列表')
    timeout: int = Field(30, ge=1, le=3600, description='超时时间(秒)，范围1-3600')
    retry: int = Field(0, ge=0, le=10, description='重试次数，范围0-10')
    retry_interval: int = Field(1, ge=1, le=300, description='重试间隔(秒)，范围1-300')
    order: int = Field(..., description='步骤顺序')
    status: int = Field(1, description='状态 1启用 0禁用')


class TestStepUpdateRequest(BaseModel):
    """测试步骤更新请求"""

    name: Optional[str] = Field(None, description='步骤名称')
    url: Optional[str] = Field(None, description='请求URL')
    test_case_id: int = Field(..., description='所属用例ID')
    method: Optional[str] = Field(None, description='请求方法')
    headers: Optional[Dict[str, Any] | List[KeyValueItem]] = Field(None, description='请求头')
    params: Optional[Dict[str, Any] | List[KeyValueItem]] = Field(None, description='查询参数')
    body: Optional[Dict[str, Any] | BodyRequestPayload] = Field(None, description='请求体')
    files: Optional[Dict[str, Any] | List[KeyValueItem]] = Field(None, description='上传文件')
    auth: Optional[Dict[str, Any]] = Field(None, description='认证信息')
    extract: Optional[Dict[str, Any] | List[KeyValueItem]] = Field(None, description='提取变量')
    validations: Optional[List[Dict[str, Any]]] = Field(None, description='断言列表')
    sql_queries: Optional[List[Dict[str, Any]]] = Field(None, description='SQL查询列表')
    timeout: Optional[int] = Field(None, ge=1, le=3600, description='超时时间(秒)，范围1-3600')
    retry: Optional[int] = Field(None, ge=0, le=10, description='重试次数，范围0-10')
    retry_interval: Optional[int] = Field(None, ge=1, le=300, description='重试间隔(秒)，范围1-300')
    order: Optional[int] = Field(None, description='步骤顺序')
    status: Optional[int] = Field(None, description='状态 1启用 0禁用')


class TestReportCreateRequest(BaseModel):
    """测试报告创建请求"""

    test_case_id: int = Field(..., description='所属用例ID')
    name: str = Field(..., description='报告名称')
    success: bool = Field(..., description='是否成功')
    total_steps: int = Field(..., description='总步骤数')
    success_steps: int = Field(..., description='成功步骤数')
    fail_steps: int = Field(..., description='失败步骤数')
    start_time: datetime = Field(..., description='开始时间')
    end_time: datetime = Field(..., description='结束时间')
    duration: int = Field(..., description='执行时长(毫秒)')
    details: Dict[str, Any] = Field(..., description='报告详情')


class TestReportResponse(BaseModel):
    """测试报告响应"""

    id: int
    test_case_id: int
    test_case_name: Optional[str] = None
    name: str
    success: int
    total_steps: int
    success_steps: int
    fail_steps: int
    start_time: str
    end_time: str
    duration: int
    details: Dict[str, Any]
    created_time: str


class BatchExecutionRequest(BaseModel):
    """批量执行请求"""

    environment_id: Optional[int] = Field(None, description='环境ID')
    max_concurrency: int = Field(5, ge=1, le=20, description='最大并发数，范围1-20')


class BatchExecutionResponse(BaseModel):
    """批量执行响应"""

    batch_report_id: int
    name: str
    target_type: str
    target_id: int
    project_id: int
    suite_id: Optional[int] = None
    success: bool
    total_cases: int
    success_cases: int
    fail_cases: int
    max_concurrency: int
    duration: int
    report_ids: List[int] = Field(default_factory=list)
    results: List[Dict[str, Any]] = Field(default_factory=list)
    start_time: str
    end_time: str


class BatchExecutionReportResponse(BaseModel):
    """批量执行报告响应"""

    id: int
    project_id: int
    project_name: Optional[str] = None
    suite_id: Optional[int] = None
    suite_name: Optional[str] = None
    name: str
    target_type: str
    success: int
    total_cases: int
    success_cases: int
    fail_cases: int
    max_concurrency: int
    start_time: str
    end_time: str
    duration: int
    report_ids: List[int] = Field(default_factory=list)
    details: Dict[str, Any]
    created_time: str


class StepReorderRequest(BaseModel):
    """步骤重新排序请求"""

    step_orders: List[Dict[str, int]] = Field(..., description='步骤排序列表，包含step_id和order字段')


class StepExecutionResult:
    """步骤执行结果"""

    def __init__(self):
        self.success = True
        self.error = None
        self.request_data = {}
        self.response_data = {}
        self.assertions = []
        self.sql_results = []
        self.extracted_variables = {}
        self.start_time = None
        self.end_time = None
        self.duration = 0

    def to_dict(self):
        """转换为字典"""
        return {
            'success': self.success,
            'error': self.error,
            'request_data': self.request_data,
            'response_data': self.response_data,
            'assertions': self.assertions,
            'sql_results': self.sql_results,
            'extracted_variables': self.extracted_variables,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': self.duration,
        }


class RequestEngine:
    """请求执行引擎"""

    @staticmethod
    async def execute_step(
        step: ApiTestStep,
        base_url: str,
        global_headers: Optional[Dict[str, str]] = None,
        variables: Optional[Dict[str, Any]] = None,
    ) -> StepExecutionResult:
        """
        执行测试步骤

        :param step: 测试步骤对象
        :param base_url: 项目基础URL
        :param global_headers: 全局请求头
        :param variables: 共享变量
        :return: 步骤执行结果
        """
        result = StepExecutionResult()
        result.start_time = datetime.now()
        variables = variables or {}

        try:
            url = RequestEngine._build_url(step.url, base_url)

            step_headers = RequestEngine._normalize_key_value_payload(step.headers, stringify_values=True)
            headers = RequestEngine._merge_headers(global_headers, step_headers)
            params = RequestEngine._normalize_key_value_payload(step.params)
            files = RequestEngine._normalize_key_value_payload(step.files)
            extract_config = RequestEngine._normalize_key_value_payload(
                step.extract, stringify_values=True
            )
            validations = RequestEngine._normalize_enabled_list(step.validate)
            sql_queries = RequestEngine._normalize_enabled_list(step.sql_queries)
            body_mode, json_body, form_body = RequestEngine._normalize_body_payload(step.body)
            request_auth, auth_headers, auth_params = RequestEngine._normalize_auth_payload(step.auth)

            if auth_headers:
                headers.update(auth_headers)
            if auth_params:
                params = RequestEngine._merge_key_value_dicts(params, auth_params)

            request_options = RequestOptions(
                timeout=step.timeout,
                retry_count=step.retry,
                retry_interval=step.retry_interval,
            )

            response = await send_request(
                method=step.method,
                url=url,
                params=params,
                headers=headers,
                data=form_body,
                json_data=json_body,
                files=files,
                auth=request_auth,
                options=request_options,
            )

            result.request_data = {
                'url': url,
                'method': step.method,
                'headers': headers,
                'params': params or {},
                'data': form_body,
                'json_data': json_body,
                'files': files or {},
                'body_mode': body_mode,
                'auth': step.auth,
            }

            result.response_data = {
                'status_code': response.status_code,
                'headers': response.headers,
                'json': response.json_data,
                'text': response.text,
                'elapsed_time': response.elapsed_time,
            }

            if response.error:
                result.success = False
                result.error = response.error
                return result

            if validations:
                assertions_success = await RequestEngine._execute_assertions(
                    validations, result.response_data, result
                )
                if not assertions_success:
                    result.success = False

            if sql_queries:
                sql_success = await RequestEngine._execute_sql_queries(sql_queries, result, variables)
                if not sql_success:
                    result.success = False

            if extract_config and response.json_data:
                RequestEngine._extract_variables(
                    extract_config, response.json_data, result, variables
                )

        except Exception as e:
            result.success = False
            result.error = str(e)
            log.error(f'执行测试步骤失败: {e}')

        finally:
            result.end_time = datetime.now()
            result.duration = int((result.end_time - result.start_time).total_seconds() * 1000)

        return result

    @staticmethod
    def _build_url(url: str, base_url: str) -> str:
        """构建完整URL"""
        if url.startswith('http'):
            return url

        base_url = base_url.rstrip('/')
        if url.startswith('/'):
            return f'{base_url}{url}'
        return f'{base_url}/{url}'

    @staticmethod
    def _merge_headers(
        global_headers: Optional[Dict[str, str]],
        step_headers: Optional[Dict[str, Any]],
    ) -> Dict[str, str]:
        """合并请求头"""
        headers: Dict[str, str] = {}
        if global_headers:
            headers.update(global_headers)
        if step_headers:
            headers.update({key: str(value) for key, value in step_headers.items()})
        return headers

    @staticmethod
    def _merge_key_value_dicts(
        first: Optional[Dict[str, Any]], second: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        merged: Dict[str, Any] = {}
        if first:
            merged.update(first)
        if second:
            merged.update(second)
        return merged or None

    @staticmethod
    def _normalize_key_value_payload(
        payload: Optional[Dict[str, Any] | List[Dict[str, Any]]],
        stringify_values: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """兼容旧字典结构和新条目数组结构"""
        if not payload:
            return None

        if isinstance(payload, dict):
            normalized = {
                str(key).strip(): (str(value) if stringify_values and value is not None else value)
                for key, value in payload.items()
                if str(key).strip()
            }
            return normalized or None

        if not isinstance(payload, list):
            return None

        normalized: Dict[str, Any] = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            if item.get('enabled', True) is False:
                continue
            key = str(item.get('key', '')).strip()
            if not key:
                continue
            value = item.get('value')
            normalized[key] = str(value) if stringify_values and value is not None else value
        return normalized or None

    @staticmethod
    def _normalize_enabled_list(items: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """过滤掉显式禁用的列表条目"""
        if not items:
            return []

        normalized: List[Dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get('enabled', True) is False:
                continue
            cleaned = dict(item)
            cleaned.pop('enabled', None)
            normalized.append(cleaned)
        return normalized

    @staticmethod
    def _normalize_body_payload(
        payload: Optional[Dict[str, Any]],
    ) -> tuple[str, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """兼容旧 JSON body 和新 mode/items body"""
        if not payload:
            return 'json', None, None

        if isinstance(payload, dict) and payload.get('mode') in {
            'json',
            'form-data',
            'x-www-form-urlencoded',
        } and isinstance(payload.get('items'), list):
            mode = str(payload['mode'])
            body_items = RequestEngine._normalize_key_value_payload(payload['items'])
            if mode == 'json':
                return mode, body_items, None
            return mode, None, body_items

        return 'json', payload, None

    @staticmethod
    def _normalize_auth_payload(
        payload: Optional[Dict[str, Any]],
    ) -> tuple[Optional[tuple[str, str]], Dict[str, str], Dict[str, Any]]:
        """将结构化认证配置转换为请求层参数"""
        if not payload:
            return None, {}, {}

        auth_type = str(payload.get('type', payload.get('auth_type', ''))).strip().lower()

        if auth_type == 'bearer' or ('token' in payload and payload.get('token') is not None):
            token = str(payload.get('token', '')).strip()
            if not token:
                return None, {}, {}
            return None, {'Authorization': f'Bearer {token}'}, {}

        if (
            auth_type == 'basic'
            or 'username' in payload
            or 'password' in payload
        ):
            username = str(payload.get('username', ''))
            password = str(payload.get('password', ''))
            if not username and not password:
                return None, {}, {}
            return (username, password), {}, {}

        if auth_type == 'apikey' or auth_type == 'api_key' or 'key' in payload or 'value' in payload:
            key = str(payload.get('key', payload.get('name', ''))).strip()
            value = payload.get('value')
            location = str(payload.get('in', payload.get('location', 'header'))).strip().lower()
            if not key or value is None:
                return None, {}, {}
            if location == 'query':
                return None, {}, {key: value}
            return None, {key: str(value)}, {}

        return None, {}, {}

    @staticmethod
    async def _execute_assertions(
        assertions_config: List[Dict[str, Any]],
        response_data: Dict[str, Any],
        result: StepExecutionResult,
    ) -> bool:
        """执行断言"""
        all_success = True

        for assertion_dict in assertions_config:
            try:
                assertion = Assertion(**assertion_dict)
                assertion_result = AssertionEngine.execute_assertion(assertion, response_data)
                result.assertions.append(assertion_result.model_dump())

                if not assertion_result.success:
                    all_success = False
            except Exception as e:
                log.error(f'执行断言失败: {e}')
                all_success = False

        return all_success

    @staticmethod
    async def _execute_sql_queries(
        sql_configs: List[Dict[str, Any]],
        result: StepExecutionResult,
        variables: Dict[str, Any],
    ) -> bool:
        """执行SQL查询"""
        all_success = True

        for sql_dict in sql_configs:
            try:
                sql_query = SQLQuery(**sql_dict)
                sql_result = await SQLExecutor.execute_query(sql_query)
                result.sql_results.append(sql_result.model_dump())

                if not sql_result.success:
                    all_success = False

                if sql_result.extracted_variables:
                    variables.update(sql_result.extracted_variables)
                    result.extracted_variables.update(sql_result.extracted_variables)
            except Exception as e:
                log.error(f'执行SQL查询失败: {e}')
                all_success = False

        return all_success

    @staticmethod
    def _extract_variables(
        extract_config: Dict[str, Any],
        json_data: Dict[str, Any],
        result: StepExecutionResult,
        variables: Dict[str, Any],
    ):
        """提取变量"""
        for var_name, json_path in extract_config.items():
            try:
                jsonpath_expr = parse(str(json_path))
                matches = [match.value for match in jsonpath_expr.find(json_data)]

                if matches:
                    value = matches[0] if len(matches) == 1 else matches
                    variables[var_name] = value
                    result.extracted_variables[var_name] = value
            except Exception as e:
                log.error(f'提取变量 {var_name} 失败: {e}')


class SqlTaskSubmitResponse(BaseModel):
    """SQL异步任务提交响应"""

    task_id: str
    celery_task_id: Optional[str] = None
    status: str
    name: str


class SqlTaskStatusResponse(BaseModel):
    """SQL异步任务状态响应"""

    task_id: str
    celery_task_id: Optional[str] = None
    status: str
    name: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
