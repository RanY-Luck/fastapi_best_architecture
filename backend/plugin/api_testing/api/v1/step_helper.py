#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time     : 2025/12/13 11:14
# @Author   : 冉勇
# @File     : step_helper.py
# @Software : PyCharm
# @Desc     :
"""
测试步骤增强API接口
提供断言规则、SQL查询模板、变量提取等辅助功能
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Query, Body
from pydantic import BaseModel
from backend.common.response.response_schema import response_base, ResponseModel, ResponseSchemaModel

router = APIRouter()


# ==================== 数据模型 ====================

class AssertionTemplate(BaseModel):
    """断言规则模板"""
    id: str
    name: str
    description: str
    type: str  # equals, contains, greater_than等
    source: str  # json, status_code, headers等
    example_path: Optional[str] = None
    example_expected: Optional[Any] = None
    category: str  # 响应验证、性能验证、数据验证等


class SQLTemplate(BaseModel):
    """SQL查询模板"""
    id: str
    name: str
    description: str
    database_type: str  # mysql, postgresql
    query_template: str
    parameters: List[Dict[str, str]]  # 参数说明
    extract_example: Dict[str, str]  # 变量提取示例
    category: str  # 数据查询、数据验证、数据准备等


class VariableExtractTemplate(BaseModel):
    """变量提取模板"""
    id: str
    name: str
    description: str
    source_type: str  # response_json, response_header, sql_result
    path_example: str  # JSONPath或其他路径表达式示例
    usage_scenario: str  # 使用场景说明


class ValidationRule(BaseModel):
    """验证规则"""
    rule_type: str
    description: str
    parameters: List[Dict[str, Any]]
    example: Dict[str, Any]


# ==================== 断言规则接口 ====================

@router.get("/assertion-templates", response_model=ResponseModel, summary="获取断言规则模板列表")
async def get_assertion_templates(
        category: Optional[str] = Query(None, description="分类筛选"),
        source: Optional[str] = Query(None, description="来源筛选")
) -> ResponseModel | ResponseSchemaModel:
    """
    获取所有可用的断言规则模板

    包含：
    - 响应状态码验证
    - JSON数据验证
    - 响应头验证
    - 性能验证
    - 数据类型验证
    """

    templates = [
        # 响应状态码验证
        {
            "id": "assert_status_200",
            "name": "验证状态码为200",
            "description": "验证HTTP响应状态码是否为200",
            "type": "equals",
            "source": "status_code",
            "example_path": None,
            "example_expected": 200,
            "category": "响应验证"
        },
        {
            "id": "assert_status_success",
            "name": "验证状态码为成功范围",
            "description": "验证HTTP响应状态码在200-299之间",
            "type": "greater_than_or_equals",
            "source": "status_code",
            "example_path": None,
            "example_expected": 200,
            "category": "响应验证"
        },

        # JSON数据验证
        {
            "id": "assert_json_equals",
            "name": "验证JSON字段值相等",
            "description": "验证响应JSON中指定字段的值等于预期值",
            "type": "equals",
            "source": "json",
            "example_path": "$.data.id",
            "example_expected": 123,
            "category": "数据验证"
        },
        {
            "id": "assert_json_contains",
            "name": "验证JSON字段包含值",
            "description": "验证响应JSON中指定字段包含预期的子字符串或元素",
            "type": "contains",
            "source": "json",
            "example_path": "$.data.name",
            "example_expected": "test",
            "category": "数据验证"
        },
        {
            "id": "assert_json_exists",
            "name": "验证JSON字段存在",
            "description": "验证响应JSON中指定字段存在",
            "type": "exists",
            "source": "json",
            "example_path": "$.data.token",
            "example_expected": None,
            "category": "数据验证"
        },
        {
            "id": "assert_json_not_null",
            "name": "验证JSON字段不为空",
            "description": "验证响应JSON中指定字段不为null",
            "type": "is_not_null",
            "source": "json",
            "example_path": "$.data.user_id",
            "example_expected": None,
            "category": "数据验证"
        },
        {
            "id": "assert_json_type",
            "name": "验证JSON字段类型",
            "description": "验证响应JSON中指定字段的数据类型",
            "type": "is_true",
            "source": "json",
            "example_path": "$.data.count",
            "example_expected": "integer",
            "category": "数据验证"
        },
        {
            "id": "assert_json_array_length",
            "name": "验证数组长度",
            "description": "验证响应JSON中数组的长度",
            "type": "length_equals",
            "source": "json",
            "example_path": "$.data.items",
            "example_expected": 10,
            "category": "数据验证"
        },

        # 响应头验证
        {
            "id": "assert_header_exists",
            "name": "验证响应头存在",
            "description": "验证指定的响应头字段存在",
            "type": "exists",
            "source": "headers",
            "example_path": "Content-Type",
            "example_expected": None,
            "category": "响应验证"
        },
        {
            "id": "assert_header_contains",
            "name": "验证响应头包含值",
            "description": "验证响应头字段包含指定值",
            "type": "contains",
            "source": "headers",
            "example_path": "Content-Type",
            "example_expected": "application/json",
            "category": "响应验证"
        },

        # 性能验证
        {
            "id": "assert_response_time",
            "name": "验证响应时间",
            "description": "验证响应时间小于指定值(毫秒)",
            "type": "less_than",
            "source": "elapsed_time",
            "example_path": None,
            "example_expected": 1000,
            "category": "性能验证"
        },

        # 正则表达式验证
        {
            "id": "assert_regex_match",
            "name": "正则表达式匹配",
            "description": "验证字段值匹配指定的正则表达式",
            "type": "match_regex",
            "source": "json",
            "example_path": "$.data.email",
            "example_expected": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
            "category": "数据验证"
        },

        # 数值范围验证
        {
            "id": "assert_number_range",
            "name": "验证数值在范围内",
            "description": "验证数值字段在指定范围内",
            "type": "greater_than",
            "source": "json",
            "example_path": "$.data.age",
            "example_expected": 0,
            "category": "数据验证"
        }
    ]

    # 应用筛选
    filtered_templates = templates
    if category:
        filtered_templates = [t for t in filtered_templates if t["category"] == category]
    if source:
        filtered_templates = [t for t in filtered_templates if t["source"] == source]

    return response_base.success(
        data={
            "templates": filtered_templates,
            "total": len(filtered_templates),
            "categories": list(set(t["category"] for t in templates)),
            "sources": list(set(t["source"] for t in templates))
        }
    )


@router.get("/assertion-types", response_model=ResponseModel, summary="获取断言类型列表")
async def get_assertion_types() -> ResponseModel | ResponseSchemaModel:
    """
    获取所有支持的断言类型及其说明
    """

    assertion_types = [
        {
            "type": "equals",
            "name": "等于",
            "description": "验证实际值等于预期值",
            "requires_expected": True,
            "supports_sources": ["status_code", "json", "headers", "cookies"]
        },
        {
            "type": "not_equals",
            "name": "不等于",
            "description": "验证实际值不等于预期值",
            "requires_expected": True,
            "supports_sources": ["status_code", "json", "headers", "cookies"]
        },
        {
            "type": "contains",
            "name": "包含",
            "description": "验证实际值包含预期值",
            "requires_expected": True,
            "supports_sources": ["json", "headers", "body"]
        },
        {
            "type": "not_contains",
            "name": "不包含",
            "description": "验证实际值不包含预期值",
            "requires_expected": True,
            "supports_sources": ["json", "headers", "body"]
        },
        {
            "type": "starts_with",
            "name": "以...开头",
            "description": "验证字符串以指定值开头",
            "requires_expected": True,
            "supports_sources": ["json", "headers", "body"]
        },
        {
            "type": "ends_with",
            "name": "以...结尾",
            "description": "验证字符串以指定值结尾",
            "requires_expected": True,
            "supports_sources": ["json", "headers", "body"]
        },
        {
            "type": "match_regex",
            "name": "匹配正则表达式",
            "description": "验证值匹配正则表达式",
            "requires_expected": True,
            "supports_sources": ["json", "headers", "body"]
        },
        {
            "type": "less_than",
            "name": "小于",
            "description": "验证数值小于预期值",
            "requires_expected": True,
            "supports_sources": ["status_code", "json", "elapsed_time"]
        },
        {
            "type": "less_than_or_equals",
            "name": "小于或等于",
            "description": "验证数值小于或等于预期值",
            "requires_expected": True,
            "supports_sources": ["status_code", "json", "elapsed_time"]
        },
        {
            "type": "greater_than",
            "name": "大于",
            "description": "验证数值大于预期值",
            "requires_expected": True,
            "supports_sources": ["status_code", "json", "elapsed_time"]
        },
        {
            "type": "greater_than_or_equals",
            "name": "大于或等于",
            "description": "验证数值大于或等于预期值",
            "requires_expected": True,
            "supports_sources": ["status_code", "json", "elapsed_time"]
        },
        {
            "type": "exists",
            "name": "存在",
            "description": "验证字段或值存在",
            "requires_expected": False,
            "supports_sources": ["json", "headers", "cookies"]
        },
        {
            "type": "not_exists",
            "name": "不存在",
            "description": "验证字段或值不存在",
            "requires_expected": False,
            "supports_sources": ["json", "headers", "cookies"]
        },
        {
            "type": "is_empty",
            "name": "为空",
            "description": "验证值为空",
            "requires_expected": False,
            "supports_sources": ["json", "body"]
        },
        {
            "type": "is_not_empty",
            "name": "不为空",
            "description": "验证值不为空",
            "requires_expected": False,
            "supports_sources": ["json", "body"]
        },
        {
            "type": "is_null",
            "name": "为null",
            "description": "验证值为null",
            "requires_expected": False,
            "supports_sources": ["json"]
        },
        {
            "type": "is_not_null",
            "name": "不为null",
            "description": "验证值不为null",
            "requires_expected": False,
            "supports_sources": ["json"]
        },
        {
            "type": "is_true",
            "name": "为true",
            "description": "验证布尔值为true",
            "requires_expected": False,
            "supports_sources": ["json"]
        },
        {
            "type": "is_false",
            "name": "为false",
            "description": "验证布尔值为false",
            "requires_expected": False,
            "supports_sources": ["json"]
        },
        {
            "type": "length_equals",
            "name": "长度等于",
            "description": "验证数组或字符串长度等于预期值",
            "requires_expected": True,
            "supports_sources": ["json", "body"]
        },
        {
            "type": "length_greater_than",
            "name": "长度大于",
            "description": "验证数组或字符串长度大于预期值",
            "requires_expected": True,
            "supports_sources": ["json", "body"]
        },
        {
            "type": "length_less_than",
            "name": "长度小于",
            "description": "验证数组或字符串长度小于预期值",
            "requires_expected": True,
            "supports_sources": ["json", "body"]
        }
    ]

    return response_base.success(
        data={
            "types": assertion_types,
            "total": len(assertion_types)
        }
    )


# ==================== SQL查询模板接口 ====================

@router.get("/sql-templates", response_model=ResponseModel, summary="获取SQL查询模板列表")
async def get_sql_templates(
        database_type: Optional[str] = Query(None, description="数据库类型"),
        category: Optional[str] = Query(None, description="分类筛选")
) -> ResponseModel | ResponseSchemaModel:
    """
    获取SQL查询模板列表

    包含常用的SQL查询模板，帮助用户快速构建测试SQL
    """

    templates = [
        # MySQL模板
        {
            "id": "mysql_select_by_id",
            "name": "根据ID查询记录",
            "description": "查询指定ID的记录",
            "database_type": "mysql",
            "query_template": "SELECT * FROM {{table_name}} WHERE id = {{id}}",
            "parameters": [
                {"name": "table_name", "description": "表名"},
                {"name": "id", "description": "记录ID"}
            ],
            "extract_example": {
                "user_id": "0.id",
                "username": "0.username"
            },
            "category": "数据查询"
        },
        {
            "id": "mysql_count_records",
            "name": "统计记录数",
            "description": "统计表中符合条件的记录数",
            "database_type": "mysql",
            "query_template": "SELECT COUNT(*) as count FROM {{table_name}} WHERE {{condition}}",
            "parameters": [
                {"name": "table_name", "description": "表名"},
                {"name": "condition", "description": "查询条件"}
            ],
            "extract_example": {
                "total_count": "0.count"
            },
            "category": "数据验证"
        },
        {
            "id": "mysql_insert_record",
            "name": "插入测试数据",
            "description": "插入一条测试数据",
            "database_type": "mysql",
            "query_template": "INSERT INTO {{table_name}} ({{columns}}) VALUES ({{values}})",
            "parameters": [
                {"name": "table_name", "description": "表名"},
                {"name": "columns", "description": "列名，逗号分隔"},
                {"name": "values", "description": "值，逗号分隔"}
            ],
            "extract_example": {},
            "category": "数据准备"
        },
        {
            "id": "mysql_update_record",
            "name": "更新测试数据",
            "description": "更新指定ID的记录",
            "database_type": "mysql",
            "query_template": "UPDATE {{table_name}} SET {{set_clause}} WHERE id = {{id}}",
            "parameters": [
                {"name": "table_name", "description": "表名"},
                {"name": "set_clause", "description": "SET子句"},
                {"name": "id", "description": "记录ID"}
            ],
            "extract_example": {},
            "category": "数据准备"
        },
        {
            "id": "mysql_delete_record",
            "name": "删除测试数据",
            "description": "删除指定ID的记录",
            "database_type": "mysql",
            "query_template": "DELETE FROM {{table_name}} WHERE id = {{id}}",
            "parameters": [
                {"name": "table_name", "description": "表名"},
                {"name": "id", "description": "记录ID"}
            ],
            "extract_example": {},
            "category": "数据清理"
        },
        {
            "id": "mysql_check_exists",
            "name": "检查记录是否存在",
            "description": "检查符合条件的记录是否存在",
            "database_type": "mysql",
            "query_template": "SELECT EXISTS(SELECT 1 FROM {{table_name}} WHERE {{condition}}) as exists_flag",
            "parameters": [
                {"name": "table_name", "description": "表名"},
                {"name": "condition", "description": "查询条件"}
            ],
            "extract_example": {
                "exists": "0.exists_flag"
            },
            "category": "数据验证"
        },

        # PostgreSQL模板
        {
            "id": "pg_select_by_id",
            "name": "根据ID查询记录",
            "description": "查询指定ID的记录(PostgreSQL)",
            "database_type": "postgresql",
            "query_template": "SELECT * FROM {{table_name}} WHERE id = {{id}}",
            "parameters": [
                {"name": "table_name", "description": "表名"},
                {"name": "id", "description": "记录ID"}
            ],
            "extract_example": {
                "user_id": "0.id",
                "username": "0.username"
            },
            "category": "数据查询"
        },
        {
            "id": "pg_select_with_json",
            "name": "查询JSON字段",
            "description": "查询包含JSON字段的记录(PostgreSQL)",
            "database_type": "postgresql",
            "query_template": "SELECT id, {{json_column}}->>'{{json_key}}' as value FROM {{table_name}} WHERE id = {{id}}",
            "parameters": [
                {"name": "table_name", "description": "表名"},
                {"name": "json_column", "description": "JSON列名"},
                {"name": "json_key", "description": "JSON键"},
                {"name": "id", "description": "记录ID"}
            ],
            "extract_example": {
                "json_value": "0.value"
            },
            "category": "数据查询"
        }
    ]

    # 应用筛选
    filtered_templates = templates
    if database_type:
        filtered_templates = [t for t in filtered_templates if t["database_type"] == database_type]
    if category:
        filtered_templates = [t for t in filtered_templates if t["category"] == category]

    return response_base.success(
        data={
            "templates": filtered_templates,
            "total": len(filtered_templates),
            "database_types": list(set(t["database_type"] for t in templates)),
            "categories": list(set(t["category"] for t in templates))
        }
    )


@router.post("/sql-templates/render", response_model=ResponseModel, summary="渲染SQL模板")
async def render_sql_template(
        template_id: str = Body(..., description="模板ID"),
        parameters: Dict[str, str] = Body(..., description="参数值")
) -> ResponseModel | ResponseSchemaModel:
    """
    根据提供的参数渲染SQL模板
    """
    # 这里应该从数据库或缓存中获取模板，这里简化处理
    # 实际应用中应该调用get_sql_templates获取对应模板

    # 示例：简单的字符串替换
    rendered_query = "SELECT * FROM users WHERE id = 1"  # 实际应该根据template_id和parameters渲染

    return response_base.success(
        data={
            "template_id": template_id,
            "rendered_query": rendered_query,
            "parameters": parameters
        }
    )


# ==================== 变量提取模板接口 ====================

@router.get("/extract-templates", response_model=ResponseModel, summary="获取变量提取模板列表")
async def get_extract_templates(
        source_type: Optional[str] = Query(None, description="来源类型筛选")
) -> ResponseModel | ResponseSchemaModel:
    """
    获取变量提取模板列表

    包含各种常见的变量提取场景和示例
    """

    templates = [
        # 响应JSON提取
        {
            "id": "extract_json_simple",
            "name": "提取JSON简单字段",
            "description": "从响应JSON中提取简单字段值",
            "source_type": "response_json",
            "path_example": "$.data.token",
            "usage_scenario": "提取登录后返回的token"
        },
        {
            "id": "extract_json_nested",
            "name": "提取JSON嵌套字段",
            "description": "从响应JSON中提取嵌套字段值",
            "source_type": "response_json",
            "path_example": "$.data.user.id",
            "usage_scenario": "提取嵌套对象中的用户ID"
        },
        {
            "id": "extract_json_array",
            "name": "提取JSON数组元素",
            "description": "从响应JSON数组中提取元素",
            "source_type": "response_json",
            "path_example": "$.data.items[0].id",
            "usage_scenario": "提取数组第一个元素的ID"
        },
        {
            "id": "extract_json_array_all",
            "name": "提取JSON数组所有元素",
            "description": "提取JSON数组中所有元素的某个字段",
            "source_type": "response_json",
            "path_example": "$.data.items[*].id",
            "usage_scenario": "提取所有商品的ID列表"
        },
        {
            "id": "extract_json_filter",
            "name": "条件过滤提取",
            "description": "根据条件过滤后提取值",
            "source_type": "response_json",
            "path_example": "$.data.users[?(@.status=='active')].id",
            "usage_scenario": "提取所有激活用户的ID"
        },

        # 响应头提取
        {
            "id": "extract_header_auth",
            "name": "提取认证头",
            "description": "从响应头中提取认证信息",
            "source_type": "response_header",
            "path_example": "Authorization",
            "usage_scenario": "提取服务器返回的认证令牌"
        },
        {
            "id": "extract_header_location",
            "name": "提取Location头",
            "description": "从响应头中提取Location",
            "source_type": "response_header",
            "path_example": "Location",
            "usage_scenario": "提取重定向地址"
        },

        # SQL结果提取
        {
            "id": "extract_sql_single",
            "name": "提取SQL单行结果",
            "description": "从SQL查询结果中提取单行数据",
            "source_type": "sql_result",
            "path_example": "0.id",
            "usage_scenario": "提取第一行记录的ID字段"
        },
        {
            "id": "extract_sql_multiple",
            "name": "提取SQL多行结果",
            "description": "从SQL查询结果中提取多行数据",
            "source_type": "sql_result",
            "path_example": "*.id",
            "usage_scenario": "提取所有行的ID字段"
        }
    ]

    # 应用筛选
    filtered_templates = templates
    if source_type:
        filtered_templates = [t for t in filtered_templates if t["source_type"] == source_type]

    return response_base.success(
        data={
            "templates": filtered_templates,
            "total": len(filtered_templates),
            "source_types": list(set(t["source_type"] for t in templates))
        }
    )


@router.get("/jsonpath-examples", response_model=ResponseModel, summary="获取JSONPath表达式示例")
async def get_jsonpath_examples() -> ResponseModel | ResponseSchemaModel:
    """
    获取JSONPath表达式使用示例
    """

    examples = [
        {
            "expression": "$",
            "description": "根节点",
            "example_json": '{"name": "test"}',
            "result": '{"name": "test"}'
        },
        {
            "expression": "$.name",
            "description": "获取name字段",
            "example_json": '{"name": "test", "age": 20}',
            "result": '"test"'
        },
        {
            "expression": "$.user.name",
            "description": "获取嵌套对象的name字段",
            "example_json": '{"user": {"name": "test", "age": 20}}',
            "result": '"test"'
        },
        {
            "expression": "$.items[0]",
            "description": "获取数组第一个元素",
            "example_json": '{"items": [{"id": 1}, {"id": 2}]}',
            "result": '{"id": 1}'
        },
        {
            "expression": "$.items[*].id",
            "description": "获取数组所有元素的id字段",
            "example_json": '{"items": [{"id": 1}, {"id": 2}]}',
            "result": '[1, 2]'
        },
        {
            "expression": "$.items[?(@.price > 100)]",
            "description": "过滤价格大于100的商品",
            "example_json": '{"items": [{"price": 50}, {"price": 150}]}',
            "result": '[{"price": 150}]'
        },
        {
            "expression": "$.items[0:2]",
            "description": "获取数组切片(前两个元素)",
            "example_json": '{"items": [1, 2, 3, 4, 5]}',
            "result": '[1, 2]'
        },
        {
            "expression": "$..name",
            "description": "递归获取所有name字段",
            "example_json": '{"user": {"name": "test"}, "admin": {"name": "admin"}}',
            "result": '["test", "admin"]'
        }
    ]

    return response_base.success(
        data={
            "examples": examples,
            "total": len(examples),
            "reference": "JSONPath语法参考: https://goessner.net/articles/JsonPath/"
        }
    )


# ==================== 验证规则接口 ====================

@router.get("/validation-rules", response_model=ResponseModel, summary="获取验证规则列表")
async def get_validation_rules() -> ResponseModel | ResponseSchemaModel:
    """
    获取完整的验证规则说明

    包括断言规则、SQL验证等的完整配置说明
    """

    rules = [
        {
            "rule_type": "assertion",
            "description": "响应断言验证",
            "parameters": [
                {
                    "name": "source",
                    "type": "string",
                    "required": True,
                    "description": "数据来源",
                    "enum": ["status_code", "json", "headers", "cookies", "body"]
                },
                {
                    "name": "type",
                    "type": "string",
                    "required": True,
                    "description": "断言类型",
                    "enum": ["equals", "contains", "greater_than", "exists", "is_null", "length_equals"]
                },
                {
                    "name": "path",
                    "type": "string",
                    "required": False,
                    "description": "JSONPath表达式(当source为json时必填)"
                },
                {
                    "name": "expected",
                    "type": "any",
                    "required": False,
                    "description": "预期值(某些断言类型需要)"
                },
                {
                    "name": "message",
                    "type": "string",
                    "required": False,
                    "description": "自定义断言消息"
                }
            ],
            "example": {
                "source": "json",
                "type": "equals",
                "path": "$.data.status",
                "expected": "success",
                "message": "验证接口返回状态为成功"
            }
        },
        {
            "rule_type": "sql_validation",
            "description": "SQL数据验证",
            "parameters": [
                {
                    "name": "name",
                    "type": "string",
                    "required": True,
                    "description": "SQL查询名称"
                },
                {
                    "name": "query",
                    "type": "string",
                    "required": True,
                    "description": "SQL查询语句"
                },
                {
                    "name": "extract",
                    "type": "object",
                    "required": False,
                    "description": "变量提取配置"
                },
                {
                    "name": "use_default_db",
                    "type": "boolean",
                    "required": False,
                    "description": "是否使用默认数据库配置"
                }
            ],
            "example": {
                "name": "查询用户信息",
                "query": "SELECT id, username, status FROM users WHERE id = 1",
                "extract": {
                    "user_id": "0.id",
                    "username": "0.username",
                    "status": "0.status"
                },
                "use_default_db": True
            }
        },
        {
            "rule_type": "variable_extract",
            "description": "变量提取规则",
            "parameters": [
                {
                    "name": "variable_name",
                    "type": "string",
                    "required": True,
                    "description": "变量名称"
                },
                {
                    "name": "extract_path",
                    "type": "string",
                    "required": True,
                    "description": "提取路径表达式"
                }
            ],
            "example": {
                "token": "$.data.token",
                "user_id": "$.data.user.id",
                "order_ids": "$.data.orders[*].id"
            }
        }
    ]

    return response_base.success(
        data={
            "rules": rules,
            "total": len(rules)
        }
    )


# ==================== 测试步骤快速配置接口 ====================

@router.post("/quick-config/assertion", response_model=ResponseModel, summary="快速生成断言配置")
async def quick_config_assertion(
        template_id: str = Body(..., description="断言模板ID"),
        path: Optional[str] = Body(None, description="自定义路径"),
        expected: Optional[Any] = Body(None, description="自定义预期值"),
        message: Optional[str] = Body(None, description="自定义消息")
) -> ResponseModel | ResponseSchemaModel:
    """
    根据模板快速生成断言配置
    """

    # 这里应该根据template_id查找对应的模板
    # 简化示例
    config = {
        "source": "json",
        "type": "equals",
        "path": path or "$.data.status",
        "expected": expected if expected is not None else "success",
        "message": message or "验证响应状态"
    }

    return response_base.success(
        data={
            "assertion": config,
            "template_id": template_id
        }
    )


@router.post("/quick-config/sql", response_model=ResponseModel, summary="快速生成SQL配置")
async def quick_config_sql(
        template_id: str = Body(..., description="SQL模板ID"),
        parameters: Dict[str, str] = Body(..., description="模板参数"),
        extract: Optional[Dict[str, str]] = Body(None, description="变量提取配置")
) -> ResponseModel | ResponseSchemaModel:
    """
    根据模板快速生成SQL配置
    """

    # 简化示例
    config = {
        "name": "数据库查询",
        "query": f"SELECT * FROM {parameters.get('table_name', 'users')} WHERE id = {parameters.get('id', '1')}",
        "extract": extract or {"user_id": "0.id"},
        "use_default_db": True
    }

    return response_base.success(
        data={
            "sql_query": config,
            "template_id": template_id
        }
    )


@router.post("/quick-config/extract", response_model=ResponseModel, summary="快速生成变量提取配置")
async def quick_config_extract(
        template_id: str = Body(..., description="提取模板ID"),
        variable_name: str = Body(..., description="变量名称"),
        custom_path: Optional[str] = Body(None, description="自定义路径")
) -> ResponseModel | ResponseSchemaModel:
    """
    根据模板快速生成变量提取配置
    """

    config = {
        variable_name: custom_path or "$.data.value"
    }

    return response_base.success(
        data={
            "extract": config,
            "template_id": template_id
        }
    )


# ==================== 批量配置接口 ====================

@router.post("/batch-config", response_model=ResponseModel, summary="批量生成测试步骤配置")
async def batch_config(
        assertions: Optional[List[Dict[str, Any]]] = Body(None, description="断言配置列表"),
        sql_queries: Optional[List[Dict[str, Any]]] = Body(None, description="SQL查询配置列表"),
        extracts: Optional[Dict[str, str]] = Body(None, description="变量提取配置")
) -> ResponseModel | ResponseSchemaModel:
    """
    批量生成测试步骤的完整配置

    一次性配置多个断言、SQL查询和变量提取
    """

    config = {
        "validate": assertions or [],
        "sql_queries": sql_queries or [],
        "extract": extracts or {}
    }

    return response_base.success(
        data={
            "config": config,
            "summary": {
                "assertions_count": len(config["validate"]),
                "sql_queries_count": len(config["sql_queries"]),
                "extracts_count": len(config["extract"])
            }
        }
    )


# ==================== 配置验证接口 ====================

@router.post("/validate-config", response_model=ResponseModel, summary="验证配置正确性")
async def validate_config(
        config_type: str = Body(..., description="配置类型: assertion/sql/extract"),
        config_data: Dict[str, Any] = Body(..., description="配置数据")
) -> ResponseModel | ResponseSchemaModel:
    """
    验证配置数据的正确性
    """

    errors = []
    warnings = []

    if config_type == "assertion":
        # 验证断言配置
        if "source" not in config_data:
            errors.append("缺少必填字段: source")
        if "type" not in config_data:
            errors.append("缺少必填字段: type")
        if config_data.get("source") == "json" and not config_data.get("path"):
            warnings.append("建议为JSON断言指定path")

    elif config_type == "sql":
        # 验证SQL配置
        if "query" not in config_data:
            errors.append("缺少必填字段: query")
        if not config_data.get("name"):
            warnings.append("建议为SQL查询指定名称")

    elif config_type == "extract":
        # 验证提取配置
        if not config_data:
            errors.append("提取配置不能为空")

    is_valid = len(errors) == 0

    return response_base.success(
        data={
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "config_type": config_type
        }
    )


# ==================== 推荐配置接口 ====================

@router.post("/recommend-config", response_model=ResponseModel, summary="推荐配置方案")
async def recommend_config(
        scenario: str = Body(..., description="测试场景"),
        api_type: Optional[str] = Body(None, description="API类型")
) -> ResponseModel | ResponseSchemaModel:
    """
    根据测试场景推荐配置方案

    场景包括:
    - login: 登录接口
    - crud: 增删改查接口
    - list: 列表查询接口
    - detail: 详情查询接口
    """

    recommendations = {
        "login": {
            "assertions": [
                {
                    "source": "status_code",
                    "type": "equals",
                    "expected": 200,
                    "message": "验证登录请求成功"
                },
                {
                    "source": "json",
                    "type": "exists",
                    "path": "$.data.token",
                    "message": "验证返回token"
                },
                {
                    "source": "json",
                    "type": "is_not_null",
                    "path": "$.data.user.id",
                    "message": "验证返回用户ID"
                }
            ],
            "extract": {
                "token": "$.data.token",
                "user_id": "$.data.user.id"
            },
            "sql_queries": [
                {
                    "name": "验证用户状态",
                    "query": "SELECT status FROM users WHERE id = {{user_id}}",
                    "extract": {
                        "user_status": "0.status"
                    }
                }
            ]
        },
        "crud_create": {
            "assertions": [
                {
                    "source": "status_code",
                    "type": "equals",
                    "expected": 201,
                    "message": "验证创建成功"
                },
                {
                    "source": "json",
                    "type": "exists",
                    "path": "$.data.id",
                    "message": "验证返回新记录ID"
                }
            ],
            "extract": {
                "new_id": "$.data.id"
            },
            "sql_queries": [
                {
                    "name": "验证数据已入库",
                    "query": "SELECT COUNT(*) as count FROM {{table}} WHERE id = {{new_id}}",
                    "extract": {
                        "exists_count": "0.count"
                    }
                }
            ]
        },
        "list": {
            "assertions": [
                {
                    "source": "status_code",
                    "type": "equals",
                    "expected": 200,
                    "message": "验证请求成功"
                },
                {
                    "source": "json",
                    "type": "exists",
                    "path": "$.data.items",
                    "message": "验证返回列表"
                },
                {
                    "source": "json",
                    "type": "length_greater_than",
                    "path": "$.data.items",
                    "expected": 0,
                    "message": "验证列表不为空"
                },
                {
                    "source": "json",
                    "type": "exists",
                    "path": "$.data.total",
                    "message": "验证返回总数"
                }
            ],
            "extract": {
                "total": "$.data.total",
                "first_id": "$.data.items[0].id"
            },
            "sql_queries": []
        },
        "detail": {
            "assertions": [
                {
                    "source": "status_code",
                    "type": "equals",
                    "expected": 200,
                    "message": "验证请求成功"
                },
                {
                    "source": "json",
                    "type": "exists",
                    "path": "$.data.id",
                    "message": "验证返回ID"
                },
                {
                    "source": "json",
                    "type": "is_not_null",
                    "path": "$.data",
                    "message": "验证返回数据不为空"
                }
            ],
            "extract": {
                "record_id": "$.data.id"
            },
            "sql_queries": [
                {
                    "name": "验证数据一致性",
                    "query": "SELECT * FROM {{table}} WHERE id = {{record_id}}",
                    "extract": {
                        "db_data": "0"
                    }
                }
            ]
        }
    }

    recommendation = recommendations.get(
        scenario, {
            "assertions": [],
            "extract": {},
            "sql_queries": []
        }
    )

    return response_base.success(
        data={
            "scenario": scenario,
            "recommendation": recommendation,
            "description": f"针对{scenario}场景的推荐配置"
        }
    )


# ==================== 配置示例接口 ====================

@router.get("/config-examples", response_model=ResponseModel, summary="获取配置示例")
async def get_config_examples(
        example_type: Optional[str] = Query(None, description="示例类型")
) -> ResponseModel | ResponseSchemaModel:
    """
    获取完整的配置示例
    """

    examples = [
        {
            "type": "complete_step",
            "name": "完整测试步骤示例",
            "description": "包含请求、断言、SQL和变量提取的完整配置",
            "config": {
                "name": "用户登录并验证",
                "url": "/api/auth/login",
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": {
                    "username": "test_user",
                    "password": "password123"
                },
                "validate": [
                    {
                        "source": "status_code",
                        "type": "equals",
                        "expected": 200,
                        "message": "验证登录成功"
                    },
                    {
                        "source": "json",
                        "type": "exists",
                        "path": "$.data.token",
                        "message": "验证token存在"
                    },
                    {
                        "source": "json",
                        "type": "match_regex",
                        "path": "$.data.token",
                        "expected": "^[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+$",
                        "message": "验证token格式为JWT"
                    }
                ],
                "extract": {
                    "token": "$.data.token",
                    "user_id": "$.data.user.id",
                    "username": "$.data.user.username"
                },
                "sql_queries": [
                    {
                        "name": "验证用户登录状态",
                        "query": "SELECT last_login_time, login_count FROM users WHERE id = {{user_id}}",
                        "extract": {
                            "last_login": "0.last_login_time",
                            "login_count": "0.login_count"
                        },
                        "use_default_db": True
                    }
                ],
                "timeout": 30,
                "retry": 3,
                "retry_interval": 1,
                "order": 1
            }
        },
        {
            "type": "assertion_chain",
            "name": "断言链示例",
            "description": "多个相关断言的组合",
            "config": {
                "validate": [
                    {
                        "source": "status_code",
                        "type": "equals",
                        "expected": 200,
                        "message": "1. 验证HTTP状态码"
                    },
                    {
                        "source": "json",
                        "type": "equals",
                        "path": "$.code",
                        "expected": 0,
                        "message": "2. 验证业务状态码"
                    },
                    {
                        "source": "json",
                        "type": "is_not_null",
                        "path": "$.data",
                        "message": "3. 验证数据不为空"
                    },
                    {
                        "source": "json",
                        "type": "length_greater_than",
                        "path": "$.data.items",
                        "expected": 0,
                        "message": "4. 验证列表有数据"
                    }
                ]
            }
        },
        {
            "type": "complex_extract",
            "name": "复杂变量提取示例",
            "description": "从响应和SQL中提取多个变量",
            "config": {
                "extract": {
                    "order_id": "$.data.order.id",
                    "order_no": "$.data.order.order_no",
                    "total_amount": "$.data.order.total_amount",
                    "item_ids": "$.data.order.items[*].id",
                    "first_item_name": "$.data.order.items[0].name"
                },
                "sql_queries": [
                    {
                        "name": "获取订单详细信息",
                        "query": "SELECT status, create_time, user_id FROM orders WHERE order_no = '{{order_no}}'",
                        "extract": {
                            "order_status": "0.status",
                            "order_time": "0.create_time",
                            "buyer_id": "0.user_id"
                        }
                    }
                ]
            }
        },
        {
            "type": "data_validation",
            "name": "数据一致性验证示例",
            "description": "验证API返回数据与数据库数据一致",
            "config": {
                "validate": [
                    {
                        "source": "json",
                        "type": "equals",
                        "path": "$.data.user.id",
                        "expected": "{{db_user_id}}",
                        "message": "验证用户ID一致"
                    },
                    {
                        "source": "json",
                        "type": "equals",
                        "path": "$.data.user.username",
                        "expected": "{{db_username}}",
                        "message": "验证用户名一致"
                    }
                ],
                "sql_queries": [
                    {
                        "name": "查询数据库用户信息",
                        "query": "SELECT id, username, email FROM users WHERE id = {{user_id}}",
                        "extract": {
                            "db_user_id": "0.id",
                            "db_username": "0.username",
                            "db_email": "0.email"
                        }
                    }
                ]
            }
        }
    ]

    # 应用筛选
    filtered_examples = examples
    if example_type:
        filtered_examples = [e for e in examples if e["type"] == example_type]

    return response_base.success(
        data={
            "examples": filtered_examples,
            "total": len(filtered_examples),
            "types": list(set(e["type"] for e in examples))
        }
    )


# ==================== 辅助功能接口 ====================

@router.get("/http-methods", response_model=ResponseModel, summary="获取支持的HTTP方法列表")
async def get_http_methods() -> ResponseModel | ResponseSchemaModel:
    """
    获取所有支持的HTTP方法
    """

    methods = [
        {"method": "GET", "description": "获取资源"},
        {"method": "POST", "description": "创建资源"},
        {"method": "PUT", "description": "更新资源(完整)"},
        {"method": "PATCH", "description": "更新资源(部分)"},
        {"method": "DELETE", "description": "删除资源"},
        {"method": "HEAD", "description": "获取资源头信息"},
        {"method": "OPTIONS", "description": "获取支持的方法"}
    ]

    return response_base.success(data={"methods": methods})


@router.get("/content-types", response_model=ResponseModel, summary="获取常用Content-Type列表")
async def get_content_types() -> ResponseModel | ResponseSchemaModel:
    """
    获取常用的Content-Type
    """

    content_types = [
        {"value": "application/json", "description": "JSON格式"},
        {"value": "application/x-www-form-urlencoded", "description": "表单格式"},
        {"value": "multipart/form-data", "description": "文件上传"},
        {"value": "application/xml", "description": "XML格式"},
        {"value": "text/plain", "description": "纯文本"},
        {"value": "text/html", "description": "HTML"},
    ]

    return response_base.success(data={"content_types": content_types})


@router.post("/test-jsonpath", response_model=ResponseModel, summary="测试JSONPath表达式")
async def test_jsonpath(
        json_data: Dict[str, Any] = Body(..., description="JSON数据"),
        path: str = Body(..., description="JSONPath表达式")
) -> ResponseModel | ResponseSchemaModel:
    """
    测试JSONPath表达式是否正确
    """
    from jsonpath_ng import parse

    try:
        jsonpath_expr = parse(path)
        matches = [match.value for match in jsonpath_expr.find(json_data)]

        return response_base.success(
            data={
                "valid": True,
                "matches": matches,
                "count": len(matches),
                "path": path
            }
        )
    except Exception as e:
        return response_base.fail(data=f"JSONPath表达式错误: {str(e)}")

