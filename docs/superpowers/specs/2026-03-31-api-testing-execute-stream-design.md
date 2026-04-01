# API Testing Execute Stream Design

## Goal

为 API Testing 测试用例执行增加实时运行日志能力，在不破坏现有 `POST /v1/api_testing/test_cases/{case_id}/execute` 行为的前提下，新增一个基于 HTTP 流的执行接口，供前端在“运行日志”页签中边执行边展示结构化日志。

本次只解决单用例执行时的实时日志问题，不扩展到测试集合、批量执行、断线重连、历史回放或服务端日志落盘。

## Scope

### In Scope

- 保留现有同步执行接口 `POST /{case_id}/execute`
- 新增流式执行接口 `POST /{case_id}/execute/stream`
- 响应类型为 `application/x-ndjson`
- 每条日志按一行 JSON 输出，前端通过 `fetch` 流式消费
- 将现有执行逻辑抽为共享执行器，避免 `/execute` 与 `/execute/stream` 双份实现
- 在关键执行节点输出结构化运行事件
- 保持现有报告生成能力，流式执行结束后仍生成报告并返回 `report_id`

### Out of Scope

- Socket.IO 或 SSE 方案
- 批量执行、测试集合执行的实时流
- 前端 UI 细节与样式实现
- 流式断点续传、重放、任务持久化订阅
- 将运行日志写入后端文件日志

## Existing Context

当前单用例执行入口在 `backend/plugin/api_testing/api/v1/test_case.py` 的 `POST /{case_id}/execute`，核心逻辑位于 `backend/plugin/api_testing/service/test_case_execution_service.py`。

现状问题：

- 执行逻辑是同步聚合式，只有全部步骤结束后才返回最终结果
- 步骤内部已经有请求、断言、SQL、变量提取等阶段性信息，但没有统一的事件输出接口
- 如果直接为流接口复制一份执行代码，会造成逻辑漂移，后续修复和扩展成本高

## Recommended Approach

采用“共享执行器 + 双消费端”的方案：

1. 将现有 `execute_test_case()` 重构为基于 async generator 的共享执行核心
2. 共享执行核心在执行过程中持续产出结构化事件，并在内部累计最终报告数据
3. 现有 `/execute` 接口消费全部事件，但只返回最终汇总结果
4. 新增 `/execute/stream` 接口消费同一执行核心，将事件按 NDJSON 逐行输出

推荐该方案的原因：

- 不破坏现有接口和调用方
- 流接口和普通接口共享同一条执行路径，减少行为不一致风险
- 事件模型可被前端直接消费，也可复用于未来批量执行流式化

不采用“复制现有逻辑快速实现流接口”的原因：

- 两份执行路径会很快失去同步
- 每次修复断言、SQL、变量提取行为都要修改两处
- 测试成本翻倍，回归风险明显更高

## API Contract

### Existing Endpoint

保留：

- `POST /v1/api_testing/test_cases/{case_id}/execute`

行为保持不变：

- 执行完成后返回汇总结果
- 返回体结构尽量与当前保持兼容

### New Endpoint

新增：

- `POST /v1/api_testing/test_cases/{case_id}/execute/stream`

查询参数：

- `environment_id`：可选，含义与现有 `/execute` 一致

响应头：

- `Content-Type: application/x-ndjson`
- `Cache-Control: no-cache`
- `X-Accel-Buffering: no`

响应体：

- 每行一个 JSON 事件对象
- 每行以 `\n` 结尾

## Event Model

所有事件包含以下公共字段：

- `type`: 事件类型
- `timestamp`: ISO8601 时间戳
- `case_id`: 测试用例 ID
- `environment_id`: 环境 ID，可为 `null`

### `run_start`

表示整次执行开始。

字段：

- `test_case_name`
- `environment_name`
- `total_steps`

### `step_start`

表示某步骤开始执行。

字段：

- `step_order`
- `step_name`
- `method`
- `url`
- `message`

### `step_request`

表示步骤请求参数已解析完成并准备发出。

字段：

- `step_order`
- `step_name`
- `request`

说明：

- `request` 使用已变量替换后的最终请求数据
- 内容沿用现有结果结构，避免前后端维护两套字段语义

### `step_response`

表示收到响应或请求层返回错误。

字段：

- `step_order`
- `step_name`
- `status_code`
- `elapsed_time`
- `success`
- `message`

### `step_assertion`

表示单条断言执行结果。

字段：

- `step_order`
- `step_name`
- `assertion`
- `success`
- `actual`
- `message`

### `step_sql`

表示单条 SQL 执行结果。

字段：

- `step_order`
- `step_name`
- `sql_name`
- `success`
- `message`
- `extracted_variables`

### `step_extract`

表示变量提取结果。

字段：

- `step_order`
- `step_name`
- `variable_name`
- `success`
- `value`
- `message`

### `step_end`

表示步骤结束。

字段：

- `step_order`
- `step_name`
- `success`
- `duration`
- `message`

### `run_end`

表示整个执行流程正常结束。

字段：

- `success`
- `report_id`
- `report_name`
- `total_steps`
- `success_steps`
- `fail_steps`
- `duration`
- `start_time`
- `end_time`
- `details`

说明：

- `details` 保持与当前 `/execute` 返回的详细结果结构一致，便于前端在流结束后直接复用现有结果区

