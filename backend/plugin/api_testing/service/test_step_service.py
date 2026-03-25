#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API测试步骤服务层
"""
from typing import List, Optional

from fastapi import Query
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import joinedload

from backend.database.db import async_db_session
from backend.plugin.api_testing.model.models import ApiTestStep, ApiTestCase
from backend.plugin.api_testing.schema.request import TestStepCreateRequest, TestStepUpdateRequest


class TestStepService:
    """API测试步骤服务类"""

    @staticmethod
    async def create_test_step(step_data: TestStepCreateRequest) -> ApiTestStep:
        """创建测试步骤"""
        async with async_db_session() as db:
            # 验证测试用例是否存在
            test_case_result = await db.execute(
                select(ApiTestCase).where(ApiTestCase.id == step_data.test_case_id)
            )
            test_case = test_case_result.scalar_one_or_none()
            if not test_case:
                raise ValueError(f"测试用例ID {step_data.test_case_id} 不存在")
            test_step = ApiTestStep(
                name=step_data.name,
                test_case_id=step_data.test_case_id,
                url=step_data.url,
                method=step_data.method,
                headers=step_data.headers,
                params=step_data.params,
                body=step_data.body,
                files=step_data.files,
                auth=step_data.auth,
                extract=step_data.extract,
                validate=step_data.validations,
                sql_queries=step_data.sql_queries,
                timeout=step_data.timeout,
                retry=step_data.retry,
                retry_interval=step_data.retry_interval,
                order=step_data.order,
                status=step_data.status
            )
            db.add(test_step)
            await db.commit()
            await db.refresh(test_step)
            return test_step

    @staticmethod
    async def get_test_step_by_id(step_id: int) -> Optional[ApiTestStep]:
        """根据ID获取测试步骤"""
        async with async_db_session() as db:
            result = await db.execute(select(ApiTestStep).where(ApiTestStep.id == step_id))
            return result.scalar_one_or_none()

    @staticmethod
    async def get_test_steps(
            test_case_id: Optional[int] = None,
            name: Optional[str] = None,
            method: Optional[str] = None,
            status: Optional[int] = Query(None, description="测试步骤状态，不传或传空表示查询所有状态"),
            skip: int = 0,
            limit: int = 20
    ) -> List[ApiTestStep]:
        """获取测试步骤列表"""
        async with async_db_session() as db:
            query = select(ApiTestStep).options(
                joinedload(ApiTestStep.test_case)
            )

            if test_case_id:
                query = query.where(ApiTestStep.test_case_id == test_case_id)
            if name is not None and name.strip():
                query = query.where(ApiTestStep.name.ilike(f"%{name}%"))
            if method:
                query = query.where(ApiTestStep.method == method)
            if status is not None:
                query = query.where(ApiTestStep.status == status)

            query = query.offset(skip).limit(limit).order_by(ApiTestStep.created_time.desc())
            result = await db.execute(query)
            return result.scalars().all()

    @staticmethod
    async def update_test_step(
            step_id: int,
            step_data: TestStepUpdateRequest,
            partial: bool = True  # True=PATCH部分更新, False=PUT完整更新
    ) -> Optional[ApiTestStep]:
        """更新测试步骤"""
        async with async_db_session() as db:
            if partial:
                # PATCH: 只更新传递的字段
                update_data = step_data.model_dump(exclude_unset=True)
            else:
                # PUT: 完整更新,未传递的字段使用模型默认值或 None
                update_data = step_data.model_dump(exclude_unset=False)

            # 特殊处理 method 字段
            if 'method' in update_data and update_data['method'] is not None:
                update_data['method'] = str(update_data['method'])

            # 处理字段名映射
            if 'validations' in update_data:
                update_data['validate'] = update_data.pop('validations')

            if update_data:
                await db.execute(
                    update(ApiTestStep)
                    .where(ApiTestStep.id == step_id)
                    .values(**update_data)
                )
                await db.commit()

            result = await db.execute(select(ApiTestStep).where(ApiTestStep.id == step_id))
            return result.scalar_one_or_none()

    @staticmethod
    async def delete_test_step(step_id: int) -> bool:
        """删除测试步骤"""
        async with async_db_session() as db:
            result = await db.execute(delete(ApiTestStep).where(ApiTestStep.id == step_id))
            await db.commit()
            return result.rowcount > 0

    @staticmethod
    async def get_test_step_count(
            test_case_id: Optional[int] = None,
            name: Optional[str] = None,
            method: Optional[str] = None,
            status: Optional[int] = None,
    ) -> int:
        """获取测试步骤总数"""
        async with async_db_session() as db:
            query = select(func.count(ApiTestStep.id))
            if test_case_id is not None:
                query = query.where(ApiTestStep.test_case_id == test_case_id)
            if name is not None and name.strip():
                query = query.where(ApiTestStep.name.ilike(f"%{name}%"))
            if method:
                query = query.where(ApiTestStep.method == method)
            if status is not None:
                query = query.where(ApiTestStep.status == status)
            result = await db.execute(query)
            return result.scalar()

    @staticmethod
    async def reorder_steps(test_case_id: int, step_orders: List[dict]) -> bool:
        """重新排序测试步骤"""
        async with async_db_session() as db:
            try:
                for item in step_orders:
                    await db.execute(
                        update(ApiTestStep)
                        .where(ApiTestStep.id == item['step_id'])
                        .where(ApiTestStep.test_case_id == test_case_id)
                        .values(order=item['order'])
                    )
                await db.commit()
                return True
            except Exception:
                await db.rollback()
                return False
