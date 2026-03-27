# AI Assistant Agent 集成说明

## 1. 目标

当前 `ai_assistant` 已从“固定 action 分发器”演进到“可接入 LangChain tool-calling 的 Agent 壳子”。

这套实现的目标不是推翻原有插件结构，而是在保留以下既有能力的前提下，引入更自然的 AI 调用链路：

- FastAPI 接口入口
- 会话与消息持久化
- Celery 异步执行
- Socket.IO 运行状态推送
- Java API / Data Assistant / Browser Service 等既有执行器

当前首个落地工具是：

- `query_device_reports`

它用于查询设备上报记录，适配真实接口：

- `/api/admin/packetInfo/pageList`

---

## 2. 当前架构

### 2.1 主要入口

#### Chat API
- 文件：`backend/plugin/ai_assistant/api/v1/chat.py:41`
- 接口：`POST /messages`

#### 聊天主编排
- 文件：`backend/plugin/ai_assistant/service/chat_service.py:43`
- 作用：
  - 读取用户消息
  - 创建或获取会话
  - 写入 user message
  - 决定走 Agent 还是旧 Router
  - 创建异步 `AiActionRun`
  - 投递 Celery 任务

### 2.2 异步任务入口
- 文件：`backend/app/task/tasks/ai_assistant/tasks.py:15`
- 作用：
  - 接收 `route_type`
  - 发 started / progress / completed / failed 事件
  - 调用 `AgentService` / `DataAssistantService` / `BrowserService`

### 2.3 Agent 主脑
- 文件：`backend/plugin/ai_assistant/service/agent_service.py:9`
- 当前职责：
  - 根据 rollout 和配置判断是否启用 Agent
  - 兼容显式 `action_name`
  - 构造 LangChain tools
  - 调用 LLM 进行 tool-calling
  - 执行工具
  - 对工具结果做二次自然语言总结

### 2.4 LLM Provider 抽象层
- 文件：`backend/plugin/ai_assistant/service/llm_provider_service.py:15`
- 当前职责：
  - 统一初始化 `ChatOpenAI`
  - 统一构造消息
  - 统一执行普通 `ainvoke`
  - 统一执行 `bind_tools(...).ainvoke(...)`
  - 在 LangChain 依赖缺失时优雅降级

### 2.5 Tool Registry
- 文件：`backend/plugin/ai_assistant/service/tool_registry.py:18`
- 当前职责：
  - 注册可用 Agent 工具
  - 维护工具描述与输入 schema
  - 为 LangChain 动态生成 `StructuredTool`

### 2.6 首个工具执行器
- 文件：`backend/plugin/ai_assistant/service/data_assistant_service.py:21`
- 工具：`query_device_reports`
- 底层真实请求执行：
  - `backend/plugin/ai_assistant/service/java_api_service.py`

---

## 3. 当前调用链路

## 3.1 显式工具调用路径

当前 `.env` 默认已切到：

```env
AI_ASSISTANT_AGENT_ROLLOUT_MODE='agent_forced_for_explicit_tools'
```

因此，只要请求里显式传：

- `action_name='query_device_reports'`

就会直接进入 Agent 路径。

链路如下：

1. 前端/调用方请求 `POST /messages`
2. `ChatService.send_message()` 写入 user message
3. `AgentService.should_use_agent(...)` 返回 `True`
4. `AgentService.build_agent_route_plan(...)` 生成：
   - `route_type='agent'`
   - `target_name='query_device_reports'`
5. Celery 执行 `execute_ai_assistant_run()`
6. `AgentService.execute_run()` 执行工具
7. 若 LLM 已启用：
   - 对工具结果做自然语言总结
8. 写回 assistant message 与 action run 结果

## 3.2 自然语言自动选工具路径

当满足以下条件时，系统可走更接近普通 AI 的工具选择：

1. `AI_ASSISTANT_LLM_ENABLED=true`
2. `AI_ASSISTANT_LLM_API_KEY` 已配置
3. rollout 使用：
   - `agent_primary`
   - 或允许自动走 Agent 的其他模式

