#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据驱动测试API
"""
import pandas as pd
import json
import os
from pathlib import Path as FilePath
from fastapi import APIRouter, Path, UploadFile, File, Form
from backend.common.response.response_schema import response_base, ResponseModel, ResponseSchemaModel
from backend.plugin.api_testing.utils.data_driven import (
    DataDriverManager, DataDrivenConfig, DataSourceConfig, DataSourceType
)

router = APIRouter()


ALLOWED_UPLOAD_SUFFIXES = {
    ".csv": "csv",
    ".xls": "excel",
    ".xlsx": "excel",
    ".json": "json",
}


def normalize_data_subpath(subpath: str) -> str:
    normalized = (subpath or "data").replace("\\", "/").strip()
    normalized = normalized.strip("/")
    if not normalized:
        normalized = "data"
    candidate = FilePath(normalized)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("目录路径不合法")
    return normalized


def build_data_path(*parts: str) -> str:
    from backend.core.path_conf import PLUGIN_DIR

    normalized_parts = [normalize_data_subpath(part) for part in parts if part]
    base_path = FilePath(PLUGIN_DIR) / "api_testing"
    target_path = base_path.joinpath(*normalized_parts).resolve()
    if base_path.resolve() not in target_path.parents and target_path != base_path.resolve():
        raise ValueError("目录路径超出插件范围")
    return str(target_path)


def validate_upload_file(filename: str, expected_type: str) -> None:
    suffix = FilePath(filename or "").suffix.lower()
    if not suffix:
        raise ValueError("上传文件缺少扩展名")
    actual_type = ALLOWED_UPLOAD_SUFFIXES.get(suffix)
    if actual_type != expected_type:
        raise ValueError(f"不支持的文件类型: {suffix}")


@router.post("/config", summary="创建或更新数据驱动测试配置")
async def create_data_driven_config(config: DataDrivenConfig) -> ResponseModel | ResponseSchemaModel:
    """
    创建或更新数据驱动测试配置
    """
    try:
        if config.data_source and config.data_source.type != DataSourceType.PARAMETER:
            if config.data_source.file_path:
                file_path = build_data_path(config.data_source.file_path)
                if not os.path.exists(file_path):
                    return response_base.fail(data=f"文件不存在: {file_path}")

        iterations = await DataDriverManager.prepare_iterations(config)
        config.iterations = iterations

        return response_base.success(data=config.model_dump())
    except Exception as e:
        return response_base.fail(data=f"数据驱动测试配置创建失败: {str(e)}")


@router.post("/upload/csv", summary="上传CSV数据文件")
async def upload_csv_file(
        file: UploadFile = File(...),
        directory: str = Form("data")
) -> ResponseModel | ResponseSchemaModel:
    """
    上传CSV数据文件
    
    保存到插件目录的指定子目录中
    """
    try:
        validate_upload_file(file.filename, "csv")
        normalized_directory = normalize_data_subpath(directory)
        save_dir = build_data_path(normalized_directory)
        os.makedirs(save_dir, exist_ok=True)

        file_path = os.path.join(save_dir, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        df = pd.read_csv(file_path, nrows=5)
        preview = df.to_dict(orient='records')

        return response_base.success(
            data={
                "file_path": f"{normalized_directory}/{file.filename}",
                "columns": list(df.columns),
                "preview": preview,
                "rows": len(pd.read_csv(file_path))
            }
        )
    except Exception as e:
        return response_base.fail(data=f"CSV文件上传失败: {str(e)}")


@router.post("/upload/excel", summary="上传Excel数据文件")
async def upload_excel_file(
        file: UploadFile = File(...),
        directory: str = Form("data")
) -> ResponseModel | ResponseSchemaModel:
    """
    上传Excel数据文件
    
    保存到插件目录的指定子目录中
    """
    try:
        validate_upload_file(file.filename, "excel")
        normalized_directory = normalize_data_subpath(directory)
        save_dir = build_data_path(normalized_directory)
        os.makedirs(save_dir, exist_ok=True)

        file_path = os.path.join(save_dir, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        xls = pd.ExcelFile(file_path)
        sheet_info = {}

        for sheet_name in xls.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=5)
            sheet_info[sheet_name] = {
                "columns": list(df.columns),
                "preview": df.to_dict(orient='records'),
                "rows": len(pd.read_excel(file_path, sheet_name=sheet_name))
            }

        return response_base.success(
            data={
                "file_path": f"{normalized_directory}/{file.filename}",
                "sheets": sheet_info
            }
        )
    except Exception as e:
        return response_base.fail(data=f"Excel文件上传失败: {str(e)}")


@router.post("/upload/json", summary="上传JSON数据文件")
async def upload_json_file(
        file: UploadFile = File(...),
        directory: str = Form("data")
) -> ResponseModel | ResponseSchemaModel:
    """
    上传JSON数据文件
    
    保存到插件目录的指定子目录中
    """
    try:
        validate_upload_file(file.filename, "json")
        normalized_directory = normalize_data_subpath(directory)
        save_dir = build_data_path(normalized_directory)
        os.makedirs(save_dir, exist_ok=True)

        file_path = os.path.join(save_dir, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        with open(file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        preview = json_data
        items_count = 1

        if isinstance(json_data, list):
            items_count = len(json_data)
            preview = json_data[:5] if len(json_data) > 5 else json_data
        elif isinstance(json_data, dict):
            preview = [json_data]

        return response_base.success(
            data={
                "file_path": f"{normalized_directory}/{file.filename}",
                "preview": preview,
                "items_count": items_count
            }
        )
    except Exception as e:
        return response_base.fail(data=f"JSON文件上传失败: {str(e)}")


@router.post("/validate-data-source", summary="验证数据源配置")
async def validate_data_source(config: DataSourceConfig) -> ResponseModel | ResponseSchemaModel:
    """
    验证数据源配置
    
    加载部分数据验证数据源配置是否正确
    """
    try:
        # 加载前5条数据
        data = await DataDriverManager.load_data_source(config)
        preview = data[:5] if len(data) > 5 else data

        return response_base.success(
            data={
                "valid": True,
                "rows_count": len(data),
                "preview": preview,
                "columns": list(preview[0].keys()) if preview else []
            }
        )
    except Exception as e:
        return response_base.fail(
            data=f"数据源配置验证失败: {str(e)}"
        )


@router.post("/prepare-iterations", summary="准备测试迭代数据")
async def prepare_iterations(config: DataDrivenConfig) -> ResponseModel | ResponseSchemaModel:
    """
    准备测试迭代数据
    
    根据数据驱动配置生成测试迭代数据
    """
    try:
        iterations = await DataDriverManager.prepare_iterations(config)

        return response_base.success(
            data={
                "iterations_count": len(iterations),
                "iterations": [iter.model_dump() for iter in iterations]
            }
        )
    except Exception as e:
        return response_base.fail(data=f"测试迭代数据准备失败: {str(e)}")


@router.get("/data-directories", summary="获取数据目录列表")
async def get_data_directories() -> ResponseModel | ResponseSchemaModel:
    """
    获取数据目录列表
    
    获取插件目录下可用于存放数据文件的目录列表
    """
    try:
        plugin_dir = build_data_path()
        data_dir = build_data_path("data")
        os.makedirs(data_dir, exist_ok=True)

        directories = []
        for root, dirs, files in os.walk(plugin_dir):
            if os.path.abspath(root) != os.path.abspath(plugin_dir):
                rel_path = os.path.relpath(root, plugin_dir).replace("\\", "/")
                directories.append(rel_path)

        return response_base.success(data=directories)
    except Exception as e:
        return response_base.fail(data=f"获取数据目录列表失败: {str(e)}")


@router.get("/data-files/{directory}", summary="获取数据目录下的文件")
async def get_data_files(directory: str = Path(..., description="目录路径")) -> ResponseModel | ResponseSchemaModel:
    """
    获取数据目录下的文件
    
    获取指定数据目录下的所有文件
    """
    try:
        normalized_directory = normalize_data_subpath(directory)
        dir_path = build_data_path(normalized_directory)

        if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
            return response_base.fail(data=f"目录不存在: {directory}")

        files = []
        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            if os.path.isfile(file_path):
                files.append(
                    {
                        "name": filename,
                        "path": f"{normalized_directory}/{filename}",
                        "size": os.path.getsize(file_path),
                        "type": os.path.splitext(filename)[1].lstrip('.')
                    }
                )

        return response_base.success(data=files)
    except Exception as e:
        return response_base.fail(data=f"获取数据文件列表失败: {str(e)}")
