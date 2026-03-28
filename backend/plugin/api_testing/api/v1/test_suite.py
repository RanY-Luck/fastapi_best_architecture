#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API测试集合管理接口
"""
from fastapi import APIRouter, Path, Query

from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.plugin.api_testing.schema.request import (
    BatchExecutionRequest,
    BatchExecutionResponse,
    TestSuiteCreateRequest,
    TestSuiteResponse,
    TestSuiteUpdateRequest,
)
from backend.plugin.api_testing.service.test_batch_execution_service import BatchExecutionService
from backend.plugin.api_testing.service.test_suite_service import TestSuiteService

router = APIRouter()


def build_test_suite_response(test_suite) -> TestSuiteResponse:  # noqa: ANN001
    """构建测试集合响应。"""
    suite_cases = sorted(test_suite.suite_cases, key=lambda item: item.order)
    case_ids = [suite_case.test_case_id for suite_case in suite_cases]
    return TestSuiteResponse(
        id=test_suite.id,
        name=test_suite.name,
        project_id=test_suite.project_id,
        project_name=test_suite.project.name if test_suite.project else None,
        description=test_suite.description,
        status=test_suite.status,
        case_ids=case_ids,
        case_count=len(case_ids),
        created_time=test_suite.created_time.isoformat() if test_suite.created_time else '',
        updated_time=test_suite.updated_time.isoformat() if test_suite.updated_time else '',
    )


@router.post('', response_model=ResponseModel, summary='创建测试集合')
async def create_test_suite(suite_data: TestSuiteCreateRequest) -> ResponseModel | ResponseSchemaModel:
    """创建测试集合。"""
    try:
        suite = await TestSuiteService.create_test_suite(suite_data)
        return response_base.success(data=build_test_suite_response(suite).model_dump())
    except Exception as exc:  # noqa: BLE001
        return response_base.fail(data=f'创建测试集合失败: {str(exc)}')


@router.get('/{suite_id}', response_model=ResponseModel, summary='获取测试集合详情')
async def get_test_suite(suite_id: int = Path(..., description='测试集合ID')) -> ResponseModel | ResponseSchemaModel:
    """获取测试集合详情。"""
    try:
        suite = await TestSuiteService.get_test_suite_by_id(suite_id)
        if not suite:
            return response_base.fail(data='测试集合不存在')
        return response_base.success(data=build_test_suite_response(suite).model_dump())
    except Exception as exc:  # noqa: BLE001
        return response_base.fail(data=f'获取测试集合失败: {str(exc)}')


@router.get('', response_model=ResponseModel, summary='获取测试集合列表')
async def get_test_suites(
    project_id: int | None = Query(None, description='项目ID'),
    status: int | None = Query(None, description='状态'),
    name: str | None = Query(None, description='集合名称'),
    skip: int = Query(0, description='跳过数量'),
    limit: int = Query(20, description='限制数量'),
) -> ResponseModel | ResponseSchemaModel:
    """获取测试集合列表。"""
    try:
        suites = await TestSuiteService.get_test_suites(
            project_id=project_id,
            status=status,
            name=name,
            skip=skip,
            limit=limit,
        )
        total = await TestSuiteService.get_test_suite_count(project_id=project_id, name=name, status=status)
        return response_base.success(
            data={
                'items': [build_test_suite_response(suite).model_dump() for suite in suites],
                'total': total,
                'skip': skip,
                'limit': limit,
                'project_id': project_id,
            }
        )
    except Exception as exc:  # noqa: BLE001
        return response_base.fail(data=f'获取测试集合列表失败: {str(exc)}')


@router.put('/{suite_id}', response_model=ResponseModel, summary='更新测试集合')
async def update_test_suite(
    suite_data: TestSuiteUpdateRequest,
    suite_id: int = Path(..., description='测试集合ID'),
) -> ResponseModel | ResponseSchemaModel:
    """更新测试集合。"""
    try:
        suite = await TestSuiteService.update_test_suite(suite_id, suite_data)
        if not suite:
            return response_base.fail(data='测试集合不存在')
        return response_base.success(data=build_test_suite_response(suite).model_dump())
    except Exception as exc:  # noqa: BLE001
        return response_base.fail(data=f'更新测试集合失败: {str(exc)}')


@router.delete('/{suite_id}', response_model=ResponseModel, summary='删除测试集合')
async def delete_test_suite(suite_id: int = Path(..., description='测试集合ID')) -> ResponseModel | ResponseSchemaModel:
    """删除测试集合。"""
    try:
        success = await TestSuiteService.delete_test_suite(suite_id)
        if not success:
            return response_base.fail(data='测试集合不存在或删除失败')
        return response_base.success(data='测试集合删除成功')
    except Exception as exc:  # noqa: BLE001
        return response_base.fail(data=f'删除测试集合失败: {str(exc)}')


@router.get('/{suite_id}/cases', response_model=ResponseModel, summary='获取测试集合关联用例')
async def get_test_suite_cases(suite_id: int = Path(..., description='测试集合ID')) -> ResponseModel | ResponseSchemaModel:
    """获取测试集合关联的用例列表。"""
    try:
        suite = await TestSuiteService.get_test_suite_by_id(suite_id)
        if not suite:
            return response_base.fail(data='测试集合不存在')
        suite_cases = sorted(suite.suite_cases, key=lambda item: item.order)
        cases = [
            {
                'id': sc.test_case_id,
                'name': sc.test_case.name if sc.test_case else '',
                'status': sc.test_case.status if sc.test_case else None,
                'order': sc.order,
            }
            for sc in suite_cases
        ]
        return response_base.success(data=cases)
    except Exception as exc:  # noqa: BLE001
        return response_base.fail(data=f'获取关联用例失败: {str(exc)}')


@router.post('/{suite_id}/execute', response_model=ResponseModel, summary='批量执行测试集合')
async def execute_test_suite(
    execution_data: BatchExecutionRequest,
    suite_id: int = Path(..., description='测试集合ID'),
) -> ResponseModel | ResponseSchemaModel:
    """按测试集合批量执行。"""
    try:
        result = await BatchExecutionService.execute_suite(
            suite_id,
            environment_id=execution_data.environment_id,
            max_concurrency=execution_data.max_concurrency,
        )
        return response_base.success(data=BatchExecutionResponse(**result).model_dump())
    except Exception as exc:  # noqa: BLE001
        return response_base.fail(data=f'批量执行测试集合失败: {str(exc)}')
