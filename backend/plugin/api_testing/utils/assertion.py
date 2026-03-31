#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
断言工具模块
提供接口响应断言功能
"""
import re
from enum import Enum
from typing import Any, Dict, List, Optional

from jsonpath_ng import parse
from pydantic import BaseModel


class AssertionType(str, Enum):
    """断言类型枚举"""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    MATCH_REGEX = "match_regex"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUALS = "less_than_or_equals"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUALS = "greater_than_or_equals"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    IS_TRUE = "is_true"
    IS_FALSE = "is_false"
    LENGTH_EQUALS = "length_equals"
    LENGTH_GREATER_THAN = "length_greater_than"
    LENGTH_LESS_THAN = "length_less_than"


class AssertionSource(str, Enum):
    """断言来源枚举"""

    STATUS_CODE = "status_code"
    HEADERS = "headers"
    COOKIES = "cookies"
    BODY = "body"
    JSON = "json"
    ELAPSED_TIME = "elapsed_time"


class Assertion(BaseModel):
    """断言配置模型"""

    source: AssertionSource
    type: AssertionType
    path: Optional[str] = None
    expected: Optional[Any] = None
    message: Optional[str] = None


class AssertionResult(BaseModel):
    """断言结果模型"""

    assertion: Assertion
    success: bool
    actual: Optional[Any] = None
    message: Optional[str] = None


class AssertionEngine:
    """断言引擎"""

    @staticmethod
    def get_value_by_path(data: Any, path: str) -> Any:
        """通过路径获取数据值。"""
        if not path:
            return data

        if isinstance(data, dict) and path in data:
            return data[path]

        if isinstance(data, (dict, list)):
            try:
                jsonpath_expr = parse(path)
                matches = [match.value for match in jsonpath_expr.find(data)]
                if not matches:
                    return None
                return matches[0] if len(matches) == 1 else matches
            except Exception:
                if isinstance(data, dict):
                    return data.get(path)
                return None

        return None

    @staticmethod
    def _resolve_source_data(assertion: Assertion, response_data: Dict[str, Any]) -> Any:
        if assertion.source == AssertionSource.STATUS_CODE:
            return response_data.get("status_code")
        if assertion.source == AssertionSource.HEADERS:
            return response_data.get("headers", {})
        if assertion.source == AssertionSource.COOKIES:
            return response_data.get("cookies", {})
        if assertion.source == AssertionSource.BODY:
            return response_data.get("body", "")
        if assertion.source == AssertionSource.ELAPSED_TIME:
            return response_data.get("elapsed_time")
        if assertion.source == AssertionSource.JSON:
            return response_data.get("json")
        return None

    @staticmethod
    def _extract_actual_value(assertion: Assertion, source_data: Any, response_data: Dict[str, Any]) -> Any:
        if not assertion.path or assertion.source in (AssertionSource.STATUS_CODE, AssertionSource.BODY, AssertionSource.ELAPSED_TIME):
            return source_data

        actual_value = AssertionEngine.get_value_by_path(source_data, assertion.path)
        if actual_value is not None:
            return actual_value

        if assertion.source == AssertionSource.JSON:
            return AssertionEngine.get_value_by_path(response_data, assertion.path)

        return actual_value

    @staticmethod
    def _is_empty_value(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, (str, bytes, list, tuple, dict, set)):
            return len(value) == 0
        return False

    @staticmethod
    def execute_assertion(assertion: Assertion, response_data: Dict[str, Any]) -> AssertionResult:
        """执行断言。"""
        source_data = AssertionEngine._resolve_source_data(assertion, response_data)

        if source_data is None and assertion.type not in (AssertionType.IS_NULL, AssertionType.NOT_EXISTS):
            return AssertionResult(
                assertion=assertion,
                success=False,
                actual=None,
                message=f"断言来源 {assertion.source} 不存在",
            )

        actual_value = AssertionEngine._extract_actual_value(assertion, source_data, response_data)
        success = False
        message = None

        try:
            if assertion.type == AssertionType.EQUALS:
                success = actual_value == assertion.expected
                message = f"期望值: {assertion.expected}, 实际值: {actual_value}"
            elif assertion.type == AssertionType.NOT_EQUALS:
                success = actual_value != assertion.expected
                message = f"期望值不等于: {assertion.expected}, 实际值: {actual_value}"
            elif assertion.type == AssertionType.CONTAINS:
                if isinstance(actual_value, (str, list, dict)):
                    success = assertion.expected in actual_value
                message = f"期望包含: {assertion.expected}, 实际值: {actual_value}"
            elif assertion.type == AssertionType.NOT_CONTAINS:
                if isinstance(actual_value, (str, list, dict)):
                    success = assertion.expected not in actual_value
                message = f"期望不包含: {assertion.expected}, 实际值: {actual_value}"
            elif assertion.type == AssertionType.STARTS_WITH:
                if isinstance(actual_value, str):
                    success = actual_value.startswith(assertion.expected)
                message = f"期望以 {assertion.expected} 开头, 实际值: {actual_value}"
            elif assertion.type == AssertionType.ENDS_WITH:
                if isinstance(actual_value, str):
                    success = actual_value.endswith(assertion.expected)
                message = f"期望以 {assertion.expected} 结尾, 实际值: {actual_value}"
            elif assertion.type == AssertionType.MATCH_REGEX:
                if isinstance(actual_value, str):
                    success = bool(re.match(assertion.expected, actual_value))
                message = f"期望匹配正则: {assertion.expected}, 实际值: {actual_value}"
            elif assertion.type == AssertionType.LESS_THAN:
                if isinstance(actual_value, (int, float)) and isinstance(assertion.expected, (int, float)):
                    success = actual_value < assertion.expected
                message = f"期望小于: {assertion.expected}, 实际值: {actual_value}"
            elif assertion.type == AssertionType.LESS_THAN_OR_EQUALS:
                if isinstance(actual_value, (int, float)) and isinstance(assertion.expected, (int, float)):
                    success = actual_value <= assertion.expected
                message = f"期望小于等于: {assertion.expected}, 实际值: {actual_value}"
            elif assertion.type == AssertionType.GREATER_THAN:
                if isinstance(actual_value, (int, float)) and isinstance(assertion.expected, (int, float)):
                    success = actual_value > assertion.expected
                message = f"期望大于: {assertion.expected}, 实际值: {actual_value}"
            elif assertion.type == AssertionType.GREATER_THAN_OR_EQUALS:
                if isinstance(actual_value, (int, float)) and isinstance(assertion.expected, (int, float)):
                    success = actual_value >= assertion.expected
                message = f"期望大于等于: {assertion.expected}, 实际值: {actual_value}"
            elif assertion.type == AssertionType.EXISTS:
                success = actual_value is not None
                message = f"期望存在, 实际: {'存在' if success else '不存在'}"
            elif assertion.type == AssertionType.NOT_EXISTS:
                success = actual_value is None
                message = f"期望不存在, 实际: {'不存在' if success else '存在'}"
            elif assertion.type == AssertionType.IS_EMPTY:
                success = AssertionEngine._is_empty_value(actual_value)
                message = f"期望为空, 实际值: {actual_value}"
            elif assertion.type == AssertionType.IS_NOT_EMPTY:
                success = not AssertionEngine._is_empty_value(actual_value)
                message = f"期望不为空, 实际值: {actual_value}"
            elif assertion.type == AssertionType.IS_NULL:
                success = actual_value is None
                message = f"期望为null, 实际值: {actual_value}"
            elif assertion.type == AssertionType.IS_NOT_NULL:
                success = actual_value is not None
                message = f"期望不为null, 实际值: {actual_value}"
            elif assertion.type == AssertionType.IS_TRUE:
                success = actual_value is True
                message = f"期望为true, 实际值: {actual_value}"
            elif assertion.type == AssertionType.IS_FALSE:
                success = actual_value is False
                message = f"期望为false, 实际值: {actual_value}"
            elif assertion.type == AssertionType.LENGTH_EQUALS:
                if hasattr(actual_value, "__len__"):
                    success = len(actual_value) == assertion.expected
                message = f"期望长度等于: {assertion.expected}, 实际长度: {len(actual_value) if hasattr(actual_value, '__len__') else 'N/A'}"
            elif assertion.type == AssertionType.LENGTH_GREATER_THAN:
                if hasattr(actual_value, "__len__"):
                    success = len(actual_value) > assertion.expected
                message = f"期望长度大于: {assertion.expected}, 实际长度: {len(actual_value) if hasattr(actual_value, '__len__') else 'N/A'}"
            elif assertion.type == AssertionType.LENGTH_LESS_THAN:
                if hasattr(actual_value, "__len__"):
                    success = len(actual_value) < assertion.expected
                message = f"期望长度小于: {assertion.expected}, 实际长度: {len(actual_value) if hasattr(actual_value, '__len__') else 'N/A'}"
            else:
                message = f"不支持的断言类型: {assertion.type}"
        except Exception as exc:  # noqa: BLE001
            message = f"断言执行异常: {exc}"
            success = False

        if assertion.message:
            message = f"{assertion.message}: {message}"

        return AssertionResult(assertion=assertion, success=success, actual=actual_value, message=message)

    @staticmethod
    def execute_assertions(assertions: List[Assertion], response_data: Dict[str, Any]) -> List[AssertionResult]:
        """批量执行断言。"""
        return [AssertionEngine.execute_assertion(assertion, response_data) for assertion in assertions]
