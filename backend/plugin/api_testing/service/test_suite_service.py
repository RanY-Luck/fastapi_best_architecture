#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API测试集合服务层
"""
from typing import Optional

from fastapi import Query
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import joinedload, selectinload

from backend.database.db import async_db_session
from backend.plugin.api_testing.model.models import ApiProject, ApiTestCase, ApiTestSuite, ApiTestSuiteCase
from backend.plugin.api_testing.schema.request import TestSuiteCreateRequest, TestSuiteUpdateRequest


def normalize_suite_case_ids(case_ids: list[int] | None) -> list[int]:
    """集合成员去重、保序并过滤非法值。"""
    if not case_ids:
        return []

    normalized: list[int] = []
    seen: set[int] = set()
    for case_id in case_ids:
        if not isinstance(case_id, int) or case_id <= 0 or case_id in seen:
            continue
        seen.add(case_id)
        normalized.append(case_id)
    return normalized


class TestSuiteService:
    """API测试集合服务类"""

    @staticmethod
    async def create_test_suite(suite_data: TestSuiteCreateRequest) -> ApiTestSuite:
        """创建测试集合。"""
        case_ids = normalize_suite_case_ids(suite_data.case_ids)

        async with async_db_session() as db:
            project = await db.scalar(select(ApiProject).where(ApiProject.id == suite_data.project_id))
            if not project:
                raise ValueError(f'项目ID {suite_data.project_id} 不存在')

            suite = ApiTestSuite(
                name=suite_data.name,
                project_id=suite_data.project_id,
                description=suite_data.description,
                status=suite_data.status,
            )
            db.add(suite)
            await db.flush()

            await TestSuiteService._replace_suite_cases(db, suite.id, suite_data.project_id, case_ids)
            await db.commit()

        return await TestSuiteService.get_test_suite_by_id(suite.id)

    @staticmethod
    async def get_test_suite_by_id(suite_id: int) -> Optional[ApiTestSuite]:
        """根据ID获取测试集合。"""
        async with async_db_session() as db:
            result = await db.execute(
                select(ApiTestSuite)
                .options(
                    joinedload(ApiTestSuite.project),
                    selectinload(ApiTestSuite.suite_cases).selectinload(ApiTestSuiteCase.test_case),
                )
                .where(ApiTestSuite.id == suite_id)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def get_test_suites(
        project_id: Optional[int] = None,
        status: Optional[int] = Query(None, description='测试集合状态，不传或传空表示查询所有状态'),
        name: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ApiTestSuite]:
        """获取测试集合列表。"""
        async with async_db_session() as db:
            query = select(ApiTestSuite).options(
                joinedload(ApiTestSuite.project),
                selectinload(ApiTestSuite.suite_cases),
            )

            if project_id is not None:
                query = query.where(ApiTestSuite.project_id == project_id)
            if name is not None and name.strip():
                query = query.where(ApiTestSuite.name.ilike(f'%{name}%'))
            if status is not None:
                query = query.where(ApiTestSuite.status == status)

            result = await db.execute(query.offset(skip).limit(limit).order_by(ApiTestSuite.created_time.desc()))
            return result.scalars().all()

    @staticmethod
    async def get_test_suite_count(
        project_id: Optional[int] = None,
        name: Optional[str] = None,
        status: Optional[int] = None,
    ) -> int:
        """获取测试集合总数。"""
        async with async_db_session() as db:
            query = select(func.count(ApiTestSuite.id))
            if project_id is not None:
                query = query.where(ApiTestSuite.project_id == project_id)
            if name is not None and name.strip():
                query = query.where(ApiTestSuite.name.ilike(f'%{name}%'))
            if status is not None:
                query = query.where(ApiTestSuite.status == status)
            return await db.scalar(query)

    @staticmethod
    async def update_test_suite(suite_id: int, suite_data: TestSuiteUpdateRequest) -> Optional[ApiTestSuite]:
        """更新测试集合。"""
        async with async_db_session() as db:
            suite = await db.scalar(select(ApiTestSuite).where(ApiTestSuite.id == suite_id))
            if not suite:
                return None

            update_data = {}
            if suite_data.name is not None:
                update_data['name'] = suite_data.name
            if suite_data.description is not None:
                update_data['description'] = suite_data.description
            if suite_data.status is not None:
                update_data['status'] = suite_data.status

            if update_data:
                await db.execute(update(ApiTestSuite).where(ApiTestSuite.id == suite_id).values(**update_data))

            if suite_data.case_ids is not None:
                await TestSuiteService._replace_suite_cases(
                    db,
                    suite_id,
                    suite.project_id,
                    normalize_suite_case_ids(suite_data.case_ids),
                )

            await db.commit()

        return await TestSuiteService.get_test_suite_by_id(suite_id)

    @staticmethod
    async def delete_test_suite(suite_id: int) -> bool:
        """删除测试集合。"""
        async with async_db_session() as db:
            result = await db.execute(delete(ApiTestSuite).where(ApiTestSuite.id == suite_id))
            await db.commit()
            return result.rowcount > 0

    @staticmethod
    async def get_suite_case_ids(suite_id: int, enabled_only: bool = True) -> list[int]:
        """获取集合内的用例ID列表。"""
        async with async_db_session() as db:
            query = (
                select(ApiTestCase.id)
                .join(ApiTestSuiteCase, ApiTestSuiteCase.test_case_id == ApiTestCase.id)
                .where(ApiTestSuiteCase.suite_id == suite_id)
                .order_by(ApiTestSuiteCase.order.asc(), ApiTestSuiteCase.id.asc())
            )
            if enabled_only:
                query = query.where(ApiTestCase.status == 1)
            result = await db.execute(query)
            return [row[0] for row in result.all()]

    @staticmethod
    async def _replace_suite_cases(db, suite_id: int, project_id: int, case_ids: list[int]) -> None:  # noqa: ANN001
        """替换集合成员。"""
        await db.execute(delete(ApiTestSuiteCase).where(ApiTestSuiteCase.suite_id == suite_id))
        if not case_ids:
            return

        result = await db.execute(
            select(ApiTestCase.id)
            .where(ApiTestCase.project_id == project_id)
            .where(ApiTestCase.id.in_(case_ids))
        )
        valid_ids = {row[0] for row in result.all()}
        missing_case_ids = [case_id for case_id in case_ids if case_id not in valid_ids]
        if missing_case_ids:
            raise ValueError(f'测试用例不存在或不属于当前项目: {missing_case_ids}')

        for index, case_id in enumerate(case_ids, start=1):
            db.add(ApiTestSuiteCase(suite_id=suite_id, test_case_id=case_id, order=index))
