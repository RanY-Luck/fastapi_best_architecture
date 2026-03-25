#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境和变量管理API
"""
from typing import Dict, Optional, Any
from fastapi import APIRouter, Body, Path, Query
from backend.common.response.response_schema import response_base, ResponseModel, ResponseSchemaModel
from backend.common.log import log
from backend.plugin.api_testing.utils.environment import (
    EnvironmentManager, EnvironmentModel, VariableManager, VariableModel, VariableScope
)

router = APIRouter()


# 环境管理接口
@router.post("", summary="创建环境")
async def create_environment(environment: EnvironmentModel) -> ResponseModel | ResponseSchemaModel:
    """
    创建环境
    """
    try:
        environment.id = None
        environment.updated_time = None
        new_env: EnvironmentModel = await EnvironmentManager.create_environment(environment)
        return response_base.success(data=new_env.model_dump())
    except Exception as e:
        log.error(f"创建环境失败: {e}")
        return response_base.fail(data=f"创建环境失败: {str(e)}")


@router.get("/{environment_id}", summary="获取环境信息")
async def get_environment(environment_id: int = Path(description="环境ID")) -> ResponseModel | ResponseSchemaModel:
    """
    获取环境信息
    """
    environment = await EnvironmentManager.get_environment(environment_id)
    if environment:
        return response_base.success(data=environment.model_dump())
    return response_base.fail(data=f"环境不存在: {environment_id}")


@router.put("/{environment_id}", summary="更新环境信息")
async def update_environment(
        environment: EnvironmentModel,
        environment_id: int = Path(description="环境ID")
) -> ResponseModel | ResponseSchemaModel:
    """
    更新环境信息
    """
    environment.id = environment_id
    success = await EnvironmentManager.update_environment(environment)
    if success:
        updated_env = await EnvironmentManager.get_environment(environment_id)
        if updated_env:
            return response_base.success(data=updated_env.model_dump())
        return response_base.fail(data=f"环境更新后读取失败: {environment_id}")
    return response_base.fail(data=f"环境不存在或更新失败: {environment_id}")


@router.delete("/{environment_id}", summary="删除环境")
async def delete_environment(environment_id: int = Path(description="环境ID")) -> ResponseModel | ResponseSchemaModel:
    """
    删除环境
    """
    success = await EnvironmentManager.delete_environment(environment_id)
    if success:
        return response_base.success(data=f"删除环境ID为:{environment_id} 成功")
    return response_base.fail(data=f"环境不存在或删除失败: {environment_id}")


@router.get("", summary="获取环境列表")
async def list_environments(
        project_id: Optional[int] = Query(None, description="项目ID"),
        name: Optional[str] = Query(None, description="环境名称"),
        status: Optional[int] = Query(None, description="环境状态")
) -> ResponseModel | ResponseSchemaModel:
    """
    获取环境列表（支持按项目ID、名称、状态筛选）
    """
    environments = await EnvironmentManager.list_environments(
        project_id=project_id,
        name=name,
        status=status
    )
    return response_base.success(data=[env.model_dump() for env in environments])


@router.get("/default/{project_id}", summary="获取默认环境")
async def get_default_environment(
        project_id: int = Path(..., description="项目ID")
) -> ResponseModel | ResponseSchemaModel:
    """
    获取项目默认环境
    """
    environment = await EnvironmentManager.get_default_environment(project_id)
    if environment:
        return response_base.success(data=environment.model_dump())
    return response_base.fail(data=f"项目未设置默认环境: {project_id}")


@router.put("/{environment_id}/default", summary="设置默认环境")
async def set_default_environment(
        project_id: int = Query(..., description="项目ID"),
        environment_id: int = Path(..., description="环境ID"),
) -> ResponseModel | ResponseSchemaModel:
    """
    设置项目默认环境
    """
    environment = await EnvironmentManager.get_environment(environment_id)
    if not environment:
        return response_base.fail(data=f"环境不存在: {environment_id}")
    if environment.project_id != project_id:
        return response_base.fail(data=f"环境 {environment_id} 不属于项目 {project_id}")

    success = await EnvironmentManager.set_default_environment(project_id, environment_id)
    if success:
        return response_base.success(data="设置默认环境成功")
    return response_base.fail(data=f"设置默认环境失败: project_id={project_id}, environment_id={environment_id}")


# 变量管理接口
@router.post("/variables", summary="创建变量")
async def create_variable(variable: VariableModel) -> ResponseModel | ResponseSchemaModel:
    """
    创建变量
    """
    success = await VariableManager.set_variable(variable)
    if success:
        return response_base.success(data=variable.model_dump())
    return response_base.fail(data="创建变量失败")


@router.get("/variables/", summary="获取变量列表")
async def list_variables(
        scope: VariableScope = Query(..., description="变量作用域"),
        project_id: Optional[int] = Query(None, description="项目ID"),
        environment_id: Optional[int] = Query(None, description="环境ID"),
        case_id: Optional[int] = Query(None, description="用例ID")
) -> ResponseModel | ResponseSchemaModel:
    """
    获取变量列表
    """
    variables = await VariableManager.list_variables(
        scope=scope,
        project_id=project_id,
        environment_id=environment_id,
        case_id=case_id
    )
    return response_base.success(data=[var.model_dump() for var in variables])


@router.get("/variables/{name}", summary="获取变量")
async def get_variable(
        name: str = Path(description="变量名"),
        scope: VariableScope = Query(..., description="变量作用域"),
        project_id: Optional[int] = Query(None, description="项目ID"),
        environment_id: Optional[int] = Query(None, description="环境ID"),
        case_id: Optional[int] = Query(None, description="用例ID")
) -> ResponseModel | ResponseSchemaModel:
    """
    获取变量
    """
    variable = await VariableManager.get_variable(
        name=name,
        scope=scope,
        project_id=project_id,
        environment_id=environment_id,
        case_id=case_id
    )
    if variable:
        return response_base.success(data=variable.model_dump())
    return response_base.fail(data=f"变量不存在: {name}")


@router.delete("/variables/{name}", summary="删除变量")
async def delete_variable(
        name: str = Path(description="变量名"),
        scope: VariableScope = Query(description="变量作用域"),
        project_id: Optional[int] = Query(None, description="项目ID"),
        environment_id: Optional[int] = Query(None, description="环境ID"),
        case_id: Optional[int] = Query(None, description="用例ID")
) -> ResponseModel | ResponseSchemaModel:
    """
    删除变量
    """
    success = await VariableManager.delete_variable(
        name=name,
        scope=scope,
        project_id=project_id,
        environment_id=environment_id,
        case_id=case_id
    )
    if success:
        return response_base.success(data="删除变量成功")
    return response_base.fail(data=f"删除变量失败: {name}")


@router.post("/variables/process-template", summary="处理变量模板")
async def process_template(
        template: str = Body(..., description="模板字符串"),
        project_id: Optional[int] = Body(None, description="项目ID"),
        environment_id: Optional[int] = Body(None, description="环境ID"),
        case_id: Optional[int] = Body(None, description="用例ID"),
        temp_variables: Optional[Dict[str, Any]] = Body(None, description="临时变量")
) -> ResponseModel | ResponseSchemaModel:
    """
    处理变量模板，替换模板中的变量引用
    """
    result = await VariableManager.process_template(
        template=template,
        project_id=project_id,
        environment_id=environment_id,
        case_id=case_id,
        temp_variables=temp_variables
    )
    return response_base.success(data={"result": result})
