# 生产环境32问题修复 — 全面实施计划

## TL;DR

> **目标**: 修复测试汇总中全部32个问题，使Amazon自动化平台达到生产可用状态
> 
> **核心工作**:
> - 关键Bug修复（datetime时区、对话历史、关键词Agent）
> - 后端基础设施（DB用户表、OpenRouter集成、Mock数据层）
> - 前端重构（侧边栏8项、仪表盘增强、广告管理8-Tab赛狐ERP复刻、订单/退货/审批中心）
> - 部署（SSL证书 + HTTPS）
> 
> **交付物**:
> - 修复后的后端API（用户CRUD、OpenRouter、Mock数据端点、飞书AI聊天）
> - 全新前端页面（广告管理、订单、退货、审批中心、用户管理等）
> - 增强现有页面（仪表盘、广告仪表盘、登录、侧边栏、主题切换）
> - SSL + HTTPS生产部署
> 
> **预估规模**: XL（40+任务）
> **并行执行**: YES — 10波次
> **关键路径**: Bug修复 → 后端基础 → Mock数据 → 前端核心 → 各页面并行 → 部署 → 验证

---

## Context

### Original Request
用户测试生产环境后整理了32个问题文档（`2026.4.10测试错误汇总.md`），涵盖从域名SSL到广告管理页面的全方位问题。经过多轮逐项确认（含3组赛狐ERP截图参照），所有32个问题已完全明确。

### Interview Summary
**关键决策**:
- **数据架构**: Mock数据先行，SP-API管道后续阶段
- **广告管理**: 完整复刻赛狐ERP 8-Tab结构 + 两级钻取
- **LLM集成**: OpenRouter + 直连双模式，每Agent可配置
- **消息中心**: 不做独立页面，仅铃铛通知留位
- **退货**: 仅FBA退货Tab
- **用户角色**: boss + operator（暂不扩展）
- **时区**: 美国站=洛杉矶时间，暂不做多站点
- **审批中心历史Tab**: 替代原Agent Activity板块

**研究结论**:
- OpenRouter兼容OpenAI格式，LiteLLM原生支持
- Amazon SP-API数据延迟：订单30分钟，广告72小时校正
- Messaging API只能发不能收买家消息
- 现有前端无暗黑模式手动切换、无通知铃铛、无广告/订单/退货页面

### Metis Review
**已纳入的差距修补**:
- 共享DataTable组件提取为早期任务，解除后续页面并行阻塞
- 时区工具函数集中处理，避免各处重复
- OpenRouter feature flag机制
- 用户删除时JWT处理（添加token黑名单检查）
- Mock数据放专用目录，保持与未来真实API相同接口
- 广告管理页面占前端工作量60%+，需进一步拆分

---

## Work Objectives

### Core Objective
修复全部32个测试问题，使平台从"能打开"提升到"可日常使用"级别，所有页面有Mock数据支撑、功能可交互、UI完整。

### Concrete Deliverables
- 修复的后端：datetime时区修复、对话历史修复、关键词Agent修复
- 新增后端：users表 + CRUD API、OpenRouter集成、Mock数据API（仪表盘/广告/订单/退货）、飞书AI聊天
- 新增前端页面：广告管理(8-Tab+钻取)、全部订单、退货订单、审批中心、用户管理、Agent配置
- 增强前端：侧边栏重构、仪表盘(卡片+趋势图+SKU排名)、广告仪表盘(卡片+趋势图+排名)、登录页、主题切换、通知铃铛、返回按钮
- 部署：SSL证书 + HTTPS + 域名

### Definition of Done
- [ ] 所有32个Issue对应功能在生产环境可正常使用
- [ ] `curl -k https://siqiangshangwu.com/health` 返回200
- [ ] boss/op1/op2三个用户均可正常登录
- [ ] 仪表盘显示Mock数据卡片+趋势图+SKU排名
- [ ] 广告管理8个Tab均可浏览Mock数据
- [ ] 订单/退货页面显示Mock数据列表
- [ ] 审批中心审批+历史两个Tab正常工作
- [ ] AI Manager聊天功能正常回复
- [ ] 暗黑/明亮模式切换正常
- [ ] 通知铃铛显示待处理数量

### Must Have
- 所有Mock数据API与未来SP-API真实数据使用相同接口契约
- 用户管理基于数据库（非环境变量）
- OpenRouter集成不破坏现有OpenAI直连功能
- 广告管理表格支持排序、分页、汇总行
- 所有时间显示遵循洛杉矶时区

### Must NOT Have (Guardrails)
- ❌ 不实现真实SP-API数据管道（本期全部Mock）
- ❌ 不调用Amazon Ads API写入端点
- ❌ 不实现WebSocket实时通知（用轮询）
- ❌ 不实现买家消息收发
- ❌ 不做多站点适配
- ❌ 不修改`src/agents/base_agent.py`（24行抽象基类）
- ❌ 不修改现有`workflow.invoke()`调用
- ❌ 不添加未确认的第三方库（保持现有技术栈）
- ❌ 不实现毛利润/毛利率计算（字段留空）
- ❌ 不做广告管理的状态统计栏
- ❌ 不做FBM退货和买家之声Tab
- ❌ 不做独立消息中心页面
- ❌ 不过度添加JSDoc注释
- ❌ 不使用`as any`或`@ts-ignore`
- ❌ 不在生产代码中保留`console.log`

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (bun test via Vite, pytest for backend)
- **Automated tests**: Tests-after（关键后端API写测试，前端以QA scenarios为主）
- **Framework**: pytest (backend), bun test (frontend)

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Frontend/UI**: Use Playwright — Navigate, interact, assert DOM, screenshot
- **API/Backend**: Use Bash (curl) — Send requests, assert status + response fields
- **Bug fixes**: Use Bash — Run specific test commands, verify output

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 0 (Critical Bug Fixes — immediate, 3 parallel):
├── Task 1: datetime时区修复 [deep]
├── Task 2: 对话历史修复 [deep]
└── Task 3: 关键词Agent修复 [deep]

Wave 1 (Backend Foundations — after Wave 0, 6 parallel):
├── Task 4: users数据库表 + Alembic迁移 [deep]
├── Task 5: 用户CRUD API [unspecified-high]
├── Task 6: OpenRouter集成到LLM client [deep]
├── Task 7: Agent中文名DB存储 + API [unspecified-high]
├── Task 8: 时区工具函数库 [quick]
└── Task 9: 前端共享DataTable组件 [visual-engineering]

Wave 2 (Mock Data Layer — after Wave 1, 5 parallel):
├── Task 10: 仪表盘Mock数据API [unspecified-high]
├── Task 11: 广告Mock数据API [unspecified-high]
├── Task 12: 订单Mock数据API [unspecified-high]
├── Task 13: 退货Mock数据API [unspecified-high]
└── Task 14: 通知Mock数据API [quick]

Wave 3 (Frontend Core — after Wave 1, 6 parallel):
├── Task 15: 登录页增强 [visual-engineering]
├── Task 16: 暗黑/明亮模式切换 [visual-engineering]
├── Task 17: 侧边栏完全重构 [visual-engineering]
├── Task 18: 通知铃铛组件 [visual-engineering]
├── Task 19: 前端路由体系重建 [visual-engineering]
└── Task 20: 聊天页返回按钮 [quick]

Wave 4 (Dashboard Enhancement — after Wave 2+3, 3 parallel):
├── Task 21: 仪表盘卡片+时间切换 [visual-engineering]
├── Task 22: 仪表盘趋势图 [visual-engineering]
└── Task 23: SKU排名表格 [visual-engineering]

Wave 5 (Ad Dashboard Enhancement — after Wave 2+3, 3 parallel):
├── Task 24: 广告仪表盘卡片+时间 [visual-engineering]
├── Task 25: 广告趋势图+齿轮选择器 [visual-engineering]
└── Task 26: 广告Campaign排名 [visual-engineering]

Wave 6 (Ad Management — MASSIVE, after Wave 2+9, 5 parallel):
├── Task 27: 广告管理主框架+Portfolio树+Tab导航 [deep]
├── Task 28: 广告管理-广告组合+广告活动Tab [visual-engineering]
├── Task 29: 广告管理-广告组+广告产品Tab [visual-engineering]
├── Task 30: 广告管理-投放+搜索词+否定投放+日志Tab [visual-engineering]
└── Task 31: 广告管理-两级钻取子页面 [deep]

Wave 7 (New Pages — after Wave 2+3+9, 5 parallel):
├── Task 32: 全部订单页面 [visual-engineering]
├── Task 33: 退货订单页面 [visual-engineering]
├── Task 34: 审批中心页面 [visual-engineering]
├── Task 35: 广告优化Agent子页面 [visual-engineering]
└── Task 36: 移除广告仪表盘安全日志+沙箱 [quick]

Wave 8 (System Management — after Wave 1+3, 5 parallel):
├── Task 37: 用户管理前端页面 [visual-engineering]
├── Task 38: Agent配置管理页面 [visual-engineering]
├── Task 39: API密钥状态页面增强 [visual-engineering]
├── Task 40: 费用监控移至系统管理 [quick]
└── Task 41: 隐藏系统配置+保留计划任务 [quick]

Wave 9 (Feishu + Deploy — after ALL above, 3 sequential):
├── Task 42: 飞书AI聊天集成 [deep]
├── Task 43: 飞书通知推送增强 [unspecified-high]
└── Task 44: SSL证书+HTTPS部署 [unspecified-high]

