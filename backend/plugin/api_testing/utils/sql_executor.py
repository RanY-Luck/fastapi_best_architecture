#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQL执行工具模块
提供数据库查询和执行功能
"""
from enum import Enum
from typing import Any, Dict, List, Optional

import pymysql
from pydantic import BaseModel
from sqlalchemy import URL, text

from backend.common.log import log
from backend.core.conf import settings
from backend.database.db import create_database_async_engine
from backend.plugin.api_testing.utils.assertion import Assertion, AssertionEngine


try:
    import psycopg

    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False
    log.warning("psycopg库未安装或缺少PostgreSQL客户端库，PostgreSQL功能将不可用。")


class DatabaseType(str, Enum):
    """数据库类型枚举"""

    MYSQL = "mysql"
    POSTGRESQL = "postgresql"


class DBConfig(BaseModel):
    """数据库配置"""

    type: DatabaseType
    host: str
    port: int
    username: str
    password: str
    database: str


class SQLQuery(BaseModel):
    """SQL查询配置"""

    name: str
    query: str
    extract: Optional[Dict[str, str]] = None
    validations: Optional[List[Dict[str, Any]]] = None
    use_default_db: bool = True
    db_config: Optional[DBConfig] = None


class SQLResult(BaseModel):
    """SQL执行结果"""

    name: str
    query: str
    success: bool
    error: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    affected_rows: Optional[int] = None
    extracted_variables: Optional[Dict[str, Any]] = None
    validation_results: Optional[List[Dict[str, Any]]] = None


class SQLExecutor:
    """SQL执行器"""

    @staticmethod
    def get_default_db_config() -> DBConfig:
        db_type = DatabaseType.MYSQL if settings.DATABASE_TYPE == "mysql" else DatabaseType.POSTGRESQL
        return DBConfig(
            type=db_type,
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            username=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_SCHEMA,
        )

    @staticmethod
    def _resolve_db_config(sql_query: SQLQuery) -> DBConfig:
        db_config = sql_query.db_config
        if sql_query.use_default_db or db_config is None:
            db_config = SQLExecutor.get_default_db_config()
        return db_config

    @staticmethod
    def _init_result(sql_query: SQLQuery) -> SQLResult:
        return SQLResult(name=sql_query.name, query=sql_query.query, success=False)

    @staticmethod
    async def execute_query(sql_query: SQLQuery) -> SQLResult:
        db_config = SQLExecutor._resolve_db_config(sql_query)
        result = SQLExecutor._init_result(sql_query)

        try:
            if db_config.type == DatabaseType.MYSQL:
                result = await SQLExecutor._execute_mysql_query(sql_query, db_config, result)
            elif db_config.type == DatabaseType.POSTGRESQL:
                if not PSYCOPG_AVAILABLE:
                    result.error = "PostgreSQL功能不可用，请安装psycopg及PostgreSQL客户端库"
                    return result
                result = await SQLExecutor._execute_postgresql_query(sql_query, db_config, result)
            else:
                result.error = f"不支持的数据库类型: {db_config.type}"
                return result

            SQLExecutor._apply_validations(sql_query, result)
            return result
        except Exception as exc:  # noqa: BLE001
            result.error = f"SQL执行异常: {exc}"
            log.error(f"SQL执行异常: {exc}")
            return result

    @staticmethod
    async def execute_query_async(sql_query: SQLQuery) -> SQLResult:
        db_config = SQLExecutor._resolve_db_config(sql_query)
        result = SQLExecutor._init_result(sql_query)

        try:
            result = await SQLExecutor._execute_async_query(sql_query, db_config, result)
            SQLExecutor._apply_validations(sql_query, result)
            return result
        except Exception as exc:  # noqa: BLE001
            result.error = f"SQL异步执行异常: {exc}"
            log.error(f"SQL异步执行异常: {exc}")
            return result

    @staticmethod
    def _build_async_database_url(db_config: DBConfig) -> URL:
        drivername = 'mysql+asyncmy' if db_config.type == DatabaseType.MYSQL else 'postgresql+asyncpg'
        url = URL.create(
            drivername=drivername,
            username=db_config.username,
            password=db_config.password,
            host=db_config.host,
            port=db_config.port,
            database=db_config.database,
        )
        if db_config.type == DatabaseType.MYSQL:
            url = url.update_query_dict({'charset': settings.DATABASE_CHARSET})
        return url

    @staticmethod
    def _query_returns_rows(query: str, execution_result: Any) -> bool:
        description = getattr(execution_result, "description", None)
        if description is not None:
            return True

        returns_rows = getattr(execution_result, 'returns_rows', None)
        if returns_rows is not None:
            return bool(returns_rows)

        normalized_query = query.strip().lower()
        return normalized_query.startswith(("select", "with", "show", "describe", "desc", "explain")) or " returning " in normalized_query

    @staticmethod
    def _build_validation_payload(result: SQLResult) -> Dict[str, Any]:
        payload: Any = result.data
        if isinstance(result.data, list) and len(result.data) == 1:
            payload = result.data[0]

        return {
            "json": payload,
            "body": result.data,
            "data": result.data,
            "affected_rows": result.affected_rows,
        }

    @staticmethod
    def _apply_validations(sql_query: SQLQuery, result: SQLResult) -> None:
        if not sql_query.validations:
            return

        validation_payload = SQLExecutor._build_validation_payload(result)
        validation_results = []
        failed_messages = []

        for validation in sql_query.validations:
            assertion = Assertion(**validation)
            assertion_result = AssertionEngine.execute_assertion(assertion, validation_payload)
            validation_results.append(assertion_result.model_dump())
            if not assertion_result.success:
                failed_messages.append(assertion_result.message or "SQL断言失败")

        result.validation_results = validation_results
        if failed_messages:
            result.success = False
            result.error = "; ".join(failed_messages)

    @staticmethod
    async def _execute_async_query(sql_query: SQLQuery, db_config: DBConfig, result: SQLResult) -> SQLResult:
        engine = create_database_async_engine(SQLExecutor._build_async_database_url(db_config))
        try:
            async with engine.begin() as connection:
                execution_result = await connection.execute(text(sql_query.query))
                if SQLExecutor._query_returns_rows(sql_query.query, execution_result):
                    rows = execution_result.mappings().all()
                    result.data = [dict(row) for row in rows]
                    result.affected_rows = len(result.data)
                else:
                    result.affected_rows = execution_result.rowcount
            result.success = True

            if sql_query.extract and result.data:
                result.extracted_variables = SQLExecutor._extract_variables(sql_query.extract, result.data)

            return result
        finally:
            await engine.dispose()

    @staticmethod
    async def _execute_mysql_query(sql_query: SQLQuery, db_config: DBConfig, result: SQLResult) -> SQLResult:
        connection = None
        cursor = None

        try:
            connection = pymysql.connect(
                host=db_config.host,
                port=db_config.port,
                user=db_config.username,
                password=db_config.password,
                database=db_config.database,
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
            )
            cursor = connection.cursor()

            affected_rows = cursor.execute(sql_query.query)
            result.affected_rows = affected_rows

            if SQLExecutor._query_returns_rows(sql_query.query, cursor):
                data = cursor.fetchall()
                result.data = [dict(row) for row in data]

            connection.commit()
            result.success = True

            if sql_query.extract and result.data:
                result.extracted_variables = SQLExecutor._extract_variables(sql_query.extract, result.data)

            return result
        except Exception:
            if connection:
                connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    @staticmethod
    async def _execute_postgresql_query(sql_query: SQLQuery, db_config: DBConfig, result: SQLResult) -> SQLResult:
        connection = None
        cursor = None

        try:
            conn_str = f"postgresql://{db_config.username}:{db_config.password}@{db_config.host}:{db_config.port}/{db_config.database}"
            connection = psycopg.connect(conn_str)
            cursor = connection.cursor(row_factory=psycopg.rows.dict_row)
            cursor.execute(sql_query.query)

            if SQLExecutor._query_returns_rows(sql_query.query, cursor):
                data = cursor.fetchall()
                result.data = [dict(row) for row in data]
                result.affected_rows = len(data)
            else:
                result.affected_rows = cursor.rowcount

            connection.commit()
            result.success = True

            if sql_query.extract and result.data:
                result.extracted_variables = SQLExecutor._extract_variables(sql_query.extract, result.data)

            return result
        except Exception:
            if connection:
                connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    @staticmethod
    def _extract_variables(extract_config: Dict[str, str], data: List[Dict[str, Any]]) -> Dict[str, Any]:
        variables = {}

        for var_name, expr in extract_config.items():
            parts = expr.split('.')

            try:
                if len(parts) >= 2:
                    row_idx = int(parts[0])
                    if row_idx < len(data):
                        field = '.'.join(parts[1:])
                        if field in data[row_idx]:
                            variables[var_name] = data[row_idx][field]
            except (ValueError, IndexError):
                pass

        return variables
