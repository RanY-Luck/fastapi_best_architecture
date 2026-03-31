# API Testing Async SQL Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move `api_testing` SQL execution onto background tasks so long-running queries do not block the request/页面, and expose task status/results for report rendering.

**Architecture:** Add a dedicated async SQL task record for `api_testing`, submit SQL work through Celery, execute SQL with async database drivers in the worker, and read task status/result through new query APIs. The request API returns immediately with a task id; the frontend/report layer polls task status until completion and then renders persisted results.

**Tech Stack:** FastAPI, SQLAlchemy async ORM, Celery, Redis broker/result backend, async MySQL/PostgreSQL drivers, pytest

---

### File Map

**Create:**
- `backend/plugin/api_testing/service/sql_task_service.py` - persistence/query helpers for async SQL task records
- `backend/app/task/tasks/api_testing_sql/tasks.py` - Celery tasks for SQL execution
- `backend/plugin/api_testing/tests/test_sql_async_api.py` - API regression tests for submit/status/result flow
- `backend/plugin/api_testing/tests/test_sql_task_service.py` - service-level persistence/status tests

**Modify:**
- `backend/plugin/api_testing/model/models.py` - add async SQL task model
- `backend/plugin/api_testing/schema/request.py` - add async SQL task request/response schemas
- `backend/plugin/api_testing/api/v1/sql.py` - change execute endpoints to submit tasks and add status endpoint
- `backend/plugin/api_testing/utils/sql_executor.py` - add true async execution path for worker-side SQL queries
- `backend/app/task/tasks/__init__.py` or Celery task registration entry - register api_testing SQL tasks
- `backend/plugin/api_testing/api/v1/report.py` or related report query layer - surface SQL task status/result if report page needs it directly
- `backend/plugin/api_testing/sql/mysql/*.sql` and `backend/plugin/api_testing/sql/postgresql/*.sql` - migration/init for new async SQL task table if plugin manages its own schema

**Check for reuse:**
- `backend/app/task/celery.py`
- `backend/app/task/tasks/tasks.py`
- `backend/plugin/ai_assistant/service/chat_service.py`
- `backend/plugin/api_testing/service/test_report_service.py`

### Task 1: Define Async SQL Task Persistence

**Files:**
- Modify: `backend/plugin/api_testing/model/models.py`
- Modify: `backend/plugin/api_testing/schema/request.py`
- Test: `backend/plugin/api_testing/tests/test_sql_task_service.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_create_sql_task_defaults_to_pending():
    task = await SqlTaskService.create_task(query_payload)
    assert task.status == "pending"
    assert task.result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/plugin/api_testing/tests/test_sql_task_service.py -q`
Expected: FAIL because async SQL task model/service does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Add a new `ApiSqlExecutionTask` model with fields:
- `task_id`/Celery id
- `name`
- `status`
- `query_payload`
- `result`
- `error`
- `start_time`
- `end_time`
- `duration`

Add request/response schemas for submit/status payloads.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/plugin/api_testing/tests/test_sql_task_service.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/plugin/api_testing/model/models.py backend/plugin/api_testing/schema/request.py backend/plugin/api_testing/tests/test_sql_task_service.py
 git commit -m "feat: add api testing sql task model"
```

### Task 2: Add SQL Task Service

**Files:**
- Create: `backend/plugin/api_testing/service/sql_task_service.py`
- Test: `backend/plugin/api_testing/tests/test_sql_task_service.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_mark_sql_task_running_and_complete():
    task = await SqlTaskService.create_task(payload)
    await SqlTaskService.mark_running(task.id)
    await SqlTaskService.mark_completed(task.id, result={"success": True})
    refreshed = await SqlTaskService.get_by_task_id(task.task_id)
    assert refreshed.status == "success"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/plugin/api_testing/tests/test_sql_task_service.py -q`
Expected: FAIL because service methods are missing.

- [ ] **Step 3: Write minimal implementation**

Implement CRUD/status helpers:
- `create_task()`
- `get_by_task_id()`
- `mark_running()`
- `mark_completed()`
- `mark_failed()`

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/plugin/api_testing/tests/test_sql_task_service.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/plugin/api_testing/service/sql_task_service.py backend/plugin/api_testing/tests/test_sql_task_service.py
 git commit -m "feat: add api testing sql task service"
```

### Task 3: Add Worker-Side Async SQL Execution