链路如下：

1. 用户自然语言输入，例如：
   - “帮我查 IMEI BD02240906400445 最近 20 条设备上报记录”
2. `ChatService` 将消息投递到 `route_type='agent'`
3. `AgentService.execute_run()` 构造 LangChain tools
4. `LLMProviderService.ainvoke_with_tools(...)` 调用已绑定工具的模型
5. 模型返回 `tool_calls`
6. `AgentService` 执行第一个工具调用
7. 再用 LLM 将工具结果整理成中文结论

---

## 4. 已实现的配置项

配置定义位置：`backend/core/conf.py:170`

### Java API 相关

```env
AI_ASSISTANT_JAVA_API_BASE_URL='https://www.beidoulab.club:5557'
AI_ASSISTANT_JAVA_API_PROFILE_PATH='/api/admin/user/v2/front/info'
AI_ASSISTANT_JAVA_API_DEVICE_REPORTS_PATH='/api/admin/packetInfo/pageList'
AI_ASSISTANT_JAVA_API_AUTHORIZATION='Bearer ...'
AI_ASSISTANT_JAVA_API_HEADERS='{"Accept":"*/*","User-Agent":"Apifox/1.0.0 (https://apifox.com)","Cache-Control":"no-cache","Connection":"keep-alive"}'
```

### LLM / Agent 相关

这些依赖现在应放在插件自己的依赖文件中：

- `backend/plugin/ai_assistant/requirements.txt`

当前内容：

```txt
langchain>=0.3.27
langchain-core>=0.3.79
langchain-openai>=0.3.35
```

对应运行时配置示例：

```env
AI_ASSISTANT_LLM_ENABLED=false
AI_ASSISTANT_LLM_PROVIDER='openai'
AI_ASSISTANT_LLM_MODEL='gpt-4o-mini'
AI_ASSISTANT_LLM_API_KEY=''
AI_ASSISTANT_LLM_BASE_URL=''
AI_ASSISTANT_LLM_TIMEOUT=30
AI_ASSISTANT_AGENT_MAX_STEPS=2
AI_ASSISTANT_AGENT_TOOL_TIMEOUT=30
AI_ASSISTANT_AGENT_ENABLED_TOOLS='["query_device_reports"]'
AI_ASSISTANT_AGENT_ROLLOUT_MODE='agent_forced_for_explicit_tools'
```

---

## 5. rollout 模式说明

定义位置：`backend/core/conf.py:192`

### `legacy_router`
完全走旧路由器，不走 Agent。

适用场景：
- 需要快速回退
- LLM 尚未配置
- 只想保留旧版行为

### `agent_shadow`
当前代码里仍偏保守，主要用于后续扩展观察模式。

适用场景：
- 后续要做 shadow 执行、对比日志时

### `agent_forced_for_explicit_tools`
当前推荐的测试模式。

特点：
- 用户自然语言默认仍可走旧逻辑
- 只要显式传 `action_name`，强制进入 Agent 路径
- 风险最小，便于联调

### `agent_primary`
当前最接近“普通 AI”模式。

特点：
- 普通自然语言优先进入 Agent
- 由模型决定是否调用工具
- 需要 LLM 可用

---

## 6. 当前工具注册说明

文件：`backend/plugin/ai_assistant/service/tool_registry.py:38`

当前只注册了一个工具：

### `query_device_reports`
描述：
- 查询设备上报记录，适用于按 IMEI、时间范围、groupId、分页条件查询设备上报数据。

当前 schema：

- `imei` 必填
- `startTime` 可选
- `endTime` 可选
- `groupId` 可选
- `page` 可选
- `limit` 可选

该工具最终调用：
- `DataAssistantService.execute_action(action_name='query_device_reports', ...)`

---

## 7. 关键代码说明

## 7.1 Agent 是否启用
位置：`backend/plugin/ai_assistant/service/agent_service.py:55`

```python
def should_use_agent(cls, *, action_name: str | None, content: str) -> bool:
```

