from types import SimpleNamespace

import pytest

from backend.plugin.api_testing.utils.sql_executor import (
    DBConfig,
    DatabaseType,
    SQLExecutor,
    SQLQuery,
)


@pytest.mark.anyio
async def test_execute_query_applies_sql_validations(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_execute_mysql_query(sql_query: SQLQuery, db_config: DBConfig, result):  # noqa: ANN001
        result.success = True
        result.data = [{"count": 2}]
        result.affected_rows = 1
        return result

    monkeypatch.setattr(SQLExecutor, "_execute_mysql_query", staticmethod(fake_execute_mysql_query))

    result = await SQLExecutor.execute_query(
        SQLQuery(
            name="count users",
            query="SELECT COUNT(*) AS count FROM users",
            validations=[
                {"source": "json", "type": "equals", "path": "$.count", "expected": 2},
            ],
            db_config=DBConfig(
                type=DatabaseType.MYSQL,
                host="localhost",
                port=3306,
                username="root",
                password="secret",
                database="test",
            ),
            use_default_db=False,
        )
    )

    assert result.success is True


@pytest.mark.anyio
async def test_execute_query_marks_failed_when_sql_validation_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_execute_mysql_query(sql_query: SQLQuery, db_config: DBConfig, result):  # noqa: ANN001
        result.success = True
        result.data = [{"count": 1}]
        result.affected_rows = 1
        return result

    monkeypatch.setattr(SQLExecutor, "_execute_mysql_query", staticmethod(fake_execute_mysql_query))

    result = await SQLExecutor.execute_query(
        SQLQuery(
            name="count users",
            query="SELECT COUNT(*) AS count FROM users",
            validations=[
                {"source": "json", "type": "equals", "path": "$.count", "expected": 2, "message": "count check"},
            ],
            db_config=DBConfig(
                type=DatabaseType.MYSQL,
                host="localhost",
                port=3306,
                username="root",
                password="secret",
                database="test",
            ),
            use_default_db=False,
        )
    )

    assert result.success is False
    assert result.error is not None
    assert "count check" in result.error


@pytest.mark.anyio
async def test_execute_query_async_uses_async_execution_path(monkeypatch: pytest.MonkeyPatch) -> None:
    observed = {}

    async def fake_async_execute(sql_query: SQLQuery, db_config: DBConfig, result):  # noqa: ANN001
        observed["query"] = sql_query.query
        observed["db_type"] = db_config.type
        result.success = True
        result.data = [{"id": 1}]
        result.affected_rows = 1
        return result

    monkeypatch.setattr(SQLExecutor, "_execute_async_query", staticmethod(fake_async_execute))

    result = await SQLExecutor.execute_query_async(
        SQLQuery(
            name="users",
            query="SELECT 1 AS id",
            db_config=DBConfig(
                type=DatabaseType.MYSQL,
                host="localhost",
                port=3306,
                username="root",
                password="secret",
                database="test",
            ),
            use_default_db=False,
        )
    )

    assert result.success is True
    assert result.data == [{"id": 1}]
    assert observed == {"query": "SELECT 1 AS id", "db_type": DatabaseType.MYSQL}


def test_query_with_returning_is_treated_as_result_set() -> None:
    cursor = SimpleNamespace(description=(("id",),), rowcount=1)

    assert SQLExecutor._query_returns_rows("INSERT INTO demo(name) VALUES ('a') RETURNING id", cursor) is True


def test_query_with_cte_is_treated_as_result_set() -> None:
    cursor = SimpleNamespace(description=(("id",),), rowcount=1)

    assert SQLExecutor._query_returns_rows("WITH data AS (SELECT 1 AS id) SELECT id FROM data", cursor) is True