Wave FINAL (After ALL tasks — 4 parallel reviews, then user okay):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)
-> Present results -> Get explicit user okay
```

### Critical Path
Task 1-3 → Task 4-9 → Task 10-14 → Task 21-26 → Task 27-31 → Task 44 → F1-F4 → user okay

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| 1-3 | None | 4-9 |
| 4 | 1-3 | 5, 37 |
| 5 | 4 | 37 |
| 6 | 1-3 | 38, 42 |
| 7 | 4 | 38 |
| 8 | 1-3 | 10-14, 21-26 |
| 9 | 1-3 | 23, 26, 28-35 |
| 10 | 8 | 21, 22, 23 |
| 11 | 8 | 24, 25, 26, 28-31 |
| 12 | 8 | 32 |
| 13 | 8 | 33 |
| 14 | 8 | 18 |
| 15-20 | 1-3 | 21-26, 27-35 |
| 21-23 | 10, 15-20 | F1-F4 |
| 24-26 | 11, 15-20 | F1-F4 |
| 27 | 9, 11 | 28-31 |
| 28-30 | 27 | F1-F4 |
| 31 | 27 | F1-F4 |
| 32 | 9, 12, 17, 19 | F1-F4 |
| 33 | 9, 13, 17, 19 | F1-F4 |
| 34 | 17, 19 | F1-F4 |
| 35 | 17, 19 | F1-F4 |
| 36 | 15-20 | F1-F4 |
| 37 | 5, 17, 19 | F1-F4 |
| 38 | 6, 7, 17, 19 | F1-F4 |
| 39 | 17, 19 | F1-F4 |
| 40-41 | 17, 19 | F1-F4 |
| 42 | 6 | F1-F4 |
| 43 | 42 | F1-F4 |
| 44 | ALL 1-43 | F1-F4 |
| F1-F4 | ALL | user okay |

### Agent Dispatch Summary

- **Wave 0**: **3** — T1 `deep`, T2 `deep`, T3 `deep`
- **Wave 1**: **6** — T4 `deep`, T5 `unspecified-high`, T6 `deep`, T7 `unspecified-high`, T8 `quick`, T9 `visual-engineering`
- **Wave 2**: **5** — T10-T13 `unspecified-high`, T14 `quick`
- **Wave 3**: **6** — T15-T19 `visual-engineering`, T20 `quick`
- **Wave 4**: **3** — T21-T23 `visual-engineering`
- **Wave 5**: **3** — T24-T26 `visual-engineering`
- **Wave 6**: **5** — T27 `deep`, T28-T30 `visual-engineering`, T31 `deep`
- **Wave 7**: **5** — T32-T35 `visual-engineering`, T36 `quick`
- **Wave 8**: **5** — T37-T39 `visual-engineering`, T40-T41 `quick`
- **Wave 9**: **3** — T42 `deep`, T43 `unspecified-high`, T44 `unspecified-high`
- **FINAL**: **4** — F1 `oracle`, F2 `unspecified-high`, F3 `unspecified-high`, F4 `deep`

---

## TODOs

### Wave 0: Critical Bug Fixes (Issues 30)

- [x] 1. datetime时区修复 — 全Agent修复offset-naive vs offset-aware比较

  **What to do**:
  - 在`src/agents/chat_base_agent.py`中找到datetime比较逻辑，确保所有datetime对象统一使用timezone-aware格式
  - 创建`src/utils/timezone.py`工具模块：提供`now_site_time(site='US')`返回洛杉矶时区aware datetime、`to_site_time(dt, site='US')`转换函数
  - 搜索整个`src/agents/`目录，找到所有`datetime.now()`和`datetime.utcnow()`调用，替换为`now_site_time()`
  - 搜索所有datetime比较操作（`<`, `>`, `>=`, `<=`），确保两侧都是aware或都是naive
  - 在`src/db/models.py`中确认所有DateTime列使用`timezone=True`
  - 运行受影响的Agent测试确认修复

  **Must NOT do**:
  - 不修改`src/agents/base_agent.py`
  - 不改变datetime在数据库中的存储格式（只改Python层比较逻辑）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 需要全局搜索+理解Agent执行流中的时间逻辑，涉及多文件修改
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: 纯后端修复，无UI

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 0 (with Tasks 2, 3)
  - **Blocks**: Tasks 4-9 (Wave 1)
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `src/agents/chat_base_agent.py` — 全文件，datetime bug在此文件中（99行），找到所有datetime.now()和比较操作
  - `src/agents/base_agent.py` — 24行抽象基类，了解但不修改

  **API/Type References**:
  - `src/db/models.py` — 所有DateTime列定义，确认timezone=True设置

  **Test References**:
  - `src/agents/` — 全目录扫描所有Agent文件中的datetime用法

  **External References**:
  - Python `zoneinfo`模块文档 — `ZoneInfo("America/Los_Angeles")`用法

  **WHY Each Reference Matters**:
  - `chat_base_agent.py`是bug源头，KB自迭代hook中的datetime比较触发异常
  - `base_agent.py`标记为不可修改，需避免误改
  - 需全局扫描确保没有遗漏的naive datetime

  **Acceptance Criteria**:
  - [ ] `src/utils/timezone.py`创建，包含`now_site_time()`和`to_site_time()`
  - [ ] 所有Agent文件中无`datetime.now()`或`datetime.utcnow()`裸调用
  - [ ] `grep -r "datetime.now()" src/agents/` 返回0结果
  - [ ] `grep -r "datetime.utcnow()" src/agents/` 返回0结果

  **QA Scenarios**:

  ```
  Scenario: Agent执行不再抛出datetime比较异常
    Tool: Bash (curl)
    Preconditions: 服务器运行中，boss用户已登录获取TOKEN
    Steps:
      1. curl -X POST http://localhost:8000/api/chat/core_management/stream -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"message":"你好"}'
      2. 观察SSE响应流，检查是否有error事件
      3. grep "offset-naive" in response — 不应出现
    Expected Result: SSE流正常返回AI回复，无timezone相关错误
    Failure Indicators: 响应中包含"offset-naive"或"offset-aware"或"TypeError"
    Evidence: .sisyphus/evidence/task-1-datetime-fix.txt

  Scenario: 时区工具函数正确返回洛杉矶时间
    Tool: Bash (python)
    Preconditions: src/utils/timezone.py已创建
    Steps:
      1. python -c "from src.utils.timezone import now_site_time; dt = now_site_time('US'); print(dt.tzinfo); assert dt.tzinfo is not None"
      2. python -c "from src.utils.timezone import now_site_time; dt = now_site_time('US'); print(dt.strftime('%Z'))"
    Expected Result: tzinfo不为None，时区显示为PST或PDT
    Failure Indicators: AssertionError, ImportError, None tzinfo
    Evidence: .sisyphus/evidence/task-1-timezone-util.txt
  ```

  **Commit**: YES (groups with Wave 0)
  - Message: `fix(agents): resolve datetime timezone offset-naive vs offset-aware comparison`
  - Files: `src/utils/timezone.py`, `src/agents/chat_base_agent.py`, `src/agents/*.py`
  - Pre-commit: `python -c "from src.utils.timezone import now_site_time; assert now_site_time().tzinfo is not None"`

- [x] 2. 对话历史修复 — 前端加载+后端保存联合修复

  **What to do**:
  - 排查`src/api/chat.py`中的对话历史端点，确认`GET /api/chat/{agent_type}/conversations`和`GET /api/chat/{agent_type}/conversations/{id}/messages`正常返回数据
  - 排查`src/db/chat.py`中的CRUD函数，确认消息正确保存到数据库
  - 排查前端`src/frontend/src/pages/ChatPage.tsx`（或类似），确认页面加载时调用历史API
  - 如果前端未实现历史加载：添加useEffect在页面打开时请求历史会话列表，选中时加载消息
  - 确认SSE消息流正确保存到DB（每条AI回复+用户消息都persist）
  - 确认`PUT /api/chat/conversations/{id}`端点可正常更新对话标题

  **Must NOT do**:
  - 不改变SSE流格式
  - 不修改现有API接口契约（只修复内部实现）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 需要同时排查前端+后端+数据库三层，理解完整数据流
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 0 (with Tasks 1, 3)
  - **Blocks**: Tasks 4-9
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `src/api/chat.py` — 聊天REST + SSE端点，找到conversations GET/PUT端点和stream端点
  - `src/db/chat.py` — 聊天数据库CRUD，确认save_message/get_messages函数
  - `src/services/chat.py:30-44` — AGENT_REGISTRY，了解Agent类型到类的映射

  **API/Type References**:
  - `src/db/models.py` — Conversation和Message模型定义
  - `src/api/sse.py` — SSE格式和心跳机制

  **Frontend References**:
  - `src/frontend/src/pages/` — 找到聊天页面组件，检查是否调用了历史API
  - `src/frontend/src/api/client.ts` — Axios客户端，确认API调用方式
  - `src/frontend/src/hooks/useSSE.ts` — SSE hook，了解消息接收流程

  **WHY Each Reference Matters**:
  - 问题可能在前端（未调用API）或后端（未保存）或两者都有
  - 需要从用户发消息→SSE接收→DB保存→前端加载 全链路排查

  **Acceptance Criteria**:
  - [ ] 发送消息后关闭页面再打开，历史消息能正确显示
  - [ ] `curl GET /api/chat/core_management/conversations` 返回非空会话列表（在有历史的情况下）
  - [ ] 前端聊天页面加载时自动请求并显示历史会话

  **QA Scenarios**:

  ```
  Scenario: 发送消息后刷新页面能看到历史
    Tool: Bash (curl)
    Preconditions: boss用户TOKEN已获取
    Steps:
      1. curl -X POST http://localhost:8000/api/chat/core_management/stream -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"message":"测试历史消息保存"}'
      2. 等待SSE流完成
      3. curl http://localhost:8000/api/chat/core_management/conversations -H "Authorization: Bearer $TOKEN"
      4. 从返回的conversation列表中取最新的conversation_id
      5. curl http://localhost:8000/api/chat/core_management/conversations/{id}/messages -H "Authorization: Bearer $TOKEN"
    Expected Result: Step 3返回至少1个conversation，Step 5返回包含"测试历史消息保存"的用户消息和AI回复
    Failure Indicators: conversations返回空数组，或messages不包含发送的内容
    Evidence: .sisyphus/evidence/task-2-conversation-history.txt

  Scenario: 历史会话不存在时返回空数组而非错误
    Tool: Bash (curl)
    Preconditions: 使用一个从未聊天过的agent_type
    Steps:
      1. curl http://localhost:8000/api/chat/selection/conversations -H "Authorization: Bearer $TOKEN"
    Expected Result: 返回200 + 空数组 `[]`，不是404或500
    Failure Indicators: 非200状态码或非JSON响应
    Evidence: .sisyphus/evidence/task-2-empty-history.txt
  ```

  **Commit**: YES (groups with Wave 0)
  - Message: `fix(chat): ensure conversation history persists and loads correctly`
  - Files: `src/api/chat.py`, `src/db/chat.py`, `src/frontend/src/pages/ChatPage.tsx`
  - Pre-commit: `curl -s http://localhost:8000/api/chat/core_management/conversations -H "Authorization: Bearer $TOKEN" | python -c "import json,sys; data=json.load(sys.stdin); assert isinstance(data, list)"`

- [x] 3. 关键词Agent修复 — keyword_library Agent完全无回复问题排查

  **What to do**:
  - 查看`src/agents/`中keyword相关的Agent文件，理解其完整执行流
  - 检查`src/services/chat.py` AGENT_REGISTRY中keyword_library的注册
  - 运行keyword_library Agent并捕获完整错误日志
  - 常见原因排查：
    a) 工具(tool)依赖缺失或配置错误
    b) 模型配置指向不存在的model
    c) Prompt模板错误
    d) 外部API（如卖家精灵MCP）连接失败
  - 修复根因，确保Agent能正常对话回复
  - 如果依赖外部数据源（卖家精灵MCP等），确保在数据源不可用时给出友好的降级提示而非静默失败

  **Must NOT do**:
  - 不修改base_agent.py
  - 不改变Agent的核心工作流逻辑，只修复配置/连接问题

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 需要深入排查Agent运行时错误，可能涉及多层调试
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 0 (with Tasks 1, 2)
  - **Blocks**: Tasks 4-9
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `src/services/chat.py:30-44` — AGENT_REGISTRY，找到keyword_library映射到哪个类
  - `src/agents/chat_base_agent.py` — ChatBaseAgent基类，理解Agent执行流

  **Agent-Specific References**:
  - `src/agents/` — 搜索keyword相关文件（可能是`keyword_agent.py`或`keyword_library_agent.py`）
  - `src/agents/model_config.py` — AGENT_MODEL_MAP，检查keyword_library配置的模型

  **External References**:
  - 检查是否有`src/tools/`目录中的keyword相关工具函数
  - 检查`src/config.py`中是否有keyword相关配置项

  **WHY Each Reference Matters**:
  - AGENT_REGISTRY是入口，确认注册正确
  - model_config确认不是模型配置问题
  - Agent具体文件是修复的核心目标

  **Acceptance Criteria**:
  - [ ] `curl POST /api/chat/keyword_library/stream` 返回正常SSE流（含AI回复内容）
  - [ ] 无"Error"或"Exception"事件在SSE流中
  - [ ] Agent能正常响应基础对话（如"你好"、"帮我分析关键词 wireless earbuds"）

  **QA Scenarios**:

  ```
  Scenario: 关键词Agent正常回复用户消息
    Tool: Bash (curl)
    Preconditions: boss用户TOKEN已获取，服务运行中
    Steps:
      1. curl -X POST http://localhost:8000/api/chat/keyword_library/stream -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"message":"你好，请帮我分析关键词 wireless earbuds"}'
      2. 读取SSE流输出
      3. 检查是否有data行包含AI回复文本（非error事件）
    Expected Result: SSE流包含AI回复内容，可能包含关键词分析结果或友好的引导回复
    Failure Indicators: SSE流为空、只有error事件、超时无响应
    Evidence: .sisyphus/evidence/task-3-keyword-agent-response.txt

  Scenario: 外部数据源不可用时Agent降级友好提示
    Tool: Bash (curl)
    Preconditions: 如Agent依赖外部API，模拟该API不可用
    Steps:
      1. curl -X POST http://localhost:8000/api/chat/keyword_library/stream -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"message":"分析关键词 bluetooth speaker"}'
      2. 检查响应是否包含友好提示而非堆栈跟踪
    Expected Result: 即使外部数据源不可用，Agent也能回复（可以是"数据源暂不可用"的友好提示）
    Failure Indicators: 500错误、Python traceback暴露给用户、完全无响应
    Evidence: .sisyphus/evidence/task-3-keyword-agent-fallback.txt
  ```

  **Commit**: YES (groups with Wave 0)
  - Message: `fix(agents): resolve keyword_library agent silent failure`
  - Files: `src/agents/keyword*.py`, `src/services/chat.py`
  - Pre-commit: `curl -s -X POST http://localhost:8000/api/chat/keyword_library/stream -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"message":"test"}' | head -5`

### Wave 1: Backend Foundations (Issues 22, 23, 24, 6-utility)

- [x] 4. users数据库表 + Alembic迁移 — DB用户管理基础

  **What to do**:
  - 在`src/db/models.py`中新增`User`模型：id(UUID), username(unique), password_hash, role(boss/operator), display_name, is_active(bool), created_at, updated_at
  - 使用bcrypt做密码hash
  - 创建Alembic迁移文件`005_add_users_table`
  - 迁移脚本中：创建表 + 插入3个初始用户（boss/test123, op1/test123, op2/test123，密码hash后存储）
  - 修改`src/api/auth.py`：从环境变量USERS字典改为查询数据库验证用户
  - 确保JWT生成逻辑不变（仍返回username+role）
  - 确保`src/api/middleware.py`中JWTAuthMiddleware不需要修改（它只解码JWT，不查DB）

  **Must NOT do**:
  - 不改变JWT payload结构（保持{username, role}）
  - 不改变现有API端点路径
  - 不添加复杂权限系统（只有boss/operator两个角色）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 涉及数据库模型、迁移、认证系统修改，需要谨慎处理数据安全
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 5, 6, 7, 8, 9)
  - **Blocks**: Task 5 (CRUD API), Task 37 (用户管理前端)
  - **Blocked By**: Wave 0 完成

  **References**:

  **Pattern References**:
  - `src/db/models.py` — 现有19个模型的定义方式，遵循相同的Base/命名/字段模式
  - `src/api/auth.py` — 当前环境变量USERS字典认证逻辑，需要重写为DB查询

  **API/Type References**:
  - `src/api/middleware.py:130` — JWTAuthMiddleware返回`{"username": username, "role": role}`，确认不需修改
  - `src/config.py` — `settings.DATABASE_URL`（大写）

  **Migration References**:
  - 查找`alembic/versions/`目录中现有迁移文件格式（当前head是`004_add_phase4`）

  **WHY Each Reference Matters**:
  - models.py定义所有表，新User模型需遵循相同模式
  - auth.py是需要重写的核心文件
  - middleware.py确认JWT解码层不受影响

  **Acceptance Criteria**:
  - [ ] `alembic upgrade head`成功执行，users表创建
  - [ ] `SELECT * FROM users`返回3行（boss, op1, op2）
  - [ ] boss/test123可通过新DB验证正常登录
  - [ ] JWT payload保持`{username, role}`不变

  **QA Scenarios**:

  ```
  Scenario: 迁移成功并初始用户可登录
    Tool: Bash (curl + docker exec)
    Preconditions: 数据库运行中
    Steps:
      1. docker exec amazon-ai-app alembic upgrade head
      2. docker exec amazon-ai-postgres psql -U app_user -d amazon_automation -c "SELECT username, role, is_active FROM users ORDER BY username"
      3. curl -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"username":"boss","password":"test123"}'
      4. curl -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"username":"op1","password":"test123"}'
    Expected Result: Step 2返回3行用户; Step 3/4返回200 + access_token + 正确的role
    Failure Indicators: 迁移失败、users表不存在、登录返回401
    Evidence: .sisyphus/evidence/task-4-users-migration.txt

  Scenario: 错误密码被拒绝
    Tool: Bash (curl)
    Steps:
      1. curl -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"username":"boss","password":"wrongpassword"}'
    Expected Result: 返回401 Unauthorized
    Failure Indicators: 返回200或500
    Evidence: .sisyphus/evidence/task-4-wrong-password.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(auth): migrate user management from env vars to database`
  - Files: `src/db/models.py`, `src/api/auth.py`, `alembic/versions/005_*.py`

- [x] 5. 用户CRUD API — boss专属用户管理端点

  **What to do**:
  - 创建`src/api/users.py`：实现用户CRUD REST API
    - `GET /api/users` — 列出所有用户（boss only）
    - `POST /api/users` — 创建用户（boss only）
    - `PUT /api/users/{user_id}` — 更新用户（boss only）
    - `DELETE /api/users/{user_id}` — 删除/停用用户（boss only）
    - `PUT /api/users/me/password` — 修改自己密码（所有角色）
  - 所有boss-only端点使用`require_role("boss")`装饰器
  - 创建`src/db/users.py`：数据库CRUD操作函数
  - 在`src/api/main.py`中注册新路由
  - 删除用户时设置`is_active=False`而非物理删除
  - 创建Pydantic schema用于请求/响应验证

  **Must NOT do**:
  - 不实现token黑名单（删除用户后JWT仍有效直到过期，这是可接受的简化）
  - 不允许删除boss用户自己
  - 不允许operator创建/删除用户

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 标准REST CRUD，逻辑清晰但文件较多
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 4)
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 37 (用户管理前端)
  - **Blocked By**: Task 4 (users表)

  **References**:

  **Pattern References**:
  - `src/api/approvals.py` — 现有API端点编写模式（FastAPI router）
  - `src/api/dependencies.py` — `require_role()`使用方式

  **API/Type References**:
  - `src/db/models.py:User` — 用户模型（Task 4创建）
  - `src/api/auth.py` — 了解现有认证流程

  **WHY Each Reference Matters**:
  - approvals.py展示项目中API端点的标准写法
  - dependencies.py的require_role是权限控制核心

  **Acceptance Criteria**:
  - [ ] `GET /api/users`返回用户列表（boss token）
  - [ ] `POST /api/users`创建新用户成功
  - [ ] operator token调用`GET /api/users`返回403
  - [ ] `DELETE /api/users/{id}`设置is_active=False

  **QA Scenarios**:

  ```
  Scenario: Boss可CRUD用户
    Tool: Bash (curl)
    Steps:
      1. curl -X POST http://localhost:8000/api/users -H "Authorization: Bearer $BOSS_TOKEN" -H "Content-Type: application/json" -d '{"username":"test_user","password":"pass123","role":"operator","display_name":"测试用户"}'
      2. 记录返回的user_id
      3. curl http://localhost:8000/api/users -H "Authorization: Bearer $BOSS_TOKEN"
      4. curl -X PUT http://localhost:8000/api/users/{user_id} -H "Authorization: Bearer $BOSS_TOKEN" -H "Content-Type: application/json" -d '{"display_name":"修改后的名称"}'
      5. curl -X DELETE http://localhost:8000/api/users/{user_id} -H "Authorization: Bearer $BOSS_TOKEN"
    Expected Result: 全部返回200/201，Step 3包含新用户，Step 5后用户is_active=False
    Failure Indicators: 任何步骤非2xx响应
    Evidence: .sisyphus/evidence/task-5-user-crud.txt

  Scenario: Operator被拒绝访问用户管理
    Tool: Bash (curl)
    Steps:
      1. curl http://localhost:8000/api/users -H "Authorization: Bearer $OP1_TOKEN"
    Expected Result: 返回403 Forbidden
    Failure Indicators: 返回200或500
    Evidence: .sisyphus/evidence/task-5-rbac-reject.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(api): add user CRUD endpoints with RBAC`
  - Files: `src/api/users.py`, `src/db/users.py`, `src/api/main.py`

- [x] 6. OpenRouter集成到LLM client — 双模式LLM调用

  **What to do**:
  - 修改`src/llm/client.py`：
    a) 移除lines 524-548的硬编码Anthropic分支（直接用`anthropic.AsyncAnthropic`的代码）
    b) 添加OpenRouter支持：通过litellm的`openrouter/`前缀（如`openrouter/anthropic/claude-3.5-sonnet`）
    c) 保留直连OpenAI模式（现有逻辑不变）
    d) 根据model名称前缀自动选择路由：`openrouter/`前缀走OpenRouter，否则走直连
  - 在`src/config.py`中添加`OPENROUTER_API_KEY`配置项（可选，空则禁用）
  - 修改`src/agents/model_config.py`的AGENT_MODEL_MAP结构，支持每个Agent配置`provider`（openai/openrouter/anthropic）和`model`
  - 在数据库中添加agent_configs表（或复用现有表）存储每Agent的LLM配置
  - 确保streaming（SSE）在OpenRouter模式下正常工作

  **Must NOT do**:
  - 不破坏现有OpenAI直连功能
  - 不强制要求OpenRouter key（key为空时降级到直连模式）
  - 不修改SSE流格式
  - 不修改`base_agent.py`

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: LLM client是核心模块，修改需要深入理解litellm和现有调用链
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 38 (Agent配置管理), Task 42 (飞书AI聊天)
  - **Blocked By**: Wave 0

  **References**:

  **Pattern References**:
  - `src/llm/client.py` — 全文件，特别是lines 524-548硬编码Anthropic分支，以及`chat()`和`chat_stream()`函数
  - `src/agents/model_config.py` — AGENT_MODEL_MAP当前结构

  **API/Type References**:
  - `src/config.py` — Settings类，添加OPENROUTER_API_KEY

  **External References**:
  - LiteLLM文档：`openrouter/`前缀用法
  - OpenRouter API：`https://openrouter.ai/api/v1`，兼容OpenAI Chat Completions

  **WHY Each Reference Matters**:
  - client.py是LLM调用的唯一入口，所有Agent都通过它调用模型
  - 硬编码Anthropic分支需要移除否则会在无Anthropic key时报错（Issue 30 Bug A-2）
  - model_config.py决定每个Agent用什么模型

  **Acceptance Criteria**:
  - [ ] `src/llm/client.py`中无`anthropic.AsyncAnthropic`直接调用
  - [ ] 环境变量`OPENROUTER_API_KEY`为空时，系统正常运行（降级到OpenAI直连）
  - [ ] AGENT_MODEL_MAP支持`provider`字段
  - [ ] core_management agent用OpenAI模型可正常对话

  **QA Scenarios**:

  ```
  Scenario: OpenAI直连模式正常工作（无OpenRouter key）
    Tool: Bash (curl)
    Preconditions: OPENROUTER_API_KEY未配置或为空
    Steps:
      1. curl -X POST http://localhost:8000/api/chat/core_management/stream -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"message":"你好"}'
      2. 读取SSE流，确认有AI回复
    Expected Result: 正常SSE流回复，使用OpenAI模型
    Failure Indicators: 连接错误、API key错误、无回复
    Evidence: .sisyphus/evidence/task-6-openai-direct.txt

  Scenario: 硬编码Anthropic分支已移除
    Tool: Bash (grep)
    Steps:
      1. grep -n "AsyncAnthropic" src/llm/client.py
      2. grep -n "anthropic.Client" src/llm/client.py
    Expected Result: 两个grep都返回空（无匹配）
    Failure Indicators: 仍有硬编码Anthropic client创建代码
    Evidence: .sisyphus/evidence/task-6-no-hardcoded-anthropic.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(llm): integrate OpenRouter support with provider-per-agent configuration`
  - Files: `src/llm/client.py`, `src/config.py`, `src/agents/model_config.py`

- [x] 7. Agent中文名DB存储 + API — Agent配置数据库化

  **What to do**:
  - 在`src/db/models.py`中确认是否有现存的agent_config表，如没有则创建`AgentConfig`模型：agent_type(PK), display_name_cn, description, is_active, visible_roles(JSON), sort_order
  - 创建Alembic迁移插入13个Agent的中文名初始数据（按用户确认的顺序）
  - 创建或修改`src/api/system.py`中的Agent配置端点：
    - `GET /api/agents/config` — 返回所有Agent配置（含中文名）
    - `PUT /api/agents/config/{agent_type}` — 更新Agent配置（boss only）
  - 前端数据文件`src/frontend/src/data/agents.ts`的硬编码ID列表保留，但中文名从API获取

  **Must NOT do**:
  - 不改变AGENT_REGISTRY结构（保持agent_type→class映射）
  - 不添加Agent创建/删除API（Agent类型固定）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 数据模型+API+迁移，模式清晰
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 38 (Agent配置管理前端)
  - **Blocked By**: Task 4 (需要DB迁移基础)

  **References**:

  **Pattern References**:
  - `src/api/system.py` — 现有系统管理端点模式
  - `src/services/chat.py:30-44` — AGENT_REGISTRY中的13个agent_type

  **Data References**:
  - 用户确认的Agent中文名映射（见上方"Agent中文名映射"表格）

  **WHY Each Reference Matters**:
  - AGENT_REGISTRY列出所有有效的agent_type，迁移脚本需要为每个插入一条配置记录
  - system.py是Agent配置端点的归属地

  **Acceptance Criteria**:
  - [ ] `GET /api/agents/config`返回13个Agent配置，每个含`display_name_cn`
  - [ ] `PUT /api/agents/config/core_management`可修改中文名（boss token）
  - [ ] auditor Agent的`visible_roles`只包含"boss"

  **QA Scenarios**:

  ```
  Scenario: 获取Agent配置列表含中文名
    Tool: Bash (curl)
    Steps:
      1. curl http://localhost:8000/api/agents/config -H "Authorization: Bearer $TOKEN"
      2. 检查返回JSON中core_management的display_name_cn是否为"AI主管"
      3. 检查keyword_library的display_name_cn是否为"关键词agent"
    Expected Result: 返回13个Agent配置对象，每个都有display_name_cn字段
    Failure Indicators: 缺少display_name_cn、Agent数量不对
    Evidence: .sisyphus/evidence/task-7-agent-config.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(agents): add agent configuration with Chinese names to database`
  - Files: `src/db/models.py`, `src/api/system.py`, `alembic/versions/006_*.py`

- [x] 8. 时区工具函数库 — 前端+后端时间处理基础设施

  **What to do**:
  - **后端**（如Task 1未完全覆盖）：确保`src/utils/timezone.py`提供完整API：
    - `now_site_time(site='US')` → LA时区aware datetime
    - `to_site_time(dt, site='US')` → 转换任意datetime到站点时区
    - `site_today_range(site='US')` → 返回(start, end)元组，站点自然日边界
    - `last_24h_range(site='US')` → 返回(start, end)元组，最近24小时
    - `week_range(site='US')` / `month_range(site='US')` / `year_range(site='US')` → 本周/月/年
  - **前端**：创建`src/frontend/src/utils/timezone.ts`：
    - `toSiteTime(date: Date, site?: string): Date` — 使用Intl.DateTimeFormat转换
    - `formatSiteTime(date: Date, format?: string): string` — 格式化显示
    - `getTimeRangeLabel(range: TimeRange): string` — 时间范围中文标签
    - `TIME_RANGES`常量：6种时间范围配置

  **Must NOT do**:
  - 不引入moment.js或dayjs（使用原生Intl API + Python zoneinfo）
  - 不做多站点适配（硬编码US=America/Los_Angeles）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 纯工具函数，无复杂依赖
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 10-14 (Mock数据需要时间范围), Tasks 21-26 (仪表盘时间切换)
  - **Blocked By**: Wave 0

  **References**:

  **Pattern References**:
  - `src/utils/` — 现有工具函数目录结构
  - `src/frontend/src/utils/` — 前端工具函数目录（如有）

  **External References**:
  - Python `zoneinfo.ZoneInfo("America/Los_Angeles")` 文档
  - JS `Intl.DateTimeFormat('en-US', {timeZone: 'America/Los_Angeles'})` 文档

  **Acceptance Criteria**:
  - [ ] `python -c "from src.utils.timezone import site_today_range; print(site_today_range())"` 输出LA时区今天的start/end
  - [ ] 前端`timezone.ts`导出所有工具函数，无TypeScript错误

  **QA Scenarios**:

  ```
  Scenario: 后端时区工具正确返回LA时间范围
    Tool: Bash (python)
    Steps:
      1. python -c "from src.utils.timezone import site_today_range; s,e = site_today_range(); print(f'Start: {s}, End: {e}'); assert s.tzinfo is not None; assert e > s"
    Expected Result: 打印LA时区的今日start/end，assert通过
    Failure Indicators: ImportError, AssertionError
    Evidence: .sisyphus/evidence/task-8-timezone-utils.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(utils): add timezone utility functions for site time handling`
  - Files: `src/utils/timezone.py`, `src/frontend/src/utils/timezone.ts`

- [x] 9. 前端共享DataTable组件 — 可复用表格基础组件

  **What to do**:
  - 创建`src/frontend/src/components/DataTable.tsx`：通用可复用表格组件
  - 功能要求：
    a) 列定义配置：`columns: Column[]`（每列：key, title, width, sortable, render函数）
    b) 排序：点击列头切换升序/降序，当前排序列高亮
    c) 分页：共X条 / 上下页 / X条/页 / 前往X页（完整赛狐ERP分页样式）
    d) 汇总行：表格首行可选显示合计数据（`summaryRow?: Record<string, any>`）
    e) 行点击：`onRowClick?: (row) => void`
    f) 加载状态：loading skeleton
    g) 空状态：无数据时显示友好提示
    h) 暗黑/明亮模式兼容（使用CSS变量或Tailwind dark:前缀）
  - 创建`src/frontend/src/components/Pagination.tsx`：独立分页组件（DataTable内部使用，也可独立用）
  - 创建`src/frontend/src/types/table.ts`：Column/PaginationConfig等类型定义

  **Must NOT do**:
  - 不引入第三方表格库（用原生HTML table + Tailwind）
  - 不实现虚拟滚动（数据量不大，标准分页即可）
  - 不实现列拖拽/列隐藏/列宽调整

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: UI组件，需要精确的样式和交互
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 23, 26, 28-35 (所有使用表格的页面)
  - **Blocked By**: Wave 0

  **References**:

  **Pattern References**:
  - `src/frontend/src/components/` — 现有组件目录结构和命名约定
  - `src/frontend/src/pages/Dashboard.tsx` — 现有页面中如果有表格的话，参考其模式

  **Design References**:
  - 赛狐ERP截图中的分页样式：`共 XX 条 < 1 2 3 > XX条/页 前往 X 页`
  - 赛狐ERP截图中的汇总行样式：表格首行灰色背景，显示"合计"

  **External References**:
  - Tailwind CSS表格样式
  - React 19 + TypeScript组件模式

  **WHY Each Reference Matters**:
  - DataTable被广告管理、订单、退货、SKU排名等6+个页面使用，是最关键的共享组件
  - 分页样式需要精确匹配赛狐ERP截图

  **Acceptance Criteria**:
  - [ ] `DataTable`组件可接受columns配置渲染表格
  - [ ] 点击列头实现排序（升序/降序切换）
  - [ ] 分页组件显示"共X条 上下页 X条/页 前往X页"
  - [ ] 汇总行在数据上方显示合计
  - [ ] 暗黑/明亮模式下样式正确
  - [ ] `bun run build`无TypeScript错误

  **QA Scenarios**:

  ```
  Scenario: DataTable组件正确渲染
    Tool: Bash (build check)
    Steps:
      1. cd src/frontend && bun run build
      2. 检查build输出无error
      3. grep -r "DataTable" src/frontend/src/components/DataTable.tsx — 确认文件存在
      4. grep -r "Pagination" src/frontend/src/components/Pagination.tsx — 确认文件存在
    Expected Result: build成功，两个组件文件存在
    Failure Indicators: build失败，文件不存在
    Evidence: .sisyphus/evidence/task-9-datatable-build.txt

  Scenario: DataTable类型定义完整
    Tool: Bash (grep)
    Steps:
      1. grep "export interface Column" src/frontend/src/types/table.ts
      2. grep "export interface PaginationConfig" src/frontend/src/types/table.ts
    Expected Result: 两个interface都存在
    Failure Indicators: grep无匹配
    Evidence: .sisyphus/evidence/task-9-datatable-types.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(frontend): add shared DataTable component with sorting, pagination, summary row`
  - Files: `src/frontend/src/components/DataTable.tsx`, `src/frontend/src/components/Pagination.tsx`, `src/frontend/src/types/table.ts`

### Wave 2: Mock Data Layer (Issue 32)

- [x] 10. 仪表盘Mock数据API — Dashboard指标/趋势/SKU数据

  **What to do**:
  - 创建`src/api/dashboard.py`：仪表盘数据端点
    - `GET /api/dashboard/metrics?time_range=site_today|last_24h` — 返回10个指标卡片数据（总销售额、总订单量、销售量、广告花费、广告订单量、TACoS、ACoS、退货数量）+ 各指标较前一周期的变化百分比
    - `GET /api/dashboard/trend?time_range=site_today|last_24h|this_week|this_month|this_year|custom&start=&end=&metrics=sales,orders,...` — 返回趋势图数据点数组
    - `GET /api/dashboard/sku_ranking?time_range=...&sort_by=sales&sort_order=desc&page=1&page_size=20` — 返回SKU排名分页数据
  - 创建`data/mock/dashboard.py`：Mock数据生成器
    - 生成合理的电商Mock数据（销售额$500-$5000/天，订单量20-200等）
    - 趋势数据按时间范围生成相应粒度的数据点
    - SKU数据生成20个Mock SKU（含图片URL用placeholder）
  - 使用`src/utils/timezone.py`的时间范围函数
  - 在`src/api/main.py`注册新路由
  - **接口契约**：响应结构与未来SP-API真实数据完全相同

  **Must NOT do**:
  - 不调用任何真实SP-API
  - 不实现毛利润/毛利率计算（返回null）
  - 不在Mock数据中使用随机种子以外的外部依赖

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: API设计+Mock数据生成，需要合理的数据模型
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 11, 12, 13, 14)
  - **Blocks**: Tasks 21, 22, 23 (仪表盘前端)
  - **Blocked By**: Task 8 (时区工具)

  **References**:

  **Pattern References**:
  - `src/amazon_api/mock.py` — 现有Mock数据模式
  - `data/mock/seed_database.py` — 现有Mock数据种子脚本

  **API/Type References**:
  - `src/utils/timezone.py` — 时间范围函数（Task 8/1创建）

  **Data References**:
  - Issue 5确认的指标：总销售额、总订单量、销售量、广告花费、广告订单量、TACoS、ACoS、退货数量
  - Issue 9确认的SKU列：SKU码、商品主图、销售额、订单量、销售量、广告花费、ACoS、TACoS、毛利润(空)、毛利率(空)、FBA可售数、预计可售天数
  - Issue 7确认的趋势图7个指标

  **Acceptance Criteria**:
  - [ ] `GET /api/dashboard/metrics?time_range=site_today` 返回包含所有8个指标的JSON
  - [ ] `GET /api/dashboard/trend?time_range=this_week&metrics=sales,orders` 返回7天的数据点数组
  - [ ] `GET /api/dashboard/sku_ranking` 返回分页SKU列表（含total_count和items）
  - [ ] TACoS和ACoS值在合理范围（0%-100%）

  **QA Scenarios**:

  ```
  Scenario: Dashboard metrics API返回完整数据
    Tool: Bash (curl)
    Steps:
      1. curl http://localhost:8000/api/dashboard/metrics?time_range=site_today -H "Authorization: Bearer $TOKEN"
      2. 验证JSON包含字段: total_sales, total_orders, units_sold, ad_spend, ad_orders, tacos, acos, returns_count
      3. 验证每个指标有value和change_percentage
    Expected Result: 200 + 完整JSON，所有8个指标都有合理数值
    Failure Indicators: 缺少字段、数值为null/NaN、404
    Evidence: .sisyphus/evidence/task-10-dashboard-metrics.txt

  Scenario: SKU排名支持分页和排序
    Tool: Bash (curl)
    Steps:
      1. curl "http://localhost:8000/api/dashboard/sku_ranking?sort_by=sales&sort_order=desc&page=1&page_size=5" -H "Authorization: Bearer $TOKEN"
      2. 验证返回包含total_count、items数组（5条）
      3. 验证items按销售额降序排列
    Expected Result: 分页数据正确，排序正确
    Failure Indicators: items超过5条、排序不对、缺少分页字段
    Evidence: .sisyphus/evidence/task-10-sku-ranking.txt
  ```

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(api): add mock dashboard data endpoints`
  - Files: `src/api/dashboard.py`, `data/mock/dashboard.py`, `src/api/main.py`

- [x] 11. 广告Mock数据API — 广告仪表盘+广告管理全量数据

  **What to do**:
  - 创建`src/api/ads.py`：广告数据端点
    - **广告仪表盘**:
      - `GET /api/ads/dashboard/metrics?time_range=...` — 广告指标卡片（广告花费、广告销售额、ACoS、点击量、曝光量、CTR、转化率、CPC等）
      - `GET /api/ads/dashboard/trend?time_range=...&metrics=...` — 广告趋势图（11个指标）
      - `GET /api/ads/dashboard/campaign_ranking?sort_by=...&page=...` — Campaign排名（10列）
    - **广告管理8个Tab**:
      - `GET /api/ads/portfolios?page=...&page_size=...` — 广告组合列表
      - `GET /api/ads/campaigns?portfolio_id=...&ad_type=SP|SB|SD|ST&page=...` — 广告活动列表
      - `GET /api/ads/ad_groups?campaign_id=...&page=...` — 广告组列表
      - `GET /api/ads/ad_products?ad_group_id=...&page=...` — 广告产品列表
      - `GET /api/ads/targeting?page=...` — 投放列表
      - `GET /api/ads/search_terms?page=...` — 搜索词列表
      - `GET /api/ads/negative_targeting?page=...` — 否定投放列表
      - `GET /api/ads/logs?page=...` — 广告日志列表
    - **钻取子页面**:
      - `GET /api/ads/campaigns/{id}/ad_groups` — 活动下的广告组
      - `GET /api/ads/campaigns/{id}/targeting` — 活动下的投放
      - `GET /api/ads/campaigns/{id}/search_terms` — 活动下的搜索词
      - `GET /api/ads/campaigns/{id}/negative_targeting` — 活动下的否定投放
      - `GET /api/ads/campaigns/{id}/logs` — 活动日志
      - `GET /api/ads/campaigns/{id}/settings` — 活动设置
      - 广告组子页面类似endpoints
  - 创建`data/mock/ads.py`：广告Mock数据生成器
    - 生成5个Portfolio、20个Campaign（SP/SB/SD分布）、50个Ad Group、100个Product
    - 投放/搜索词/否定投放各生成合理数量
    - 所有列完整对照赛狐ERP截图的字段
  - 所有列表端点统一响应格式：`{total_count, items[], summary_row}`
  - Portfolio树API：`GET /api/ads/portfolio_tree` — 返回树形结构用于左侧筛选

  **Must NOT do**:
  - 不调用Amazon Ads API
  - 不实现广告操作写入（创建/修改/删除广告活动等）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 大量端点设计+Mock数据生成，但模式统一
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 24-26 (广告仪表盘前端), Tasks 28-31 (广告管理前端)
  - **Blocked By**: Task 8 (时区工具)

  **References**:

  **Data References**:
  - Issue 14确认的Campaign排名10列
  - Issue 13确认的11个广告趋势指标
  - Issue 16确认的各Tab列定义（见draft spec Issue 16部分，lines 127-145）
  - 赛狐ERP截图目录: `E:\amazon-automation\广告管理截图\` — 46张截图作为列定义参考

  **Pattern References**:
  - `src/amazon_api/mock.py` — 现有Mock模式
  - Task 10的dashboard.py — 相同的分页响应格式

  **Acceptance Criteria**:
  - [ ] 8个广告Tab端点全部返回200 + 分页数据
  - [ ] 每个列表包含summary_row
  - [ ] Campaign列表支持portfolio_id和ad_type筛选
  - [ ] Portfolio树API返回嵌套结构

  **QA Scenarios**:

  ```
  Scenario: 广告活动列表支持筛选和分页
    Tool: Bash (curl)
    Steps:
      1. curl "http://localhost:8000/api/ads/campaigns?ad_type=SP&page=1&page_size=10" -H "Authorization: Bearer $TOKEN"
      2. 验证total_count、items（≤10条）、summary_row存在
      3. 验证items中每条都有ad_type="SP"
    Expected Result: 过滤后的分页数据，只有SP类型
    Failure Indicators: 返回非SP类型数据、缺少分页字段
    Evidence: .sisyphus/evidence/task-11-campaigns-filter.txt

  Scenario: Portfolio树API返回嵌套结构
    Tool: Bash (curl)
    Steps:
      1. curl http://localhost:8000/api/ads/portfolio_tree -H "Authorization: Bearer $TOKEN"
      2. 验证返回数组，每个portfolio有id/name/campaign_count
    Expected Result: 树形结构JSON数组
    Failure Indicators: 404、空数组、缺少层级
    Evidence: .sisyphus/evidence/task-11-portfolio-tree.txt
  ```

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(api): add comprehensive mock ads data endpoints`
  - Files: `src/api/ads.py`, `data/mock/ads.py`, `src/api/main.py`

- [x] 12. 订单Mock数据API — 全部订单+详情

  **What to do**:
  - 创建`src/api/orders.py`：订单端点
    - `GET /api/orders?time_range=...&status=...&search=...&page=...&page_size=...` — 订单列表（14列）
    - `GET /api/orders/{order_id}` — 订单详情（4个区块：基本信息+收货信息+产品信息+费用明细）
  - 创建`data/mock/orders.py`：订单Mock数据生成器
    - 生成50个Mock订单（不同状态：Pending/Shipped/Delivered/Cancelled/Refunded）
    - 每个订单含完整详情（收货地址、产品信息、15+费用明细项）
    - 费用明细包含：产品金额、促销折扣、礼品包装费、买家运费、税费、销售收益、商城征税、FBA运费、销售佣金、订单其他费、亚马逊回款、采购成本、头程费用、测评费用、订单利润、订单利润率
  - 统一分页响应：`{total_count, items[], summary_row}`
  - summary_row包含：总销售收益、总订单量等汇总

  **Must NOT do**:
  - 不调用SP-API
  - 操作按钮API返回Mock提示（不实际执行）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 32 (订单前端页面)
  - **Blocked By**: Task 8

  **References**:

  **Data References**:
  - Issue 18确认的14列 + 详情弹窗4个区块（见draft spec lines 153-162）
  - 订单截图: `E:\amazon-automation\全部订单页截图-1.png`（列表）, `全部订单页截图-2.png`（详情）

  **Acceptance Criteria**:
  - [ ] `GET /api/orders?page=1&page_size=10` 返回分页订单列表
  - [ ] `GET /api/orders/{id}` 返回完整详情含4个区块
  - [ ] 费用明细包含15+项

  **QA Scenarios**:

  ```
  Scenario: 订单列表和详情正常返回
    Tool: Bash (curl)
    Steps:
      1. curl "http://localhost:8000/api/orders?page=1&page_size=5" -H "Authorization: Bearer $TOKEN"
      2. 取第一条订单的order_id
      3. curl "http://localhost:8000/api/orders/{order_id}" -H "Authorization: Bearer $TOKEN"
      4. 验证详情包含basic_info, shipping_info, products, fee_details
    Expected Result: 列表5条+详情4区块完整
    Failure Indicators: 缺少区块、fee_details少于15项
    Evidence: .sisyphus/evidence/task-12-orders-api.txt
  ```

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(api): add mock orders data endpoints`
  - Files: `src/api/orders.py`, `data/mock/orders.py`, `src/api/main.py`

- [x] 13. 退货Mock数据API — FBA退货列表

  **What to do**:
  - 创建`src/api/returns.py`：退货端点
    - `GET /api/returns?time_range=...&reason=...&status=...&search=...&page=...` — FBA退货列表（18列）
  - 创建`data/mock/returns.py`：退货Mock数据生成器
    - 生成30个Mock退货记录
    - 退货原因分布：DEFECTIVE, UNWANTED_ITEM, CUSTOMER_CHANGED_MIND, WRONG_ITEM等
    - 退货状态：Pending, Received, Refunded, Closed
  - 统一分页响应格式

  **Must NOT do**:
  - 不做FBM退货Tab
  - 不做买家之声Tab

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 33 (退货前端页面)
  - **Blocked By**: Task 8

  **References**:

  **Data References**:
  - Issue 19确认的18列（见draft spec lines 164-169）
  - 退货截图: `E:\amazon-automation\退货订单页截图-1.png`, `退货订单页截图-2.png`

  **Acceptance Criteria**:
  - [ ] `GET /api/returns?page=1` 返回分页退货列表
  - [ ] 列表每条包含18个字段
  - [ ] 支持reason和status筛选

  **QA Scenarios**:

  ```
  Scenario: 退货列表支持筛选
    Tool: Bash (curl)
    Steps:
      1. curl "http://localhost:8000/api/returns?reason=DEFECTIVE&page=1" -H "Authorization: Bearer $TOKEN"
      2. 验证返回items中每条的return_reason都是DEFECTIVE
    Expected Result: 过滤后只返回DEFECTIVE原因的退货
    Failure Indicators: 包含其他原因的退货
    Evidence: .sisyphus/evidence/task-13-returns-filter.txt
  ```

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(api): add mock returns data endpoints`
  - Files: `src/api/returns.py`, `data/mock/returns.py`, `src/api/main.py`

- [x] 14. 通知Mock数据API — 铃铛通知聚合端点

  **What to do**:
  - 创建`src/api/notifications.py`：通知端点
    - `GET /api/notifications/count` — 返回各类型待处理通知数量：`{approvals: N, kb_reviews: N, agent_failures: N, buyer_messages: 0}`
    - `GET /api/notifications/list?page=...` — 返回通知列表（类型、标题、时间、已读/未读）
    - `PUT /api/notifications/{id}/read` — 标记已读
  - 从现有数据源聚合：
    - 审批待处理数：查询approvals表status=pending的count
    - KB待审核数：查询kb_reviews表status=pending的count
    - Agent失败数：查询近24小时内status=failed的任务数
    - 买家消息：固定返回0（留位）
  - 在`src/api/main.py`注册

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 18 (通知铃铛前端)
  - **Blocked By**: Task 8

  **References**:
  - `src/api/approvals.py` — 审批API模式
  - `src/db/models.py` — approval/kb_review模型

  **Acceptance Criteria**:
  - [ ] `GET /api/notifications/count` 返回4类通知计数
  - [ ] buyer_messages固定为0

  **QA Scenarios**:

  ```
  Scenario: 通知计数正确返回
    Tool: Bash (curl)
    Steps:
      1. curl http://localhost:8000/api/notifications/count -H "Authorization: Bearer $TOKEN"
      2. 验证返回JSON有approvals/kb_reviews/agent_failures/buyer_messages四个字段
    Expected Result: 200 + 4个计数字段
    Failure Indicators: 缺少字段、非数字值
    Evidence: .sisyphus/evidence/task-14-notification-count.txt
  ```

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(api): add notification aggregation endpoints`
  - Files: `src/api/notifications.py`, `src/api/main.py`

### Wave 3: Frontend Core (Issues 2, 3, 4, 10, 31, routing)

- [x] 15. 登录页增强 — 版权信息+联系管理员提示

  **What to do**:
  - 修改登录页面组件（找到Login相关页面）
  - 在登录框下方添加两行文字：
    1. `© 2026 siqiangshangwu.com 版权所有`
    2. `没有账号？请联系管理员添加`
  - 保持"PUDIWIND AI"标题不变
  - 文字样式：灰色小字，居中对齐
  - 确保暗黑/明亮模式下均可见

  **Must NOT do**:
  - 不修改登录逻辑
  - 不添加注册功能

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 16-20)
  - **Blocks**: None (independent)
  - **Blocked By**: Wave 0

  **References**:
  - `src/frontend/src/pages/` — 找到Login页面组件
  - Issue 2确认的文字内容

  **Acceptance Criteria**:
  - [ ] 登录页显示版权文字和联系管理员提示
  - [ ] "PUDIWIND AI"标题未修改

  **QA Scenarios**:
  ```
  Scenario: 登录页显示新增文字
    Tool: Bash (curl + grep)
    Steps:
      1. curl http://localhost:8000/ -s | grep "siqiangshangwu.com"
      2. curl http://localhost:8000/ -s | grep "联系管理员"
    Expected Result: HTML中包含版权文字和联系管理员提示
    Failure Indicators: grep无匹配
    Evidence: .sisyphus/evidence/task-15-login-page.txt
  ```

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(login): add copyright notice and contact admin hint`
  - Files: `src/frontend/src/pages/LoginPage.tsx`

- [x] 16. 暗黑/明亮模式切换 — 全局主题系统

  **What to do**:
  - 创建`src/frontend/src/contexts/ThemeContext.tsx`：主题上下文
    - 提供`theme`（dark/light）和`toggleTheme()`
    - 从localStorage读取初始值，默认dark
    - 切换时保存到localStorage
    - 切换时在`<html>`元素上添加/移除`dark`类（Tailwind dark mode）
  - 在TopBar右上角添加太阳/月亮图标按钮
    - dark模式显示太阳图标（点击切换到light）
    - light模式显示月亮图标（点击切换到dark）
  - 在App.tsx中包裹ThemeProvider
  - 确保现有组件的Tailwind类支持dark:前缀
  - 参考`temp_frontend_ref/`中的主题实现但不直接复制（那个未与实际app集成）

  **Must NOT do**:
  - 不做系统主题跟随（仅手动切换）
  - 不添加第三种主题
  - 不引入CSS-in-JS库

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: 所有后续前端任务（需要主题支持）
  - **Blocked By**: Wave 0

  **References**:
  - `temp_frontend_ref/` — 参考主题实现思路（但NOT直接使用）
  - `src/frontend/src/components/TopBar.tsx` — 图标按钮放置位置
  - `src/frontend/tailwind.config.js` — 确认Tailwind darkMode配置

  **Acceptance Criteria**:
  - [ ] 顶部导航栏显示太阳/月亮图标
  - [ ] 点击图标切换主题
  - [ ] 刷新页面后主题保持（localStorage）
  - [ ] 默认dark模式

  **QA Scenarios**:
  ```
  Scenario: 主题切换和持久化
    Tool: Bash (build check)
    Steps:
      1. cd src/frontend && bun run build
      2. grep "ThemeContext" src/frontend/src/contexts/ThemeContext.tsx
      3. grep "localStorage" src/frontend/src/contexts/ThemeContext.tsx
    Expected Result: build成功，ThemeContext文件存在且使用localStorage
    Failure Indicators: build失败、文件不存在
    Evidence: .sisyphus/evidence/task-16-theme-toggle.txt
  ```

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(theme): add dark/light mode toggle with localStorage persistence`
  - Files: `src/frontend/src/contexts/ThemeContext.tsx`, `src/frontend/src/components/TopBar.tsx`, `src/frontend/src/App.tsx`

- [x] 17. 侧边栏完全重构 — 8项导航+折叠子菜单

  **What to do**:
  - 重写`src/frontend/src/components/Sidebar.tsx`：
    1. **数据大盘** → `/dashboard`
    2. **AI Manager** → `/chat/core_management`（直接跳转，无子菜单）
    3. **更多功能** → 展开子菜单显示11个Agent列表（按确认顺序），审计agent仅boss可见
    4. **广告数据大盘** → `/ads/dashboard`
    5. **广告管理** → 展开：广告列表`/ads/management`、广告优化Agent`/ads/agent`
    6. **订单** → 展开：全部订单`/orders`、退货订单`/returns`
    7. **审批中心** → `/approvals`
    8. **系统管理** (仅boss) → 展开：用户管理`/system/users`、Agent配置`/system/agents`、API密钥`/system/api-keys`、计划任务`/system/schedules`、费用监控`/system/costs`
  - 从API获取当前用户角色（JWT解析或API调用），boss才显示"系统管理"和"审计agent"
  - 折叠/展开状态保存到localStorage
  - 当前激活项高亮
  - 暗黑/明亮模式兼容
  - 响应式：移动端可收起

  **Must NOT do**:
  - 不改变路由路径格式（保持/开头的相对路径）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: 所有后续页面任务（导航入口）
  - **Blocked By**: Wave 0

  **References**:
  - `src/frontend/src/components/Sidebar.tsx` — 现有侧边栏（仅3项，需完全重写）
  - `src/frontend/src/data/agents.ts` — 13个Agent配置
  - 侧边栏最终结构确认（见draft spec lines 239-247）

  **Acceptance Criteria**:
  - [ ] 侧边栏显示8个一级菜单项
  - [ ] "更多功能"展开显示11个Agent
  - [ ] boss用户可见"系统管理"，operator不可见
  - [ ] 当前页面对应菜单项高亮

  **QA Scenarios**:
  ```
  Scenario: 侧边栏结构完整
    Tool: Bash (grep)
    Steps:
      1. grep -c "数据大盘\|AI Manager\|更多功能\|广告数据大盘\|广告管理\|订单\|审批中心\|系统管理" src/frontend/src/components/Sidebar.tsx
    Expected Result: 至少8个匹配（每个菜单项至少出现一次）
    Failure Indicators: 匹配数少于8
    Evidence: .sisyphus/evidence/task-17-sidebar.txt
  ```

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(sidebar): complete restructure with 8 navigation items and role-based visibility`
  - Files: `src/frontend/src/components/Sidebar.tsx`

- [x] 18. 通知铃铛组件 — 增强版带弹窗列表

  **What to do**:
  - 修改`src/frontend/src/components/TopBar.tsx`中的通知铃铛：
    - 定时轮询`GET /api/notifications/count`（每30秒）
    - Badge显示总待处理数（审批+KB审核+Agent失败之和）
    - 点击铃铛弹出下拉面板显示通知列表
    - 每条通知显示：类型图标、标题、时间
    - 点击审批类通知跳转到审批中心`/approvals`
    - 点击Agent失败通知跳转到对应Agent页面
    - 面板底部"查看全部"链接到审批中心
  - 创建`src/frontend/src/hooks/useNotifications.ts`：通知数据hook

  **Must NOT do**:
  - 不使用WebSocket（用轮询）
  - 不实现买家消息通知（数量固定为0）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: None
  - **Blocked By**: Task 14 (通知API)

  **References**:
  - `src/frontend/src/components/TopBar.tsx` — 现有铃铛组件位置
  - Task 14的API端点

  **Acceptance Criteria**:
  - [ ] 铃铛显示数字badge
  - [ ] 点击铃铛弹出通知列表
  - [ ] 轮询间隔30秒

  **QA Scenarios**:
  ```
  Scenario: 铃铛组件编译正确
    Tool: Bash (build)
    Steps:
      1. cd src/frontend && bun run build
      2. grep "useNotifications" src/frontend/src/hooks/useNotifications.ts
    Expected Result: build成功，hook文件存在
    Evidence: .sisyphus/evidence/task-18-notifications.txt
  ```

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(notifications): enhance bell with dropdown panel and polling`
  - Files: `src/frontend/src/components/TopBar.tsx`, `src/frontend/src/hooks/useNotifications.ts`

- [x] 19. 前端路由体系重建 — 完整路由配置

  **What to do**:
  - 重写`src/frontend/src/App.tsx`路由配置：
    - `/` → 重定向到`/dashboard`
    - `/login` → LoginPage
    - `/dashboard` → Dashboard
    - `/chat/:agentType` → ChatPage（通用聊天页面）
    - `/agents` → AgentListPage（更多功能列表）
    - `/ads/dashboard` → AdDashboard
    - `/ads/management` → AdManagement（8-Tab主页）
    - `/ads/management/campaign/:id` → CampaignDetail（活动钻取子页面）
    - `/ads/management/ad-group/:id` → AdGroupDetail（广告组钻取子页面）
    - `/ads/agent` → AdAgentPage（广告优化Agent+沙箱）
    - `/orders` → OrdersPage
    - `/returns` → ReturnsPage
    - `/approvals` → ApprovalsPage
    - `/system/users` → UserManagementPage
    - `/system/agents` → AgentConfigPage
    - `/system/api-keys` → ApiKeysPage
    - `/system/schedules` → SchedulesPage
    - `/system/costs` → CostMonitorPage
  - 创建占位页面组件（`PlaceholderPage.tsx`）用于尚未实现的路由
  - 添加`PrivateRoute`包装器确保未登录跳转login
  - 添加`BossRoute`包装器确保boss-only页面权限
  - 保持现有Layout组件（Sidebar + TopBar + Content区域）

  **Must NOT do**:
  - 不实现页面内容（只搭建路由骨架+占位页面）
  - 不改变Login页面路由逻辑

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: 所有后续页面任务
  - **Blocked By**: Wave 0

  **References**:
  - `src/frontend/src/App.tsx` — 现有12条路由
  - `src/frontend/src/api/client.ts` — JWT token处理

  **Acceptance Criteria**:
  - [ ] 所有路由路径已注册
  - [ ] 未登录访问任何页面跳转到/login
  - [ ] operator访问/system/*跳转到/dashboard
  - [ ] `bun run build`成功

  **QA Scenarios**:
  ```
  Scenario: 路由配置完整
    Tool: Bash (grep)
    Steps:
      1. grep -c "path=" src/frontend/src/App.tsx
    Expected Result: 至少18条路由定义
    Failure Indicators: 少于18条
    Evidence: .sisyphus/evidence/task-19-routes.txt
  ```

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(router): rebuild complete routing with placeholders and auth guards`
  - Files: `src/frontend/src/App.tsx`, `src/frontend/src/components/PlaceholderPage.tsx`, `src/frontend/src/components/PrivateRoute.tsx`, `src/frontend/src/components/BossRoute.tsx`

- [x] 20. 聊天页返回按钮 — 顶部导航返回

  **What to do**:
  - 在聊天页面组件顶部添加"← 返回"按钮
  - 点击返回到Agent列表页（`/agents`）
  - 使用`useNavigate()`的`navigate(-1)`或直接`navigate('/agents')`
  - 样式：左上角，小字，带左箭头图标

  **Must NOT do**:
  - 不修改聊天功能逻辑

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: None
  - **Blocked By**: Wave 0

  **References**:
  - `src/frontend/src/pages/` — 聊天页面组件

  **Acceptance Criteria**:
  - [ ] 聊天页面顶部显示"← 返回"按钮
  - [ ] 点击按钮导航到Agent列表页

  **QA Scenarios**:
  ```
  Scenario: 返回按钮存在
    Tool: Bash (grep)
    Steps:
      1. grep -r "返回" src/frontend/src/pages/ChatPage.tsx
    Expected Result: 找到"返回"文字
    Evidence: .sisyphus/evidence/task-20-back-button.txt
  ```

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(chat): add back button to chat page header`
  - Files: `src/frontend/src/pages/ChatPage.tsx`

### Wave 4: Dashboard Enhancement (Issues 5, 7, 8, 9)

- [x] 21. 仪表盘指标卡片+时间切换 — 10个指标卡片

  **What to do**:
  - 重写`src/frontend/src/pages/Dashboard.tsx`的卡片区域：
    - 10个指标卡片：总销售额、总订单量、销售量、广告花费、广告订单量、TACoS、ACoS、退货数量（+ 保留现有的其他2个如有）
    - 每个卡片显示：指标名称、数值、较前一周期变化百分比（绿色↑/红色↓）
    - 卡片区顶部时间切换：「站点今天」/「最近24小时」两个Tab
    - 切换时间时调用`GET /api/dashboard/metrics?time_range=site_today|last_24h`
  - 卡片网格布局：4列×3行（或自适应）
  - 标注数据新鲜度：卡片区右上角显示"Mock数据 · 最后更新: XX:XX"
  - 暗黑/明亮模式兼容

  **Must NOT do**:
  - 不实现毛利润卡片（不在此列表中）
  - 不实现真实数据获取

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 22, 23)
  - **Blocks**: F1-F4
  - **Blocked By**: Task 10 (Mock API), Tasks 15-20 (前端核心)

  **References**:
  - `src/frontend/src/pages/Dashboard.tsx` — 现有仪表盘页面
  - Task 10的API响应格式
  - Issue 5确认的指标列表

  **Acceptance Criteria**:
  - [ ] 仪表盘显示8+个指标卡片
  - [ ] 时间切换Tab可用
  - [ ] 卡片显示变化百分比和箭头
  - [ ] 标注"Mock数据"标签

  **QA Scenarios**:
  ```
  Scenario: 仪表盘卡片渲染和时间切换
    Tool: Bash (build + grep)
    Steps:
      1. cd src/frontend && bun run build
      2. grep "site_today\|last_24h" src/frontend/src/pages/Dashboard.tsx
      3. grep "Mock数据" src/frontend/src/pages/Dashboard.tsx
    Expected Result: build成功，时间切换和Mock标签代码存在
    Evidence: .sisyphus/evidence/task-21-dashboard-cards.txt
  ```

  **Commit**: YES (groups with Wave 4)
  - Message: `feat(dashboard): add metric cards with time range toggle`
  - Files: `src/frontend/src/pages/Dashboard.tsx`

- [x] 22. 仪表盘趋势图 — 7指标可切换趋势图

  **What to do**:
  - 在Dashboard.tsx中添加趋势图区域（卡片下方）：
    - 使用图表库（recharts或chart.js — 检查package.json中已安装的库）
    - 7个指标：销售额、订单量、销售量、广告花费、广告销售额、ACoS、TACoS
    - 每个指标有独立的开关按钮（chip/toggle），可显示/隐藏该指标线
    - 时间范围选择器：6个选项（站点今天/最近24小时/本周/本月/本年/自定义）
    - 自定义时间范围：日期选择器（DatePicker）
    - 调用`GET /api/dashboard/trend?time_range=...&metrics=...`
  - X轴根据时间范围自动调整粒度（今天=小时，本周=天，本月=天/周，本年=月）
  - 多Y轴支持（百分比指标和绝对值指标分左右Y轴）
  - 暗黑/明亮模式兼容（图表背景色适应）

  **Must NOT do**:
  - 不引入新的图表库（使用已安装的或选择一个轻量级的）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4
  - **Blocks**: F1-F4
  - **Blocked By**: Task 10, Tasks 15-20

  **References**:
  - `src/frontend/package.json` — 检查已安装的图表库
  - Task 10的trend API响应格式
  - Issue 7+8确认的指标和时间范围

  **Acceptance Criteria**:
  - [ ] 趋势图显示折线图
  - [ ] 7个指标toggle可用
  - [ ] 6种时间范围切换可用
  - [ ] 暗黑模式下图表可见

  **QA Scenarios**:
  ```
  Scenario: 趋势图组件编译正确
    Tool: Bash (build)
    Steps:
      1. cd src/frontend && bun run build
    Expected Result: build成功无错误
    Evidence: .sisyphus/evidence/task-22-trend-chart.txt
  ```

  **Commit**: YES (groups with Wave 4)
  - Message: `feat(dashboard): add trend chart with 7 toggleable metrics and time ranges`
  - Files: `src/frontend/src/pages/Dashboard.tsx`, `src/frontend/src/components/TrendChart.tsx`

- [x] 23. SKU排名表格 — DataTable集成+Agent Activity移除

  **What to do**:
  - 在Dashboard.tsx中添加SKU排名区域（趋势图下方）：
    - 使用共享DataTable组件
    - 12列：SKU码、商品主图（缩略图）、销售额、订单量、销售量、广告花费、ACoS、TACoS、毛利润(灰色"-")、毛利率(灰色"-")、FBA可售数、预计可售天数
    - 默认按销售额降序
    - 可点击列头切换排序
    - 调用`GET /api/dashboard/sku_ranking`
  - **完全移除Agent Activity板块**（如存在）
    - Agent活动历史移到审批中心的历史Tab
  - 商品主图列：显示50x50缩略图（Mock用placeholder图片）

  **Must NOT do**:
  - 不实现毛利润/毛利率计算（显示"-"）
  - 不保留Agent Activity板块

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4
  - **Blocks**: F1-F4
  - **Blocked By**: Task 9 (DataTable), Task 10 (Mock API)

  **References**:
  - Task 9的DataTable组件
  - Task 10的sku_ranking API
  - Issue 9确认的12列和排序规则

  **Acceptance Criteria**:
  - [ ] SKU排名表格显示12列
  - [ ] 默认按销售额降序
  - [ ] 毛利润/毛利率显示"-"
  - [ ] Agent Activity板块已移除

  **QA Scenarios**:
  ```
  Scenario: SKU排名使用DataTable
    Tool: Bash (grep)
    Steps:
      1. grep "DataTable" src/frontend/src/pages/Dashboard.tsx
      2. grep -c "Agent Activity\|AgentActivity" src/frontend/src/pages/Dashboard.tsx
    Expected Result: DataTable引用存在，Agent Activity引用为0
    Evidence: .sisyphus/evidence/task-23-sku-ranking.txt
  ```

  **Commit**: YES (groups with Wave 4)
  - Message: `feat(dashboard): add SKU ranking table, remove Agent Activity`
  - Files: `src/frontend/src/pages/Dashboard.tsx`

### Wave 5: Ad Dashboard Enhancement (Issues 12, 13, 14, 15)

- [x] 24. 广告仪表盘卡片+时间 — 广告指标卡片

  **What to do**:
  - 重写/增强广告仪表盘页面的卡片区域：
    - 广告指标卡片：广告花费、广告销售额、ACoS、点击量、曝光量、CTR、转化率、CPC等
    - 卡片区时间：站点今天/最近24小时 切换
    - 调用`GET /api/ads/dashboard/metrics`
    - 每个卡片显示数值+变化百分比
  - 标注"Mock数据"标签

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Tasks 25, 26)
  - **Blocks**: F1-F4
  - **Blocked By**: Task 11, Tasks 15-20

  **References**:
  - 现有广告仪表盘页面
  - Task 11的ads dashboard metrics API
  - Issue 12确认的时间切换规则

  **Acceptance Criteria**:
  - [ ] 广告卡片显示8+个指标
  - [ ] 时间切换正常

  **QA Scenarios**:
  ```
  Scenario: 广告仪表盘卡片渲染
    Tool: Bash (build)
    Steps:
      1. cd src/frontend && bun run build
    Expected Result: 无编译错误
    Evidence: .sisyphus/evidence/task-24-ad-cards.txt
  ```

  **Commit**: YES (groups with Wave 5)

- [x] 25. 广告趋势图+齿轮选择器 — 11指标可选广告趋势

  **What to do**:
  - 在广告仪表盘添加趋势图：
    - 11个指标：广告花费、广告销售额、ACoS、点击量、曝光量、CTR、转化率、CPC、广告销量、广告订单量、TACoS
    - 右上角齿轮图标，点击弹出弹窗可勾选显示哪些指标
    - 最多同时显示6个指标（超过6个时禁用其他checkbox）
    - 时间范围：6个完整选项（同主仪表盘趋势图）
    - 调用`GET /api/ads/dashboard/trend`
  - 复用Task 22的TrendChart组件（如可复用），或基于其创建AdTrendChart

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5
  - **Blocks**: F1-F4
  - **Blocked By**: Task 11, Tasks 15-20

  **References**:
  - Task 22的TrendChart组件（复用基础）
  - Issue 13确认的11个指标 + 齿轮选择器 + 最多6个

  **Acceptance Criteria**:
  - [ ] 齿轮图标可点击弹出指标选择器
  - [ ] 最多选6个指标
  - [ ] 趋势图正确显示

  **QA Scenarios**:
  ```
  Scenario: 齿轮选择器限制6个指标
    Tool: Bash (grep)
    Steps:
      1. grep -n "6\|maxMetrics\|MAX_METRICS" src/frontend/src/pages/AdDashboard.tsx
    Expected Result: 找到6个指标限制的逻辑
    Evidence: .sisyphus/evidence/task-25-gear-selector.txt
  ```

  **Commit**: YES (groups with Wave 5)

- [x] 26. 广告Campaign排名 — 10列排名表格

  **What to do**:
  - 在广告仪表盘添加Campaign排名表格：
    - 使用DataTable组件
    - 10列按顺序：广告活动名、广告点击量、广告点击率、广告订单量、广告销售额、广告销售量、广告花费、CPC、ACoS、TACoS
    - 默认按广告花费降序
    - 调用`GET /api/ads/dashboard/campaign_ranking`
  - **移除安全日志和沙箱模拟板块**（Issue 15）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5
  - **Blocks**: F1-F4
  - **Blocked By**: Task 9 (DataTable), Task 11

  **References**:
  - Task 9的DataTable
  - Issue 14确认的10列 + Issue 15确认移除的板块

  **Acceptance Criteria**:
  - [ ] Campaign排名表格10列
  - [ ] 安全日志和沙箱已移除

  **QA Scenarios**:
  ```
  Scenario: 安全日志和沙箱已移除
    Tool: Bash (grep)
    Steps:
      1. grep -ic "安全日志\|SafetyLog\|沙箱\|Sandbox" src/frontend/src/pages/AdDashboard.tsx
    Expected Result: 0匹配（完全移除）
    Evidence: .sisyphus/evidence/task-26-remove-blocks.txt
  ```

  **Commit**: YES (groups with Wave 5)

### Wave 6: Ad Management (Issue 16 — MASSIVE, ~60% frontend effort)

- [x] 27. 广告管理主框架+Portfolio树+Tab导航 — 页面骨架

  **What to do**:
  - 创建`src/frontend/src/pages/AdManagement.tsx`：广告管理主页面
  - **页面布局**：
    - 左侧面板：Portfolio树（约200px宽）
      - 顶部搜索框
      - 全选/确认按钮
      - 树形复选框列表（从`GET /api/ads/portfolio_tree`获取）
      - 选中Portfolio后筛选右侧表格数据
    - 右侧内容区：
      - 顶部8个Tab导航：广告组合、广告活动、广告组、广告产品、投放、搜索词、否定投放、广告日志
      - Tab下方：SP/SB/SD/ST类型筛选Tab（4个小Tab）
      - 类型筛选下方：时间范围选择 + 搜索框
      - 主体：DataTable（内容由子组件根据当前Tab渲染）
  - **状态管理**：
    - 当前选中Tab
    - 选中的Portfolio(s)
    - 选中的广告类型(SP/SB/SD/ST)
    - 时间范围
    - 搜索关键词
    - 分页状态
  - 创建`src/frontend/src/pages/ad-management/`目录，用于子组件

  **Must NOT do**:
  - 不实现状态统计栏（有成交/有点击无成交等）
  - 不实现广告操作写入功能（只有UI按钮+Mock toast）
  - 不在此任务实现各Tab的列定义（由Task 28-30实现）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 复杂的状态管理+布局+多组件协调
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (Wave 6 foundation)
  - **Parallel Group**: Wave 6 start
  - **Blocks**: Tasks 28, 29, 30, 31
  - **Blocked By**: Task 9 (DataTable), Task 11 (ads API)

  **References**:

  **Design References**:
  - 赛狐ERP截图: `E:\amazon-automation\广告管理截图\广告管理-广告活动-1.png` — 整体布局参考（左侧树+右侧表格+顶部Tab）
  - `E:\amazon-automation\广告管理截图\广告管理-广告组合-1.png` — Portfolio树样式参考

  **Component References**:
  - Task 9的DataTable组件
  - Task 11的ads API端点

  **Acceptance Criteria**:
  - [ ] 页面显示左侧Portfolio树+右侧Tab导航
  - [ ] 8个Tab可切换
  - [ ] SP/SB/SD/ST筛选Tab可用
  - [ ] Portfolio树可搜索和勾选
  - [ ] `bun run build`成功

  **QA Scenarios**:
  ```
  Scenario: 广告管理页面结构完整
    Tool: Bash (grep + build)
    Steps:
      1. cd src/frontend && bun run build
      2. grep -c "广告组合\|广告活动\|广告组\|广告产品\|投放\|搜索词\|否定投放\|广告日志" src/frontend/src/pages/AdManagement.tsx
    Expected Result: build成功，8个Tab标签全部存在
    Evidence: .sisyphus/evidence/task-27-ad-mgmt-framework.txt
  ```

  **Commit**: YES (groups with Wave 6)
  - Message: `feat(ad-management): scaffold main page with portfolio tree and 8-tab navigation`
  - Files: `src/frontend/src/pages/AdManagement.tsx`, `src/frontend/src/pages/ad-management/`

- [x] 28. 广告管理-广告组合+广告活动Tab — 前两个Tab列定义

  **What to do**:
  - 创建`src/frontend/src/pages/ad-management/PortfolioTab.tsx`：
    - 广告组合列表列：店铺、广告组合、服务状态、预算、预算上限类型、预算开始/结束日期、广告活动数量、广告曝光量、广告点击量、广告点击率、广告花费、操作
    - 操作列：编辑按钮（点击toast"Mock数据模式不可用"）
    - 汇总行显示合计
    - 点击广告组合名称进入Portfolio详情（筛选该Portfolio下的Campaign）
  - 创建`src/frontend/src/pages/ad-management/CampaignTab.tsx`：
    - 广告活动列表列：店铺、广告活动(可点击进入子页面)、有效(toggle,点击toast)、服务状态、广告组合、广告类型、每日预算、预算剩余、竞价策略、广告曝光量、广告点击量、广告点击率、广告花费、CPC、广告订单量、广告转化率、ACoS、开始日期、操作
    - 有效列：toggle开关样式（点击提示Mock不可用）
    - 点击广告活动名称→导航到`/ads/management/campaign/:id`
  - 两个Tab都使用DataTable组件
  - 数据从`GET /api/ads/portfolios`和`GET /api/ads/campaigns`获取

  **Must NOT do**:
  - 不实现操作按钮的实际功能（只有UI+toast）
  - 不实现toggle的实际开关（只有UI+toast）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 27)
  - **Parallel Group**: Wave 6 parallel (with Tasks 29, 30)
  - **Blocks**: Task 31 (drill-down needs Campaign click)
  - **Blocked By**: Task 27

  **References**:
  - Issue 16确认的列定义（draft spec lines 138-140）
  - 赛狐截图: `广告管理-广告活动-1~7.png`, `广告管理-广告组合-1~3.png`
  - Task 9 DataTable组件
  - Task 11 API端点

  **Acceptance Criteria**:
  - [ ] 广告组合Tab显示完整列
  - [ ] 广告活动Tab显示19列
  - [ ] 点击活动名称有导航行为
  - [ ] 操作按钮点击显示toast

  **QA Scenarios**:
  ```
  Scenario: Campaign Tab列定义完整
    Tool: Bash (grep)
    Steps:
      1. grep -c "广告活动\|服务状态\|每日预算\|竞价策略\|ACoS\|CPC" src/frontend/src/pages/ad-management/CampaignTab.tsx
    Expected Result: 至少6个关键列名匹配
    Evidence: .sisyphus/evidence/task-28-campaign-tab.txt
  ```

  **Commit**: YES (groups with Wave 6)

- [x] 29. 广告管理-广告组+广告产品Tab — 第3-4个Tab

  **What to do**:
  - 创建`src/frontend/src/pages/ad-management/AdGroupTab.tsx`：
    - 列：店铺、广告组(可点击进入子页面)、有效(toggle)、广告产品数、服务状态、广告活动、广告组合、默认竞价、标签、创建人、广告曝光量、操作
    - 点击广告组名称→导航到`/ads/management/ad-group/:id`
  - 创建`src/frontend/src/pages/ad-management/AdProductTab.tsx`：
    - 列：店铺、产品信息(图片+标题+ASIN)、有效(toggle)、服务状态、FBA可售、价格、评分数、星级(★显示)、广告组、广告活动、广告组合、标签、业务员、操作
    - 产品信息列：缩略图+ASIN+标题的组合cell
  - 使用DataTable组件

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 27)
  - **Parallel Group**: Wave 6 parallel
  - **Blocked By**: Task 27

  **References**:
  - Issue 16列定义（draft spec lines 139, 141）
  - 赛狐截图: `广告管理-广告组-1~5.png`, `广告管理-广告产品-1~5.png`

  **Acceptance Criteria**:
  - [ ] 广告组Tab列完整，名称可点击
  - [ ] 广告产品Tab含产品图片列

  **QA Scenarios**:
  ```
  Scenario: AdGroup Tab可点击进入子页面
    Tool: Bash (grep)
    Steps:
      1. grep "navigate\|/ads/management/ad-group" src/frontend/src/pages/ad-management/AdGroupTab.tsx
    Expected Result: 找到导航到广告组子页面的代码
    Evidence: .sisyphus/evidence/task-29-adgroup-tab.txt
  ```

  **Commit**: YES (groups with Wave 6)

- [x] 30. 广告管理-投放+搜索词+否定投放+日志Tab — 后4个Tab

  **What to do**:
  - 创建`src/frontend/src/pages/ad-management/TargetingTab.tsx`：
    - 列：店铺、关键词、有效(toggle)、服务状态、匹配类型、广告组、广告活动、广告组合、竞价、建议竞价、操作
  - 创建`src/frontend/src/pages/ad-management/SearchTermTab.tsx`：
    - 列：店铺、用户搜索词、投放、匹配类型、建议竞价/范围、源竞价、ABA搜索词排名、排名周变化率、广告组、广告活动、操作
  - 创建`src/frontend/src/pages/ad-management/NegativeTargetingTab.tsx`：
    - 列：店铺、否定关键词、否定状态、匹配类型、广告组、广告活动、广告组合、创建人、广告曝光量、广告点击量、广告花费、广告订单量、广告销售、操作
  - 创建`src/frontend/src/pages/ad-management/AdLogTab.tsx`：
    - 列：店铺、操作时间(站点/北京双行)、广告组合、广告类型、广告活动、广告组、操作对象、对象详情、操作类型、操作内容

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 27)
  - **Parallel Group**: Wave 6 parallel
  - **Blocked By**: Task 27

  **References**:
  - Issue 16列定义（draft spec lines 142-145）
  - 赛狐截图: `广告管理-投放-*.png`, `广告管理-搜索词-*.png`, `广告管理-否定投放-*.png`, `广告管理-广告日志-1.png`

  **Acceptance Criteria**:
  - [ ] 4个Tab组件全部创建
  - [ ] 各Tab列定义完整匹配赛狐截图
  - [ ] `bun run build`成功

  **QA Scenarios**:
  ```
  Scenario: 4个Tab文件全部存在
    Tool: Bash (ls)
    Steps:
      1. ls src/frontend/src/pages/ad-management/TargetingTab.tsx
      2. ls src/frontend/src/pages/ad-management/SearchTermTab.tsx
      3. ls src/frontend/src/pages/ad-management/NegativeTargetingTab.tsx
      4. ls src/frontend/src/pages/ad-management/AdLogTab.tsx
    Expected Result: 4个文件全部存在
    Evidence: .sisyphus/evidence/task-30-remaining-tabs.txt
  ```

  **Commit**: YES (groups with Wave 6)

- [x] 31. 广告管理-两级钻取子页面 — Campaign+AdGroup详情子页面

  **What to do**:
  - 创建`src/frontend/src/pages/ad-management/CampaignDetail.tsx`：广告活动子页面
    - 顶部：面包屑导航（广告管理 > 广告活动名称）+ 返回按钮
    - 左侧6个Tab：广告组、投放、搜索词、否定投放、广告日志、活动设置
    - 各Tab复用Wave 6的Tab组件但传入campaign_id筛选
    - 活动设置Tab：显示Campaign的详细配置信息（只读）
  - 创建`src/frontend/src/pages/ad-management/AdGroupDetail.tsx`：广告组子页面
    - 顶部：面包屑导航（广告管理 > 活动名 > 广告组名）+ 返回按钮
    - 左侧7个Tab：广告产品、投放、搜索词、否定投放、提示词、广告组设置、广告日志
    - 提示词Tab：显示投放建议（Mock文本内容）
    - 广告组设置Tab：显示AdGroup配置信息（只读）
  - 路由已在Task 19注册：`/ads/management/campaign/:id`和`/ads/management/ad-group/:id`

  **Must NOT do**:
  - 不实现设置修改功能（只读展示）
  - 不添加广告位Tab和广告策略Tab（已确认移除）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 组件复用+路由参数传递+面包屑导航，逻辑较复杂
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Tab components from 28-30)
  - **Parallel Group**: Wave 6 后段
  - **Blocks**: F1-F4
  - **Blocked By**: Tasks 27-30

  **References**:
  - Tasks 28-30创建的Tab组件（复用+传入campaign_id/ad_group_id）
  - 赛狐截图: `广告管理-广告活动-子页面-*.png`（6张）, `广告管理-广告组-子页面-*.png`（6张）
  - Issue 16确认的子页面Tab列表

  **Acceptance Criteria**:
  - [ ] Campaign子页面6个Tab
  - [ ] AdGroup子页面7个Tab
  - [ ] 面包屑导航正确显示
  - [ ] 返回按钮回到广告管理主页

  **QA Scenarios**:
  ```
  Scenario: 钻取子页面文件和Tab数量
    Tool: Bash (grep)
    Steps:
      1. grep -c "Tab\|tab" src/frontend/src/pages/ad-management/CampaignDetail.tsx
      2. grep -c "Tab\|tab" src/frontend/src/pages/ad-management/AdGroupDetail.tsx
    Expected Result: CampaignDetail至少6个Tab引用，AdGroupDetail至少7个
    Evidence: .sisyphus/evidence/task-31-drill-down.txt
  ```

  **Commit**: YES (groups with Wave 6)
  - Message: `feat(ad-management): implement campaign and ad-group drill-down detail pages`

### Wave 7: New Pages (Issues 17, 18, 19, 21, 15-partial)

- [x] 32. 全部订单页面 — 14列列表+详情弹窗

  **What to do**:
  - 创建`src/frontend/src/pages/OrdersPage.tsx`：
    - **筛选区**：时间范围选择器 + 订单状态下拉 + ASIN/订单号搜索框
    - **数据表格**（DataTable）14列：订单号(可点击)、订购时间、付款时间、退款时间、订单状态(badge)、销售收益、图片/ASIN/MSKU(组合列)、品名/SKU、销量、退款量、促销编码、产品金额、订单利润/订单利润率(双行)、操作
    - **汇总行**：总销售收益、总订单量等
    - **操作按钮**：录入费用、标记跟评、上传发票、同步订单、导入成本、联系买家（全部点击toast"Mock数据模式不可用"）
    - **详情弹窗**（Modal）：点击订单号弹出
      - 基本信息区：订单号、状态badge、店铺、订购时间、发货时间、配送方式、预计最晚送达、物流商、运单号、买家姓名、买家邮箱、税号
      - 收货信息区：收件人、电话、邮编、收件地区、收件地址、IOSS税号
      - 产品信息表格：MSKU/FNSKU、ASIN/产品标题、商品折扣、产品金额、销量
      - 费用明细区：15+项（产品金额→订单利润率）
    - 调用`GET /api/orders`和`GET /api/orders/{id}`
  - 分页：使用DataTable的内置分页

  **Must NOT do**:
  - 不实现操作按钮实际功能
  - 不实现导出功能

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 7 (with Tasks 33-36)
  - **Blocks**: F1-F4
  - **Blocked By**: Task 9, Task 12, Task 17, Task 19

  **References**:
  - Issue 18确认的14列+详情弹窗规格（draft spec lines 153-162）
  - 订单截图: `全部订单页截图-1.png`(列表), `全部订单页截图-2.png`(详情弹窗)
  - Task 9 DataTable组件
  - Task 12 orders API端点

  **Acceptance Criteria**:
  - [ ] 订单列表14列完整
  - [ ] 点击订单号弹出详情弹窗
  - [ ] 详情弹窗含4个区块
  - [ ] 费用明细15+项
  - [ ] 筛选器可用

  **QA Scenarios**:
  ```
  Scenario: 订单页面编译和结构完整
    Tool: Bash (build + grep)
    Steps:
      1. cd src/frontend && bun run build
      2. grep -c "订单号\|订购时间\|销售收益\|产品金额" src/frontend/src/pages/OrdersPage.tsx
    Expected Result: build成功，至少4个关键列名存在
    Evidence: .sisyphus/evidence/task-32-orders-page.txt
  ```

  **Commit**: YES (groups with Wave 7)

- [x] 33. 退货订单页面 — FBA退货18列列表

  **What to do**:
  - 创建`src/frontend/src/pages/ReturnsPage.tsx`：
    - 页面标题："FBA退货"
    - **筛选区**：退货时间范围 + 退货原因下拉 + 退货状态下拉 + 订单号搜索框
    - **数据表格**（DataTable）18列：订单号、售后问题标签、退货时间、订购时间、退货站点时间、店铺/站点、商品信息(图片+标题+ASIN+MSKU组合列)、品名/SKU、父ASIN、买家备注(可展开)、退货量、发货仓库编号、库存属性、退货原因、退货状态(badge)、LPN编号、备注
    - **汇总行**：总退货量等
    - 调用`GET /api/returns`

  **Must NOT do**:
  - 不做FBM退货Tab
  - 不做买家之声Tab

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 7
  - **Blocked By**: Task 9, Task 13, Task 17, Task 19

  **References**:
  - Issue 19确认的18列（draft spec lines 164-169）
  - 退货截图: `退货订单页截图-1.png`, `退货订单页截图-2.png`

  **Acceptance Criteria**:
  - [ ] 退货列表18列完整
  - [ ] 筛选器：时间+原因+状态+搜索

  **QA Scenarios**:
  ```
  Scenario: 退货页面文件存在且编译正确
    Tool: Bash (build)
    Steps:
      1. cd src/frontend && bun run build
      2. ls src/frontend/src/pages/ReturnsPage.tsx
    Expected Result: build成功，文件存在
    Evidence: .sisyphus/evidence/task-33-returns-page.txt
  ```

  **Commit**: YES (groups with Wave 7)

- [x] 34. 审批中心页面 — 审批+历史双Tab

  **What to do**:
  - 创建`src/frontend/src/pages/ApprovalsPage.tsx`：
    - **两个Tab**：审批、历史
    - **审批Tab**：
      - 显示待审批列表（从`GET /api/approvals?status=pending`获取）
      - 每条：Agent名称(中文)、操作描述、申请时间、审批按钮(通过/拒绝)
      - 通过/拒绝调用`POST /api/approvals/{id}/approve|reject`
    - **历史Tab**：
      - 显示Agent运行历史（替代原Dashboard的Agent Activity）
      - 列：运行时间、Agent名称(中文)、运行状态(成功badge绿色/失败badge红色/进行中badge蓝色)、耗时、LLM花费、结果摘要(可展开/收起)
      - 从`GET /api/approvals?status=all`或专用历史端点获取
    - 分页
    - KB审核也显示在审批Tab中（如有pending的kb_review）

  **Must NOT do**:
  - 不实现邮件通知
  - 不实现批量审批

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 7
  - **Blocked By**: Task 17, Task 19

  **References**:
  - `src/api/approvals.py` — 现有审批API
  - `src/api/kb_review.py` — KB审核API
  - Issue 21确认的Tab结构和历史字段

  **Acceptance Criteria**:
  - [ ] 审批Tab显示待审批列表
  - [ ] 历史Tab显示运行历史，含中文Agent名
  - [ ] 结果摘要可展开收起
  - [ ] 通过/拒绝按钮调用正确API

  **QA Scenarios**:
  ```
  Scenario: 审批中心双Tab结构
    Tool: Bash (grep)
    Steps:
      1. grep -c "审批\|历史" src/frontend/src/pages/ApprovalsPage.tsx
    Expected Result: 至少4次匹配（Tab标签+内容引用）
    Evidence: .sisyphus/evidence/task-34-approvals.txt
  ```

  **Commit**: YES (groups with Wave 7)

- [x] 35. 广告优化Agent子页面 — Agent聊天+沙箱模拟

  **What to do**:
  - 创建`src/frontend/src/pages/AdAgentPage.tsx`：
    - **两个区域/Tab**：
      1. 广告监控Agent聊天：复用聊天页面组件，agent_type=ad_monitor
      2. 沙箱模拟：模拟广告操作的结果预览（从广告仪表盘移来）
    - 沙箱模拟区域：
      - 输入框：描述广告操作（如"将Campaign A的预算从$50提高到$100"）
      - 提交后显示模拟结果（Mock：预计影响指标变化）
      - 明确标注"模拟模式 — 不会执行真实操作"
  - 路由已注册：`/ads/agent`

  **Must NOT do**:
  - 不调用Amazon Ads API写入端点
  - 不实现真实的模拟计算引擎

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 7
  - **Blocked By**: Task 17, Task 19

  **References**:
  - 现有聊天页面组件（复用结构）
  - Issue 17确认：ad_monitor Agent聊天 + 沙箱模拟

  **Acceptance Criteria**:
  - [ ] 页面含Agent聊天和沙箱模拟两个区域
  - [ ] 沙箱标注"模拟模式"
  - [ ] 聊天使用ad_monitor agent_type

  **QA Scenarios**:
  ```
  Scenario: 广告Agent页面结构
    Tool: Bash (grep)
    Steps:
      1. grep "ad_monitor\|沙箱\|模拟" src/frontend/src/pages/AdAgentPage.tsx
    Expected Result: 找到agent类型和沙箱相关代码
    Evidence: .sisyphus/evidence/task-35-ad-agent.txt
  ```

  **Commit**: YES (groups with Wave 7)

- [x] 36. 移除广告仪表盘安全日志+沙箱 — 清理已移走的板块

  **What to do**:
  - 在广告仪表盘页面中完全移除：
    1. 安全日志板块（Safety Log）
    2. 沙箱模拟板块（Sandbox）
  - 这两个功能已在Task 35中移到广告管理子页面
  - 清理相关的组件导入和状态变量

  **Note**: 如果Task 26已经完成了此工作，则此任务可标记为跳过。

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 7
  - **Blocked By**: Tasks 15-20

  **Acceptance Criteria**:
  - [ ] 广告仪表盘无安全日志和沙箱
  - [ ] `bun run build`无错误

  **Commit**: YES (groups with Wave 7)

### Wave 8: System Management (Issues 22-UI, 23-UI, 24-UI, 25, 26, 27, 28)

- [x] 37. 用户管理前端页面 — Boss专属CRUD界面

  **What to do**:
  - 创建`src/frontend/src/pages/system/UserManagementPage.tsx`：
    - 用户列表表格：用户名、显示名、角色(boss/operator badge)、状态(活跃/停用)、创建时间、操作
    - 操作：编辑、停用/启用、重置密码
    - 新增用户按钮→弹出Modal表单（用户名、密码、显示名、角色选择）
    - 编辑用户→弹出Modal表单（显示名、角色）
    - 调用Task 5的用户CRUD API
  - 仅boss角色可见（BossRoute包裹）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 8 (with Tasks 38-41)
  - **Blocked By**: Task 5, Task 17, Task 19

  **References**:
  - Task 5的用户CRUD API
  - Issue 22确认的需求

  **Acceptance Criteria**:
  - [ ] 用户列表正确显示
  - [ ] CRUD操作全部可用
  - [ ] 仅boss可访问

  **QA Scenarios**:
  ```
  Scenario: 用户管理页面编译正确
    Tool: Bash (build)
    Steps:
      1. cd src/frontend && bun run build
      2. ls src/frontend/src/pages/system/UserManagementPage.tsx
    Expected Result: build成功，文件存在
    Evidence: .sisyphus/evidence/task-37-user-mgmt.txt
  ```

  **Commit**: YES (groups with Wave 8)

- [x] 38. Agent配置管理页面 — LLM提供商+模型配置

  **What to do**:
  - 创建`src/frontend/src/pages/system/AgentConfigPage.tsx`：
    - Agent列表表格：序号、中文名(可编辑)、agent_type、LLM提供商(下拉：OpenAI/OpenRouter/Anthropic)、模型名(输入框)、状态、可见角色、操作
    - 编辑按钮→Modal：修改中文名、选择LLM提供商、输入模型名、设置可见角色
    - 显示当前配置状态（已配置/未配置/错误）
    - 调用Task 7的Agent配置API
  - Agent配置不可新增/删除（只能编辑现有13个）
  - 仅boss可见

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 8
  - **Blocked By**: Task 6, Task 7, Task 17, Task 19

  **References**:
  - Task 7的Agent配置API
  - Issue 23/24确认的需求

  **Acceptance Criteria**:
  - [ ] 13个Agent全部显示
  - [ ] 可编辑中文名和LLM配置
  - [ ] LLM提供商下拉含OpenAI/OpenRouter/Anthropic

  **QA Scenarios**:
  ```
  Scenario: Agent配置页面结构
    Tool: Bash (grep)
    Steps:
      1. grep "OpenRouter\|OpenAI\|Anthropic" src/frontend/src/pages/system/AgentConfigPage.tsx
    Expected Result: 三个提供商选项都存在
    Evidence: .sisyphus/evidence/task-38-agent-config.txt
  ```

  **Commit**: YES (groups with Wave 8)

- [x] 39. API密钥状态页面增强 — 添加OpenRouter状态

  **What to do**:
  - 修改现有API密钥状态页面：
    - 保留现有OpenAI密钥状态显示
    - 添加OpenRouter密钥状态：已配置/未配置、余额（如API支持查询）、最后使用时间
    - 添加Anthropic密钥状态
    - 每个密钥项显示：名称、状态(badge)、到期日(如有)、最后验证时间
    - 手动"验证"按钮：点击后调用各平台验证端点检查密钥有效性

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 8
  - **Blocked By**: Task 17, Task 19

  **References**:
  - 现有API密钥页面
  - `src/api/system.py` — 现有api-status端点
  - Issue 26确认需求

  **Acceptance Criteria**:
  - [ ] 显示OpenAI + OpenRouter + Anthropic三个密钥状态
  - [ ] 验证按钮可用

  **Commit**: YES (groups with Wave 8)

- [x] 40. 费用监控移至系统管理 — 路由调整

  **What to do**:
  - 将费用监控页面从侧边栏一级入口移到系统管理子菜单
  - 路由从原位置改到`/system/costs`
  - 确保侧边栏中系统管理展开后显示"费用监控"子项
  - 页面内容不变，仅路由和导航变更

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 8
  - **Blocked By**: Task 17, Task 19

  **Acceptance Criteria**:
  - [ ] `/system/costs`路由可达
  - [ ] 侧边栏系统管理下显示费用监控

  **Commit**: YES (groups with Wave 8)

- [x] 41. 隐藏系统配置+保留计划任务 — 配置清理

  **What to do**:
  - 系统配置页面：从侧边栏和路由中隐藏（不删除代码，只隐藏入口）
  - 计划任务页面：保留在系统管理子菜单中`/system/schedules`
  - 确认侧边栏"系统管理"最终5个子项：用户管理、Agent配置、API密钥、计划任务、费用监控

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 8
  - **Blocked By**: Task 17, Task 19

  **Acceptance Criteria**:
  - [ ] 系统配置不在侧边栏显示
  - [ ] 计划任务在系统管理子菜单中

  **Commit**: YES (groups with Wave 8)

### Wave 9: Feishu + Deploy (Issues 29, 1)

- [x] 42. 飞书AI聊天集成 — 飞书消息→AI Manager

  **What to do**:
  - 修改`src/feishu/bot_handler.py`：
    - 当收到飞书用户消息时，将消息转发给core_management agent
    - 调用`ChatService`的处理流程，获取AI回复
    - 将AI回复通过飞书消息API返回给用户
    - 处理流式回复：收集完整回复后一次性发送（飞书不支持SSE）
  - 添加飞书用户→系统用户的映射配置
  - 添加错误处理：Agent超时/失败时发送友好错误消息
  - 保持现有webhook接收逻辑不变

  **Must NOT do**:
  - 不修改现有飞书消息格式
  - 不实现飞书审批流程（用web端审批）
  - 不实现多轮对话上下文（单轮问答）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 需要理解飞书API + Agent调用流 + 异步处理
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 9 (with Task 43)
  - **Blocks**: Task 43
  - **Blocked By**: Task 6 (OpenRouter, 确保LLM可用)

  **References**:
  - `src/feishu/bot_handler.py` — 现有飞书bot处理逻辑
  - `src/services/chat.py` — ChatService调用方式
  - `src/feishu/` — 整个飞书模块

  **Acceptance Criteria**:
  - [ ] 飞书发送消息后收到AI回复
  - [ ] Agent错误时返回友好消息而非traceback
  - [ ] 不影响现有飞书webhook功能

  **QA Scenarios**:
  ```
  Scenario: 飞书消息处理代码结构
    Tool: Bash (grep)
    Steps:
      1. grep "core_management\|ChatService" src/feishu/bot_handler.py
    Expected Result: 找到Agent调用代码
    Evidence: .sisyphus/evidence/task-42-feishu-chat.txt
  ```

  **Commit**: YES (groups with Wave 9)
  - Message: `feat(feishu): integrate AI Manager chat via Feishu bot`
  - Files: `src/feishu/bot_handler.py`

- [x] 43. 飞书通知推送增强 — 日报+任务提醒

  **What to do**:
  - 增强`src/feishu/notifications.py`：
    - **日报推送**：每日定时（如早上9点北京时间）推送昨日运营摘要
      - 摘要内容：昨日销售额、订单量、广告花费、ACoS等关键指标
      - 使用飞书卡片消息格式（美观）
    - **任务提醒**：
      - 审批待处理超过N小时：推送提醒
      - Agent任务失败：即时推送告警
      - KB待审核：推送提醒
    - 创建`src/tasks/feishu_notify.py`：定时任务函数（由计划任务系统调度）
  - 使用Mock数据生成日报内容（数据来自dashboard metrics API）

  **Must NOT do**:
  - 不实现飞书审批卡片（用web端审批）
  - 不使用飞书机器人的interactive消息（用普通卡片消息）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 42)
  - **Parallel Group**: Wave 9
  - **Blocked By**: Task 42

  **References**:
  - `src/feishu/notifications.py` — 现有通知模块
  - `src/feishu/approval.py` — 飞书消息卡片格式参考
  - Issue 29确认：日报+任务提醒

  **Acceptance Criteria**:
  - [ ] 日报推送函数存在且可调用
  - [ ] 任务失败推送函数存在
  - [ ] 使用飞书卡片消息格式

  **QA Scenarios**:
  ```
  Scenario: 通知函数可导入
    Tool: Bash (python)
    Steps:
      1. python -c "from src.feishu.notifications import send_daily_report, send_task_alert; print('OK')"
    Expected Result: 打印OK，无ImportError
    Evidence: .sisyphus/evidence/task-43-feishu-notify.txt
  ```

  **Commit**: YES (groups with Wave 9)
  - Message: `feat(feishu): add daily report and task alert notifications`
  - Files: `src/feishu/notifications.py`, `src/tasks/feishu_notify.py`

- [x] 44. SSL证书+HTTPS部署 — 生产环境最终配置

  **What to do**:
  - 在服务器(52.221.207.30)上执行：
    1. 安装certbot：`sudo apt install certbot python3-certbot-nginx`
    2. 获取Let's Encrypt证书：`sudo certbot --nginx -d siqiangshangwu.com`
    3. 启用`deploy/nginx/nginx-ssl.conf`配置（替换nginx.conf或合并）
    4. 配置HTTP→HTTPS重定向
    5. 配置自动续期：`sudo certbot renew --dry-run`验证
    6. 重启Nginx容器
  - 更新docker-compose.yml中Nginx的端口映射：添加443端口
  - 验证HTTPS访问正常

  **Must NOT do**:
  - 不使用自签名证书（必须Let's Encrypt）
  - 不关闭HTTP（保留80端口重定向到443）
  - 部署前确保所有其他任务已完成

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 服务器配置+Docker+Nginx+SSL，需要精确操作
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (must be last)
  - **Parallel Group**: Wave 9 end (sequential after all others)
  - **Blocks**: F1-F4
  - **Blocked By**: ALL Tasks 1-43

  **References**:
  - `deploy/nginx/nginx-ssl.conf` — SSL模板（certbot已配置）
  - `deploy/docker/docker-compose.yml` — 端口映射
  - 服务器信息：`ubuntu@52.221.207.30`, PEM: `~/Downloads/Pudiwind.pem`

  **Acceptance Criteria**:
  - [ ] `curl -k https://siqiangshangwu.com/health` 返回200
  - [ ] `curl http://siqiangshangwu.com/` 重定向到HTTPS
  - [ ] SSL证书有效（Let's Encrypt签发）
  - [ ] 自动续期配置验证通过

  **QA Scenarios**:
  ```
  Scenario: HTTPS正常工作
    Tool: Bash (curl)
    Steps:
      1. curl -I https://siqiangshangwu.com/
      2. curl -k https://siqiangshangwu.com/health
      3. curl -I http://siqiangshangwu.com/ (should redirect)
    Expected Result: Step 1返回200+SSL, Step 2返回{"status":"healthy"}, Step 3返回301/302到https
    Failure Indicators: SSL错误、连接拒绝、无重定向
    Evidence: .sisyphus/evidence/task-44-ssl-deploy.txt

  Scenario: SSL证书有效期
    Tool: Bash (openssl)
    Steps:
      1. echo | openssl s_client -connect siqiangshangwu.com:443 2>/dev/null | openssl x509 -noout -dates
    Expected Result: notAfter日期在90天后（Let's Encrypt标准）
    Evidence: .sisyphus/evidence/task-44-ssl-cert.txt
  ```

  **Commit**: YES
  - Message: `feat(deploy): configure SSL certificate and HTTPS for siqiangshangwu.com`
  - Files: `deploy/nginx/nginx-ssl.conf`, `deploy/docker/docker-compose.yml`

---

## Final Verification Wave

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `tsc --noEmit` + linter + `bun test`. Review all changed files for: `as any`/`@ts-ignore`, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names (data/result/item/temp).
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` skill if UI)
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (features working together, not isolation). Test edge cases: empty state, invalid input, rapid actions. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination: Task N touching Task M's files. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Wave 0**: `fix(agents): resolve datetime timezone comparison and conversation history bugs`
- **Wave 1**: `feat(backend): add users table, OpenRouter integration, agent Chinese names, timezone utils`
- **Wave 2**: `feat(api): add mock data endpoints for dashboard, ads, orders, returns`
- **Wave 3**: `feat(frontend): restructure sidebar, add theme toggle, notifications, routing`
- **Wave 4**: `feat(dashboard): enhance with metric cards, trend chart, SKU ranking`
- **Wave 5**: `feat(ad-dashboard): enhance with cards, trend chart, campaign ranking`
- **Wave 6**: `feat(ad-management): implement 8-tab ad management with drill-down`
- **Wave 7**: `feat(pages): add orders, returns, approval center, ad agent pages`
- **Wave 8**: `feat(system): add user management, agent config, API keys UI`
- **Wave 9**: `feat(feishu): add AI chat integration and notification push`
- **Wave 10**: `feat(deploy): configure SSL certificate and HTTPS`

---

## Success Criteria

### Verification Commands
```bash
# Health check via HTTPS
curl -k https://siqiangshangwu.com/health  # Expected: {"status": "healthy"}

# Login test
curl -X POST https://siqiangshangwu.com/api/auth/login -H "Content-Type: application/json" -d '{"username":"boss","password":"test123"}'  # Expected: {"access_token": "...", "role": "boss"}

# Mock data endpoints
curl -H "Authorization: Bearer $TOKEN" https://siqiangshangwu.com/api/dashboard/metrics  # Expected: JSON with sales, orders, ad_spend etc.
curl -H "Authorization: Bearer $TOKEN" https://siqiangshangwu.com/api/ads/campaigns  # Expected: paginated campaign list
curl -H "Authorization: Bearer $TOKEN" https://siqiangshangwu.com/api/orders  # Expected: paginated order list
curl -H "Authorization: Bearer $TOKEN" https://siqiangshangwu.com/api/returns  # Expected: paginated returns list

# User CRUD (boss only)
curl -H "Authorization: Bearer $BOSS_TOKEN" https://siqiangshangwu.com/api/users  # Expected: user list

# Agent chat
curl -X POST -H "Authorization: Bearer $TOKEN" https://siqiangshangwu.com/api/chat/core_management/stream  # Expected: SSE stream

# Frontend build
cd src/frontend && bun run build  # Expected: exit 0, no errors
```

### Final Checklist
- [ ] All 32 issues addressed
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All Mock data endpoints return valid paginated data
- [ ] All frontend pages render without console errors
- [ ] SSL certificate valid and HTTPS working
- [ ] boss/op1/op2 can all log in and see appropriate content
- [ ] Theme toggle persists across page reload
- [ ] Notification bell shows correct count