逻辑要点：
- `legacy_router` 时直接禁用 Agent
- LLM 未启用时也不自动走 Agent
- 显式 `action_name` 在强制模式下可直接进入 Agent
- `agent_primary` 下自然语言也可进入 Agent

## 7.2 Agent 路由计划
位置：`backend/plugin/ai_assistant/service/agent_service.py:66`

```python
def build_agent_route(...)
def build_agent_route_plan(...)
```

作用：
- 生成统一的 `ChatRoutePlan`
- 替代 `ChatService` 里临时 `type('RoutePlan', ...)` 写法

## 7.3 LangChain tool 构建
位置：`backend/plugin/ai_assistant/service/tool_registry.py:74`

```python
def build_langchain_tools(...)
```

作用：
- 把内部 `AssistantTool` 转成 `StructuredTool`
- 基于 `input_schema` 生成 `args_schema`
- 便于模型输出标准工具参数

## 7.4 LLM 绑定工具调用
位置：`backend/plugin/ai_assistant/service/llm_provider_service.py:33`

```python
def bind_tools(...)
async def ainvoke_with_tools(...)
```

作用：
- 创建带工具绑定的模型
- 执行一次 tool-calling

## 7.5 Agent 执行主流程
位置：`backend/plugin/ai_assistant/service/agent_service.py:76`

```python
async def execute_run(...)
```

当前分两种分支：

### 分支 A：显式工具
- 若 `action_name` 存在并且已注册
- 直接执行该工具
- 若 LLM 可用，再对结果做总结

### 分支 B：自然语言工具选择
- 构造 LangChain tools
- 调用 `ainvoke_with_tools(...)`
- 读取返回的 `tool_calls`
- 执行第一个工具
- 对结果做总结

---

## 8. 测试方式

## 8.1 最小可测方案：显式 action_name

这是当前最稳妥的测试方法，因为不要求先把整个自然语言 Agent 全部打开。

请求示例：

```bash
curl --location 'http://127.0.0.1:8000/api/v1/ai-assistant/messages' \
--header 'Authorization: Bearer <你的平台JWT>' \
--header 'Content-Type: application/json' \
--data '{
  "content": "帮我查设备上报记录",
  "action_name": "query_device_reports",
  "action_params": {
    "imei": "BD02240906400445",
    "startTime": "2026-03-20 00:00:00",
    "endTime": "2026-03-26 23:59:59",
    "groupId": "1484",
    "page": "1",
    "limit": "20"
  }
}'
```

预期结果：
- 返回 `accepted=true`
- 返回一个 `action_run`
- `route_type='agent'`
- 后续可通过历史消息看到 assistant 回写结果

## 8.2 自然语言自动调用工具测试

先修改 `.env`：

```env
AI_ASSISTANT_LLM_ENABLED=true
AI_ASSISTANT_LLM_API_KEY='你的key'
AI_ASSISTANT_AGENT_ROLLOUT_MODE='agent_primary'
```

然后发自然语言请求：

```bash
curl --location 'http://127.0.0.1:8000/api/v1/ai-assistant/messages' \
--header 'Authorization: Bearer <你的平台JWT>' \
--header 'Content-Type: application/json' \
--data '{
  "content": "帮我查 IMEI BD02240906400445 最近 20 条设备上报记录，groupId 1484，时间范围 2026-03-20 到 2026-03-26"
}'
```

预期结果：
- 命中 Agent 路径
- 模型产生 `query_device_reports` 的 tool call
- 工具执行成功
- assistant 返回中文总结，而不是原始 JSON

## 8.3 查询历史消息

接口位置：`backend/plugin/ai_assistant/api/v1/chat.py:30`

```bash
curl --location 'http://127.0.0.1:8000/api/v1/ai-assistant/conversations/<conversation_id>' \
--header 'Authorization: Bearer <你的平台JWT>'
```

可以查看：
- user message
- assistant message
- action 状态

---

## 9. 当前限制

### 9.1 目前只支持单工具样板
当前仅实现：
- `query_device_reports`

还没有扩展：
- `open_dashboard`
- `query_user_profile`
- 其他 Java API 工具

