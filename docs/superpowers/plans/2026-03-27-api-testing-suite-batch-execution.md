# API Testing Suite Batch Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add lightweight test suites plus one-click project or suite batch execution with bounded built-in concurrency for the API testing plugin.

**Architecture:** Keep single-case step execution serial and extract it into a reusable service. Build a separate batch executor that resolves target cases from a project or suite, runs cases concurrently behind an `asyncio.Semaphore`, persists per-case reports with the existing report flow, and writes one aggregate batch report for the whole run.

**Tech Stack:** FastAPI, SQLAlchemy async ORM, Pydantic, pytest, asyncio

---

### Task 1: Add failing tests for batch execution orchestration

**Files:**
- Create: `backend/plugin/api_testing/tests/test_batch_execution_service.py`
- Test: `backend/plugin/api_testing/tests/test_batch_execution_service.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_run_cases_concurrently_and_build_summary():
    ...
    assert result['total_cases'] == 2
    assert result['success_cases'] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/plugin/api_testing/tests/test_batch_execution_service.py -v`
Expected: FAIL because batch execution service does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
class BatchExecutionService:
    async def execute_cases(...):
        ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/plugin/api_testing/tests/test_batch_execution_service.py -v`
Expected: PASS

### Task 2: Add failing tests for suite membership resolution

**Files:**
- Create: `backend/plugin/api_testing/tests/test_test_suite_service.py`
- Test: `backend/plugin/api_testing/tests/test_test_suite_service.py`

- [ ] **Step 1: Write the failing test**

```python
def test_normalize_suite_case_order_and_deduplicate_members():
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/plugin/api_testing/tests/test_test_suite_service.py -v`
Expected: FAIL because suite service/helpers do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def normalize_suite_case_ids(case_ids: list[int]) -> list[int]:
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/plugin/api_testing/tests/test_test_suite_service.py -v`
Expected: PASS

### Task 3: Add suite persistence and schema support

**Files:**
- Modify: `backend/plugin/api_testing/model/models.py`
- Modify: `backend/plugin/api_testing/schema/request.py`
- Create: `backend/plugin/api_testing/service/test_suite_service.py`
- Modify: `backend/plugin/api_testing/sql/postgresql/001_create_api_testing_tables.sql`
- Modify: `backend/plugin/api_testing/sql/mysql/001_create_api_testing_tables.sql`
- Modify: `backend/plugin/api_testing/sql/postgresql/init.sql`
- Modify: `backend/plugin/api_testing/sql/mysql/init.sql`
- Modify: `backend/plugin/api_testing/sql/postgresql/init_snowflake.sql`
- Modify: `backend/plugin/api_testing/sql/mysql/init_snowflake.sql`

- [ ] **Step 1: Implement suite entities and schemas**
- [ ] **Step 2: Add suite service helpers for CRUD and membership replacement**
- [ ] **Step 3: Update SQL bootstrap scripts for suite tables**
- [ ] **Step 4: Run targeted tests**

Run: `pytest backend/plugin/api_testing/tests/test_test_suite_service.py -v`
Expected: PASS

### Task 4: Extract reusable single-case execution service

**Files:**
- Create: `backend/plugin/api_testing/service/test_case_execution_service.py`
- Modify: `backend/plugin/api_testing/api/v1/test_case.py`

- [ ] **Step 1: Move existing single-case execution logic behind a service boundary**
- [ ] **Step 2: Preserve current single-case endpoint response contract**
- [ ] **Step 3: Reuse the service from preview execution**
- [ ] **Step 4: Run orchestration tests**

Run: `pytest backend/plugin/api_testing/tests/test_batch_execution_service.py -v`
Expected: PASS

### Task 5: Implement batch execution aggregate report model and service

**Files:**
- Modify: `backend/plugin/api_testing/model/models.py`
- Modify: `backend/plugin/api_testing/schema/request.py`
- Create: `backend/plugin/api_testing/service/test_batch_execution_service.py`
- Modify: `backend/plugin/api_testing/sql/postgresql/001_create_api_testing_tables.sql`
- Modify: `backend/plugin/api_testing/sql/mysql/001_create_api_testing_tables.sql`
- Modify: `backend/plugin/api_testing/sql/postgresql/init.sql`
- Modify: `backend/plugin/api_testing/sql/mysql/init.sql`
- Modify: `backend/plugin/api_testing/sql/postgresql/init_snowflake.sql`
- Modify: `backend/plugin/api_testing/sql/mysql/init_snowflake.sql`

- [ ] **Step 1: Add batch report persistence model**
- [ ] **Step 2: Implement bounded concurrency batch executor**
- [ ] **Step 3: Persist aggregate project/suite run result**
- [ ] **Step 4: Run orchestration tests**

Run: `pytest backend/plugin/api_testing/tests/test_batch_execution_service.py -v`
Expected: PASS

### Task 6: Expose suite and batch execution API endpoints

**Files:**
- Create: `backend/plugin/api_testing/api/v1/test_suite.py`
- Modify: `backend/plugin/api_testing/api/router.py`
- Modify: `backend/plugin/api_testing/README.md`
- Modify: `backend/plugin/api_testing/API_DOCUMENTATION.md`

- [ ] **Step 1: Add suite CRUD and membership endpoints**
- [ ] **Step 2: Add project batch execute and suite batch execute endpoints**
- [ ] **Step 3: Return aggregate run summary plus per-case report references**
- [ ] **Step 4: Update plugin docs for new endpoints**

### Task 7: Verify focused behavior end to end

**Files:**
- Test: `backend/plugin/api_testing/tests/test_batch_execution_service.py`
- Test: `backend/plugin/api_testing/tests/test_test_suite_service.py`

- [ ] **Step 1: Run focused plugin tests**

Run: `pytest backend/plugin/api_testing/tests/test_batch_execution_service.py backend/plugin/api_testing/tests/test_test_suite_service.py -v`
Expected: PASS

- [ ] **Step 2: Inspect results and only then report status**
