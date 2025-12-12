#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time     : 2025/12/12 11:25
# @Author   : 冉勇
# @File     : json_serialization.py
# @Software : PyCharm
# @Desc     :
"""
序列化辅助工具
处理复杂对象的JSON序列化
"""
from datetime import datetime, date
from typing import Any, Dict, List, Union
from decimal import Decimal


class SerializationHelper:
    """序列化辅助类"""

    @staticmethod
    def make_serializable(obj: Any) -> Any:
        """
        将对象转换为可JSON序列化的格式

        :param obj: 任意对象
        :return: 可序列化的对象
        """
        if obj is None:
            return None

        # 处理datetime和date对象
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()

        # 处理Decimal
        elif isinstance(obj, Decimal):
            return float(obj)

        # 处理字典
        elif isinstance(obj, dict):
            return {
                key: SerializationHelper.make_serializable(value)
                for key, value in obj.items()
            }

        # 处理列表/元组
        elif isinstance(obj, (list, tuple)):
            return [
                SerializationHelper.make_serializable(item)
                for item in obj
            ]

        # 处理集合
        elif isinstance(obj, set):
            return [
                SerializationHelper.make_serializable(item)
                for item in obj
            ]

        # 处理Pydantic模型
        elif hasattr(obj, 'model_dump'):
            model_dict = obj.model_dump()
            return SerializationHelper.make_serializable(model_dict)

        # 处理普通对象（尝试转换为字典）
        elif hasattr(obj, '__dict__'):
            return SerializationHelper.make_serializable(obj.__dict__)

        # 其他类型直接返回
        else:
            return obj

    @staticmethod
    def serialize_step_results(step_results: List[Any]) -> List[Dict[str, Any]]:
        """
        序列化步骤结果列表

        :param step_results: 步骤结果列表
        :return: 可序列化的步骤结果列表
        """
        serializable_steps = []

        for step in step_results:
            # 获取步骤字典
            if hasattr(step, 'model_dump'):
                step_dict = step.model_dump()
            elif isinstance(step, dict):
                step_dict = step
            else:
                step_dict = step.__dict__

            # 递归处理所有字段
            serializable_step = SerializationHelper.make_serializable(step_dict)
            serializable_steps.append(serializable_step)

        return serializable_steps

    @staticmethod
    def serialize_report_details(details: Dict[str, Any]) -> Dict[str, Any]:
        """
        序列化报告详情

        :param details: 报告详情字典
        :return: 可序列化的报告详情
        """
        return SerializationHelper.make_serializable(details)