### 9.2 当前只执行第一个 tool call
在 `backend/plugin/ai_assistant/service/agent_service.py:128`
当前只取：
- `tool_calls[0]`

这意味着：
- 还不是多步 ReAct / LangGraph agent
- 当前是单步 tool-calling MVP

### 9.3 暂未把 conversation history 送进 Agent 推理
当前 `execute_run()` 中传给模型的上下文仍主要是当前用户消息，尚未接入完整会话历史。

### 9.4 rollout 仍然保守
当前 `.env` 默认是：

```env
AI_ASSISTANT_AGENT_ROLLOUT_MODE='agent_forced_for_explicit_tools'
```

这意味着：
- 方便测试
- 但默认还不是“所有自然语言都像普通 AI 那样优先走 Agent”

### 9.5 LLM 默认未启用
当前 `.env` 中：

```env
AI_ASSISTANT_LLM_ENABLED=false
AI_ASSISTANT_LLM_API_KEY=''
```

因此：
- 代码链路存在
- 但不开 key 时无法做真实模型工具选择

---

## 10. 已完成事项

### 已完成
- 增加 `route_type='agent'`
- 增加 LLM/Agent 配置项
- 新增 `AgentService`
- 新增 `LLMProviderService`
- 新增 `ToolRegistry`
- 为 `query_device_reports` 提供 LangChain `StructuredTool`
- Celery 支持 `agent` 路由
- `ChatService` 接入 Agent 路径
- 去掉 `ChatService` 中临时 route object，改为正式 `ChatRoutePlan`
- `.env` 已补齐 Agent 相关配置占位
- 默认 rollout 已切到 `agent_forced_for_explicit_tools`

### 已验证
- LangChain 依赖已安装
- 关键 agent 文件已编译通过
- `build_langchain_tools()` 能构造出 `query_device_reports`
- `build_agent_route()` 对显式动作和设备查询文本都可正确返回 agent 路由

---

## 11. 推荐下一步

### 阶段 1：联调显式 action_name
先保持：

```env
AI_ASSISTANT_AGENT_ROLLOUT_MODE='agent_forced_for_explicit_tools'
```

做法：
- 请求里显式传 `action_name='query_device_reports'`
- 验证 Celery、消息写回、Socket 事件、Java API 查询链路

### 阶段 2：打开自然语言 Agent
改成：

```env
AI_ASSISTANT_LLM_ENABLED=true
AI_ASSISTANT_LLM_API_KEY='你的key'
AI_ASSISTANT_AGENT_ROLLOUT_MODE='agent_primary'
```

做法：
- 用自然语言直接提问
- 验证模型是否真的返回 `tool_calls`
- 校正 prompt 和 schema

### 阶段 3：增强 Agent 能力
后续建议：
- 接入 conversation history
- 增加多工具支持
- 增加 tool timeout / step control 的实际执行限制
- 补充更细的 progress 事件
- 为工具结果增加更稳定的结构化摘要层

---

## 12. 相关文件索引

### 核心文件
- `backend/plugin/ai_assistant/api/v1/chat.py:41`
- `backend/plugin/ai_assistant/service/chat_service.py:43`
- `backend/plugin/ai_assistant/service/agent_service.py:9`
- `backend/plugin/ai_assistant/service/llm_provider_service.py:15`
- `backend/plugin/ai_assistant/service/tool_registry.py:18`
- `backend/plugin/ai_assistant/service/data_assistant_service.py:21`
- `backend/app/task/tasks/ai_assistant/tasks.py:15`
- `backend/core/conf.py:170`
- `backend/.env:26`

### 兼容层文件
- `backend/plugin/ai_assistant/service/router_service.py:5`
- `backend/plugin/ai_assistant/service/action_catalog.py`

---

## 13. 一句话总结

现在这套 AI 助手已经不是单纯的固定路由器了：

- 显式工具调用已经可以走 Agent 壳子
- 自然语言 tool-calling 的主链路已经接上
- 只差打开真实 LLM 配置，就可以继续做真正的 Agent 联调