### `error`

表示未能继续执行的全局错误。

字段：

- `message`
- `error_type`

说明：

- 如果出现全局错误，流中应先输出 `error`，随后结束响应
- 对于可归属到具体步骤的错误，优先通过 `step_response` 或 `step_end` 体现，不额外升级为全局 `error`

## Execution Architecture

### Shared Core

新增一个共享执行核心，例如：

- `stream_execute_test_case(...) -> AsyncIterator[dict[str, Any]]`

职责：

- 加载用例、项目、环境、步骤
- 逐步执行测试步骤
- 在关键节点 `yield` 结构化事件
- 累计 `step_results`、统计信息和最终报告数据
- 在结束时返回生成报告所需的完整上下文

这里的“返回”不要求 Python 生成器显式 `return` 结果给调用方；实现上可以通过包装对象、上下文收集器或专门的 runner 对象同时承载“事件输出”和“最终汇总”。

### Sync Consumer

现有 `/execute` 作为同步消费者：

- 运行共享执行核心
- 不向客户端输出中间事件
- 仅在完成后返回最终汇总结果

### Stream Consumer

新 `/execute/stream` 作为流消费者：

- 使用 `StreamingResponse`
- 消费共享执行核心产出的事件
- 每个事件序列化为一行 NDJSON 后 `yield`
- 执行完成后输出最终 `run_end` 事件并结束响应

## Data Flow

### Happy Path

1. 前端调用 `POST /{case_id}/execute/stream`
2. 后端校验用例、项目、环境
3. 输出 `run_start`
4. 对每个步骤依次输出：
   - `step_start`
   - `step_request`
   - `step_response`
   - 若有断言，逐条输出 `step_assertion`
   - 若有 SQL，逐条输出 `step_sql`
   - 若有变量提取，逐条输出 `step_extract`
   - `step_end`
5. 保存测试报告
6. 输出 `run_end`
7. 关闭流

### Step Failure Path

如果单个步骤失败：

- 当前步骤仍输出 `step_response`、已执行的断言或 SQL 事件
- 必须输出 `step_end(success=false, ...)`
- 是否继续执行后续步骤，沿用当前同步执行逻辑的语义

当前同步实现会继续执行后续步骤，因此流式接口也必须保持一致。

### Global Failure Path

如果执行在步骤循环前或报告保存前发生不可恢复异常：

- 输出 `error`
- 流结束

如果报告保存失败但步骤已跑完：

- 输出 `error`
- 不输出伪造的 `run_end`

## Error Handling

错误处理原则：

- 与具体步骤强相关的错误，尽量落在步骤事件里
- 只有整次执行无法继续时才发送全局 `error`
- 流式输出时任何 JSON 序列化异常都视为全局错误并立即终止

边界情况：

- 用例不存在：直接输出单条 `error`
- 项目不存在：直接输出单条 `error`
- 显式指定但环境不存在：直接输出单条 `error`
- 没有可执行步骤：直接输出单条 `error`
- 客户端中途断开：服务端停止生成后续事件，不额外保证补偿

## Compatibility Rules

- 现有 `/execute` 的返回结构不得因流式化重构而发生破坏性变化
- 现有步骤执行、断言执行、SQL 执行、变量提取的业务语义不得改变
- 流式接口的 `run_end.details` 与现有 `/execute.details` 尽量保持相同结构
- 不要求旧前端理解新事件模型；只有新流接口的调用方消费这些事件

## Testing Strategy

实现前先补测试，覆盖以下行为：

### Stream API Tests

- `POST /{case_id}/execute/stream` 返回 `application/x-ndjson`
- 成功执行时事件顺序至少满足：
  `run_start -> step_start -> step_request -> step_response -> step_end -> run_end`
- 有断言时会产生 `step_assertion`
- 有 SQL 时会产生 `step_sql`
- 有变量提取时会产生 `step_extract`

### Failure Tests

- 用例不存在时返回 `error` 事件
- 步骤异常时仍会产生该步骤的 `step_end(success=false)`
- 报告创建失败时返回 `error` 且不输出 `run_end`

### Regression Tests

- 现有 `/execute` 返回结构保持兼容
- 流接口和普通接口对同一用例的最终统计结果一致
- 现有 `test_case_execution_service` 相关逻辑未因重构引入行为回归

## File Impact

预计主要修改：

- `backend/plugin/api_testing/api/v1/test_case.py`
- `backend/plugin/api_testing/service/test_case_execution_service.py`
- `backend/plugin/api_testing/tests/` 下新增或扩展流式执行测试

如为保持边界清晰，也可以新增一个专门承载流事件模型或执行 runner 的模块，但不应把相同执行逻辑复制到多个服务文件中。

## Open Decisions Resolved

以下关键设计已确认：

- 保留现有 `/execute`，新增 `/execute/stream`
- 流格式使用 `NDJSON`
- 前端通过 `fetch` 读取 HTTP 流
- 本次只做单用例执行流

## Implementation Readiness

该设计已经足够进入 implementation plan，原因如下：

- 接口边界明确
- 事件模型明确
- 兼容策略明确
- 错误语义明确
- 测试边界明确

规划阶段不需要再补充前端视觉细节或未来扩展方案。