**Files:**
- Modify: `backend/plugin/api_testing/utils/sql_executor.py`
- Create: `backend/app/task/tasks/api_testing_sql/tasks.py`
- Test: `backend/plugin/api_testing/tests/test_sql_executor.py`

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.anyio
async def test_execute_query_async_returns_sql_result():
    result = await SQLExecutor.execute_query_async(sql_query)
    assert result.success is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/plugin/api_testing/tests/test_sql_executor.py -q`
Expected: FAIL because async execution entrypoint does not exist.

- [ ] **Step 3: Write minimal implementation**

Add:
- `execute_query_async()` using async drivers or SQLAlchemy async engine
- Celery task that loads task record, marks running, executes SQL, stores result/error
- registration so worker discovers the new task

Keep validation/extraction behavior aligned with existing `SQLExecutor` result format.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/plugin/api_testing/tests/test_sql_executor.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/plugin/api_testing/utils/sql_executor.py backend/app/task/tasks/api_testing_sql/tasks.py backend/plugin/api_testing/tests/test_sql_executor.py
 git commit -m "feat: run api testing sql in celery worker"
```

### Task 4: Convert SQL API To Submit-And-Poll

**Files:**
- Modify: `backend/plugin/api_testing/api/v1/sql.py`
- Modify: `backend/plugin/api_testing/schema/request.py`
- Test: `backend/plugin/api_testing/tests/test_sql_async_api.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_execute_sql_query_returns_task_id(client):
    response = await client.post("/api/v1/api_testing/sql/execute", json=payload)
    assert response.json()["data"]["status"] == "pending"
    assert response.json()["data"]["task_id"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/plugin/api_testing/tests/test_sql_async_api.py -q`
Expected: FAIL because endpoint still executes inline.

- [ ] **Step 3: Write minimal implementation**

Change `/execute` and `/batch-execute` to:
- persist task(s)
- enqueue Celery task(s)
- return lightweight task metadata immediately

Add `GET /api_testing/sql/tasks/{task_id}` for polling.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/plugin/api_testing/tests/test_sql_async_api.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/plugin/api_testing/api/v1/sql.py backend/plugin/api_testing/schema/request.py backend/plugin/api_testing/tests/test_sql_async_api.py
 git commit -m "feat: submit api testing sql as background tasks"
```

### Task 5: Surface Results For Report Rendering

**Files:**
- Modify: `backend/plugin/api_testing/api/v1/report.py` or report-facing query layer
- Modify: `backend/plugin/api_testing/service/test_report_service.py`
- Test: `backend/plugin/api_testing/tests/test_sql_async_api.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_sql_task_status_endpoint_returns_completed_result(client):
    response = await client.get(f"/api/v1/api_testing/sql/tasks/{task_id}")
    assert response.json()["data"]["result"]["success"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/plugin/api_testing/tests/test_sql_async_api.py -q`
Expected: FAIL because completed result is not exposed.

- [ ] **Step 3: Write minimal implementation**

Return report-friendly payload:
- `status`
- `result`
- `error`
- `duration`
- timestamps

If existing report endpoint already aggregates SQL data, wire task result in there without changing unrelated report structure.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/plugin/api_testing/tests/test_sql_async_api.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/plugin/api_testing/api/v1/report.py backend/plugin/api_testing/service/test_report_service.py backend/plugin/api_testing/tests/test_sql_async_api.py
 git commit -m "feat: expose api testing sql task results for reports"
```

### Task 6: Regression Verification

**Files:**
- Test: `backend/plugin/api_testing/tests/test_assertion_engine.py`
- Test: `backend/plugin/api_testing/tests/test_sql_executor.py`
- Test: `backend/plugin/api_testing/tests/test_sql_task_service.py`
- Test: `backend/plugin/api_testing/tests/test_sql_async_api.py`

- [ ] **Step 1: Run focused regression suite**

Run: `pytest backend/plugin/api_testing/tests/test_assertion_engine.py backend/plugin/api_testing/tests/test_sql_executor.py backend/plugin/api_testing/tests/test_sql_task_service.py backend/plugin/api_testing/tests/test_sql_async_api.py -q`
Expected: PASS

- [ ] **Step 2: Run broader plugin regression suite**

Run: `pytest backend/plugin/api_testing/tests -q`
Expected: PASS

- [ ] **Step 3: Smoke-check worker registration**

Run: `python -c "from backend.app.task.celery import celery_app; print('backend.app.task.tasks.api_testing_sql.tasks.execute_api_testing_sql' in celery_app.tasks)"`
Expected: `True`

- [ ] **Step 4: Commit final verification updates**

```bash
git add backend/plugin/api_testing
git commit -m "test: cover async api testing sql execution"
```
