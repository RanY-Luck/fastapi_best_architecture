#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
请求相关模型
"""
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime
from jsonpath_ng import parse
from backend.plugin.api_testing.utils.http_client import send_request, RequestOptions, RequestResult
from backend.plugin.api_testing.utils.assertion import AssertionEngine, Assertion
from backend.plugin.api_testing.utils.sql_executor import SQLExecutor, SQLQuery
from backend.plugin.api_testing.model.models import ApiTestStep
from backend.common.log import log

class ApiRequestSchema(BaseModel):
    """API请求模型"""
    url: str = Field(..., description="请求URL")
    method: str = Field(..., description="请求方法", examples=["GET", "POST", "PUT", "DELETE"])
    headers: Optional[Dict[str, str]] = Field(None, description="请求头")
    params: Optional[Dict[str, Any]] = Field(None, description="查询参数")
    data: Optional[Dict[str, Any]] = Field(None, description="表单数据")
    json_data: Optional[Dict[str, Any]] = Field(None, description="JSON数据")
    files: Optional[Dict[str, str]] = Field(None, description="上传文件，值为文件路径")
    auth: Optional[List[str]] = Field(None, description="认证信息[用户名, 密码]")
    options: Optional[RequestOptions] = Field(None, description="请求选项")


class ApiResponseSchema(BaseModel):
    """API响应模型"""
    url: str = Field(..., description="请求URL")
    method: str = Field(..., description="请求方法")
    status_code: int = Field(..., description="状态码")
    elapsed_time: float = Field(..., description="请求耗时(毫秒)")
    headers: Dict[str, str] = Field(..., description="响应头")
    cookies: Dict[str, str] = Field(..., description="响应cookies")
    content: str = Field(..., description="原始响应内容")
    text: str = Field(..., description="文本形式的响应")
    json_data: Optional[Dict[str, Any]] = Field(None, description="JSON形式的响应")
    error: Optional[str] = Field(None, description="错误信息")


class TestCaseRequest(BaseModel):
    """测试用例创建请求"""
    name: str = Field(..., description="用例名称")
    project_id: int = Field(..., description="所属项目ID")
    description: Optional[str] = Field(None, description="用例描述")
    pre_script: Optional[str] = Field(None, description="前置脚本")
    post_script: Optional[str] = Field(None, description="后置脚本")


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
    name: str = Field(..., description="步骤名称")
    test_case_id: int = Field(..., description="所属用例ID")
    url: str = Field(..., description="请求URL")
    method: str = Field(..., description="请求方法")
    headers: Optional[Dict[str, str]] = Field(None, description="请求头")
    params: Optional[Dict[str, Any]] = Field(None, description="查询参数")
    body: Optional[Dict[str, Any]] = Field(None, description="请求体")
    files: Optional[Dict[str, str]] = Field(None, description="上传文件")
    auth: Optional[Dict[str, str]] = Field(None, description="认证信息")
    extract: Optional[Dict[str, str]] = Field(None, description="提取变量")
    validations: Optional[List[Dict[str, Any]]] = Field(None, description="断言列表")
    sql_queries: Optional[List[Dict[str, Any]]] = Field(None, description="SQL查询列表")
    timeout: int = Field(30, ge=1, le=3600, description="超时时间(秒)，范围1-3600")
    retry: int = Field(0, ge=0, le=10, description="重试次数，范围0-10")
    retry_interval: int = Field(1, ge=1, le=300, description="重试间隔(秒)，范围1-300")
    order: int = Field(..., description="步骤顺序")


class TestStepResponse(BaseModel):
    id: int
    name: str
    test_case_id: int
    test_case_name: Optional[str] = None
    url: str
    method: str
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    files: Optional[Dict[str, str]] = None
    auth: Optional[Dict[str, str]] = None
    extract: Optional[Dict[str, str]] = None
    validations: Optional[List[Dict[str, Any]]] = None
    sql_queries: Optional[List[Dict[str, Any]]] = None
    timeout: int
    retry: int
    retry_interval: int
    order: int
    status: int
    created_time: str
    updated_time: str


# API项目相关模型
class ProjectCreateRequest(BaseModel):
    """API项目创建请求"""
    name: str = Field(..., description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")
    base_url: str = Field(..., description="基础URL")
    headers: Optional[Dict[str, str]] = Field(None, description="全局请求头")
    variables: Optional[Dict[str, Any]] = Field(None, description="全局变量")
    status: int = Field(1, description="状态 1启用 0禁用")


class ProjectUpdateRequest(BaseModel):
    """API项目更新请求"""
    name: Optional[str] = Field(None, description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")
    base_url: Optional[str] = Field(None, description="基础URL")
    headers: Optional[Dict[str, str]] = Field(None, description="全局请求头")
    variables: Optional[Dict[str, Any]] = Field(None, description="全局变量")
    status: Optional[int] = Field(None, description="状态 1启用 0禁用")


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


# 测试用例相关模型
class TestCaseCreateRequest(BaseModel):
    """测试用例创建请求"""
    name: str = Field(..., description="用例名称")
    project_id: int = Field(..., description="所属项目ID")
    description: Optional[str] = Field(None, description="用例描述")
    pre_script: Optional[str] = Field(None, description="前置脚本")
    post_script: Optional[str] = Field(None, description="后置脚本")
    status: int = Field(1, description="状态 1启用 0禁用")


class TestCaseUpdateRequest(BaseModel):
    """测试用例更新请求"""
    name: Optional[str] = Field(None, description="用例名称")
    description: Optional[str] = Field(None, description="用例描述")
    pre_script: Optional[str] = Field(None, description="前置脚本")
    post_script: Optional[str] = Field(None, description="后置脚本")
    status: Optional[int] = Field(None, description="状态 1启用 0禁用")


class TestSuiteCreateRequest(BaseModel):
    """测试集合创建请求"""
    name: str = Field(..., description="集合名称")
    project_id: int = Field(..., description="所属项目ID")
    description: Optional[str] = Field(None, description="集合描述")
    case_ids: List[int] = Field(default_factory=list, description="集合包含的测试用例ID列表")
    status: int = Field(1, description="状态 1启用 0禁用")


class TestSuiteUpdateRequest(BaseModel):
    """测试集合更新请求"""
    name: Optional[str] = Field(None, description="集合名称")
    description: Optional[str] = Field(None, description="集合描述")
    case_ids: Optional[List[int]] = Field(None, description="集合包含的测试用例ID列表")
    status: Optional[int] = Field(None, description="状态 1启用 0禁用")


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


# 测试步骤相关模型
class TestStepCreateRequest(BaseModel):
    """测试步骤创建请求"""
    name: str = Field(..., description="步骤名称")
    test_case_id: int = Field(..., description="所属用例ID")
    url: str = Field(..., description="请求URL")
    method: str = Field(..., description="请求方法")
    headers: Optional[Dict[str, str]] = Field(None, description="请求头")
    params: Optional[Dict[str, Any]] = Field(None, description="查询参数")
    body: Optional[Dict[str, Any]] = Field(None, description="请求体")
    files: Optional[Dict[str, str]] = Field(None, description="上传文件")
    auth: Optional[Dict[str, str]] = Field(None, description="认证信息")
    extract: Optional[Dict[str, str]] = Field(None, description="提取变量")
    validations: Optional[List[Dict[str, Any]]] = Field(None, description="断言列表")
    sql_queries: Optional[List[Dict[str, Any]]] = Field(None, description="SQL查询列表")
    timeout: int = Field(30, ge=1, le=3600, description="超时时间(秒)，范围1-3600")
    retry: int = Field(0, ge=0, le=10, description="重试次数，范围0-10")
    retry_interval: int = Field(1, ge=1, le=300, description="重试间隔(秒)，范围1-300")
    order: int = Field(..., description="步骤顺序")
    status: int = Field(1, description="状态 1启用 0禁用")


class TestStepUpdateRequest(BaseModel):
    """测试步骤更新请求"""
    name: Optional[str] = Field(None, description="步骤名称")
    url: Optional[str] = Field(None, description="请求URL")
    test_case_id: int = Field(..., description="所属用例ID")
    method: Optional[str] = Field(None, description="请求方法")
    headers: Optional[Dict[str, str]] = Field(None, description="请求头")
    params: Optional[Dict[str, Any]] = Field(None, description="查询参数")
    body: Optional[Dict[str, Any]] = Field(None, description="请求体")
    files: Optional[Dict[str, str]] = Field(None, description="上传文件")
    auth: Optional[Dict[str, str]] = Field(None, description="认证信息")
    extract: Optional[Dict[str, str]] = Field(None, description="提取变量")
    validations: Optional[List[Dict[str, Any]]] = Field(None, description="断言列表")
    sql_queries: Optional[List[Dict[str, Any]]] = Field(None, description="SQL查询列表")
    timeout: Optional[int] = Field(None, ge=1, le=3600, description="超时时间(秒)，范围1-3600")
    retry: Optional[int] = Field(None, ge=0, le=10, description="重试次数，范围0-10")
    retry_interval: Optional[int] = Field(None, ge=1, le=300, description="重试间隔(秒)，范围1-300")
    order: Optional[int] = Field(None, description="步骤顺序")
    status: Optional[int] = Field(None, description="状态 1启用 0禁用")


# 测试报告相关模型
class TestReportCreateRequest(BaseModel):
    """测试报告创建请求"""
    test_case_id: int = Field(..., description="所属用例ID")
    name: str = Field(..., description="报告名称")
    success: bool = Field(..., description="是否成功")
    total_steps: int = Field(..., description="总步骤数")
    success_steps: int = Field(..., description="成功步骤数")
    fail_steps: int = Field(..., description="失败步骤数")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    duration: int = Field(..., description="执行时长(毫秒)")
    details: Dict[str, Any] = Field(..., description="报告详情")


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
    environment_id: Optional[int] = Field(None, description="环境ID")
    max_concurrency: int = Field(5, ge=1, le=20, description="最大并发数，范围1-20")


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


# 步骤排序请求
class StepReorderRequest(BaseModel):
    """步骤重新排序请求"""
    step_orders: List[Dict[str, int]] = Field(..., description="步骤排序列表，包含step_id和order字段")


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
            "success": self.success,
            "error": self.error,
            "request_data": self.request_data,
            "response_data": self.response_data,
            "assertions": self.assertions,
            "sql_results": self.sql_results,
            "extracted_variables": self.extracted_variables,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration
        }


class RequestEngine:
    """请求执行引擎"""

    @staticmethod
    async def execute_step(
            step: ApiTestStep,
            base_url: str,
            global_headers: Optional[Dict[str, str]] = None,
            variables: Optional[Dict[str, Any]] = None
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
            # 1. 构建完整URL
            url = RequestEngine._build_url(step.url, base_url)

            # 2. 合并请求头
            headers = RequestEngine._merge_headers(global_headers, step.headers)

            # 3. 替换变量（如果需要支持变量模板）
            # url, headers, params, body = await RequestEngine._process_variables(
            #     url, headers, step.params, step.body, variables
            # )

            # 4. 准备请求选项
            request_options = RequestOptions(
                timeout=step.timeout,
                retry_count=step.retry,
                retry_interval=step.retry_interval
            )

            # 5. 发送HTTP请求
            response = await send_request(
                method=step.method,
                url=url,
                params=step.params,
                headers=headers,
                json_data=step.body,
                options=request_options
            )

            # 6. 构建请求数据
            result.request_data = {
                "url": url,
                "method": step.method,
                "headers": headers,
                "params": step.params or {},
                "json_data": step.body
            }

            # 7. 构建响应数据
            result.response_data = {
                "status_code": response.status_code,
                "headers": response.headers,
                "json": response.json_data,
                "text": response.text,
                "elapsed_time": response.elapsed_time
            }

            # 8. 检查响应错误
            if response.error:
                result.success = False
                result.error = response.error
                return result

            # 9. 执行断言
            if step.validate:
                assertions_success = await RequestEngine._execute_assertions(
                    step.validate, result.response_data, result
                )
                if not assertions_success:
                    result.success = False

            # 10. 执行SQL查询
            if step.sql_queries:
                sql_success = await RequestEngine._execute_sql_queries(
                    step.sql_queries, result, variables
                )
                if not sql_success:
                    result.success = False

            # 11. 提取变量
            if step.extract and response.json_data:
                RequestEngine._extract_variables(
                    step.extract, response.json_data, result, variables
                )

        except Exception as e:
            result.success = False
            result.error = str(e)
            log.error(f"执行测试步骤失败: {e}")

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
            return f"{base_url}{url}"
        else:
            return f"{base_url}/{url}"

    @staticmethod
    def _merge_headers(
            global_headers: Optional[Dict[str, str]],
            step_headers: Optional[Dict[str, str]]
    ) -> Dict[str, str]:
        """合并请求头"""
        headers = {}
        if global_headers:
            headers.update(global_headers)
        if step_headers:
            headers.update(step_headers)
        return headers

    @staticmethod
    async def _execute_assertions(
            assertions_config: List[Dict[str, Any]],
            response_data: Dict[str, Any],
            result: StepExecutionResult
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
                log.error(f"执行断言失败: {e}")
                all_success = False

        return all_success

    @staticmethod
    async def _execute_sql_queries(
            sql_configs: List[Dict[str, Any]],
            result: StepExecutionResult,
            variables: Dict[str, Any]
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

                # 提取SQL变量
                if sql_result.extracted_variables:
                    variables.update(sql_result.extracted_variables)
                    result.extracted_variables.update(sql_result.extracted_variables)
            except Exception as e:
                log.error(f"执行SQL查询失败: {e}")
                all_success = False

        return all_success

    @staticmethod
    def _extract_variables(
            extract_config: Dict[str, str],
            json_data: Dict[str, Any],
            result: StepExecutionResult,
            variables: Dict[str, Any]
    ):
        """提取变量"""
        for var_name, json_path in extract_config.items():
            try:
                jsonpath_expr = parse(json_path)
                matches = [match.value for match in jsonpath_expr.find(json_data)]

                if matches:
                    value = matches[0] if len(matches) == 1 else matches
                    variables[var_name] = value
                    result.extracted_variables[var_name] = value
            except Exception as e:
                log.error(f"提取变量 {var_name} 失败: {e}")
