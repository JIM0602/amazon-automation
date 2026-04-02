# Phase 3a: Web 管理控制台 + API 认证层

## TL;DR

> **快速摘要**: 为 PUDIWIND AI 系统构建 Web 管理控制台，包含 JWT 认证层、Agent REST API、Next.js 前端和生产环境部署（域名绑定+SSL）。
> 
> **交付物**:
> - JWT 认证系统（3 个用户账号：老板 + 2 运营）
> - Agent REST API（触发 + 状态查询）
> - Next.js 14 前端（登录 + 仪表盘 + Agent 管理）
> - 生产部署（siqiangshangwu.com + SSL + Nginx）
> 
> **预估工时**: Medium (2-3 周)
> **并行执行**: YES - 4 个执行波次
> **关键路径**: 认证层 → Agent API → 前端 → 部署

---

## Context

### 原始需求
用户希望开发 Phase 3 功能并部署 Web 管理控制台：
1. Web 控制台部署在服务器 52.221.207.30
2. 绑定域名 siqiangshangwu.com
3. 需要账号登录（3 个用户：老板 + 2 个运营）
4. 运营可以通过 Web 页面单独使用各个 Agent 功能
5. 已获取：SP-API 凭证、广告 API 凭证、OpenAI API Key（部署后配置）

### 访谈摘要
**关键决策**:
- Phase 3 拆分为 3a（Web 控制台）和 3b（新 Agent）
- 先完成 Web 控制台部署，再逐步配置调试各项凭证
- 用户认证使用 .env 配置（3 个固定账号，无需数据库用户表）
- 角色分为 boss 和 operator（老板可访问敏感操作）

### Metis 审查
**识别的关键风险**（已纳入计划）:
- 现有 API 端点未受保护 → 添加 JWT 中间件作为首要任务
- Agent 长时间运行会导致 HTTP 超时 → 使用后台任务 + 轮询模式
- Nginx 配置变更可能影响飞书 Webhook → 保持 /feishu/* 路由不变
- DNS 未配置会导致 SSL 证书申请失败 → 部署前验证清单

---

## Work Objectives

### 核心目标
构建可让团队通过 Web 浏览器管理 AI Agent 系统的控制台，支持账号登录、Agent 触发、状态监控和系统管理。

### 具体交付物
1. **JWT 认证系统**: 登录/登出、Token 管理、角色验证
2. **Agent REST API**: POST /api/agents/{type}/run, GET /api/agents/runs/{id}
3. **Next.js 前端**: 登录页、仪表盘、Agent 触发页、系统管理页
4. **生产部署**: Nginx 配置、SSL 证书、Docker 服务

### 完成标准
- [ ] 未认证请求 /api/system/status 返回 401
- [ ] 登录后获取有效 JWT Token
- [ ] 触发 Selection Agent 返回 run_id (HTTP 202)
- [ ] 轮询 run_id 获取执行状态
- [ ] https://siqiangshangwu.com 返回 200
- [ ] http://siqiangshangwu.com 重定向到 HTTPS
- [ ] 飞书 Webhook 仍正常工作
- [ ] Operator 无法访问 /api/system/stop (403)

### Must Have（必须包含）
- JWT 认证保护所有 /api/* 路由（除 /health 和 /feishu/*）
- 3 个用户账号配置在 .env（bcrypt 哈希密码）
- 角色区分：boss 可执行紧急停机，operator 只能触发 Agent
- Agent 异步执行 + 状态轮询
- Next.js 14 App Router 前端
- SSL 证书（Let's Encrypt）
- 飞书 Webhook 继续正常工作

### Must NOT Have（护栏 - 禁止包含）
- ❌ 不建数据库用户表（使用 .env 配置）
- ❌ 不做 WebSocket 实时推送（使用轮询）
- ❌ 不做用户管理 UI（添加/删除用户）
- ❌ 不做密码重置功能
- ❌ 不引入 Celery/Redis（使用 FastAPI BackgroundTasks）
- ❌ 不在 Phase 3a 开发新 Agent（留到 Phase 3b）
- ❌ 不存储明文密码
- ❌ 不修改现有飞书 Webhook 逻辑

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — 所有验证由 Agent 自动执行。

### 测试决策
- **测试基础设施**: 已有 pytest
- **自动测试**: YES (Tests-after)
- **测试框架**: pytest (后端) + Playwright (前端 E2E)

### QA 策略
- 后端: pytest tests/ -v --cov=src/api，覆盖率 ≥ 80%
- 前端: Playwright 冒烟测试（登录流程、Agent 触发、系统状态）
- 部署: curl 验证 HTTPS、重定向、飞书 Webhook

---

## Execution Strategy

### 并行执行波次

```
Wave 1 (基础认证层 — 3 个并行任务):
├── T1: JWT 认证基础设施 [deep]
├── T2: 认证中间件 [deep]
└── T3: 认证测试 [unspecified-high]

Wave 2 (Agent API 层 — 依赖 Wave 1):
├── T4: Agent 触发 API [deep]
├── T5: Agent 状态查询 API [unspecified-high]
└── T6: Agent API 测试 [unspecified-high]

Wave 3 (Next.js 前端 — 依赖 Wave 2):
├── T7: Next.js 脚手架 + 认证 [visual-engineering]
├── T8: 登录页面 [visual-engineering]
├── T9: 仪表盘页面 [visual-engineering]
├── T10: Agent 触发页面 [visual-engineering]
├── T11: 系统管理页面 [visual-engineering]
└── T12: 前端 E2E 测试 [unspecified-high]

Wave 4 (生产部署 — 依赖 Wave 3):
├── T13: Nginx 配置更新 [quick]
├── T14: Docker Compose 更新 [quick]
├── T15: SSL 证书配置 [quick]
├── T16: 部署脚本 + 验证 [deep]
└── T17: 凭证配置文档 [writing]

Wave FINAL (验证 — 依赖所有任务):
├── F1: 计划合规审计 [oracle]
├── F2: 代码质量审查 [unspecified-high]
├── F3: 实际 QA 验证 [unspecified-high]
└── F4: 范围保真度检查 [deep]
-> 提交结果 -> 获取用户确认

关键路径: T1 → T2 → T4 → T7 → T13 → T16 → F1-F4 → 用户确认
并行加速: ~60% faster than sequential
最大并发: 6 (Wave 3)
```

### 依赖矩阵

| Task | Depends On | Blocks |
|------|------------|--------|
| T1 | - | T2, T3 |
| T2 | T1 | T4, T5, T6 |
| T3 | T1, T2 | - |
| T4 | T2 | T6, T7, T10 |
| T5 | T2 | T6, T9, T10 |
| T6 | T4, T5 | - |
| T7 | T4, T5 | T8-T12 |
| T8-T11 | T7 | T12 |
| T12 | T8-T11 | T16 |
| T13-T15 | T7 | T16 |
| T16 | T12-T15 | F1-F4 |
| T17 | - | - |

### Agent 调度摘要

- **Wave 1**: 3 — T1 → `deep`, T2 → `deep`, T3 → `unspecified-high`
- **Wave 2**: 3 — T4 → `deep`, T5 → `unspecified-high`, T6 → `unspecified-high`
- **Wave 3**: 6 — T7-T11 → `visual-engineering`, T12 → `unspecified-high`
- **Wave 4**: 5 — T13-T15 → `quick`, T16 → `deep`, T17 → `writing`
- **FINAL**: 4 — F1 → `oracle`, F2-F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [ ] 1. JWT 认证基础设施

  **What to do**:
  - 添加依赖到 requirements.txt: `python-jose[cryptography]`, `passlib[bcrypt]`
  - 创建 `src/api/auth.py` 路由器:
    - POST `/api/auth/login` - 验证用户名密码，返回 JWT access_token + refresh_token
    - POST `/api/auth/refresh` - 使用 refresh_token 获取新 access_token
    - GET `/api/auth/me` - 返回当前用户信息
  - 用户配置从 .env 读取: `WEB_USERS=boss:$2b$...:boss,op1:$2b$...:operator,op2:$2b$...:operator`
  - JWT 配置: `JWT_SECRET`, `JWT_ACCESS_EXPIRE_MINUTES=480`, `JWT_REFRESH_EXPIRE_DAYS=7`
  - 创建 Pydantic 模型: LoginRequest, TokenResponse, UserInfo

  **Must NOT do**:
  - 不创建数据库用户表
  - 不存储明文密码
  - 不实现密码重置

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 认证是核心安全组件，需要深度理解和精确实现
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T2, T3 initial setup)
  - **Blocks**: T2, T3, T4, T5
  - **Blocked By**: None

  **References**:
  - `src/api/system.py` - 现有 APIRouter 模式
  - `src/config.py` - 环境变量读取模式
  - `src/feishu/bot_handler.py` - 现有认证逻辑参考

  **Acceptance Criteria**:
  - [ ] requirements.txt 包含 python-jose 和 passlib
  - [ ] src/api/auth.py 存在且包含 login/refresh/me 端点
  - [ ] .env.example 包含 WEB_USERS, JWT_SECRET 配置

  **QA Scenarios**:
  ```
  Scenario: 有效登录返回 JWT
    Tool: Bash (curl)
    Preconditions: .env 配置了 WEB_USERS
    Steps:
      1. curl -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"username":"boss","password":"test123"}'
      2. 解析响应 JSON
    Expected Result: HTTP 200, 响应包含 access_token 和 refresh_token
    Evidence: .sisyphus/evidence/task-1-login-success.json

  Scenario: 无效密码返回 401
    Tool: Bash (curl)
    Steps:
      1. curl -X POST http://localhost:8000/api/auth/login -d '{"username":"boss","password":"wrong"}'
    Expected Result: HTTP 401, 响应包含 "detail": "Invalid credentials"
    Evidence: .sisyphus/evidence/task-1-login-fail.json
  ```

  **Commit**: YES
  - Message: `feat(auth): add JWT auth infrastructure with login/refresh/me endpoints`
  - Files: `requirements.txt, src/api/auth.py, src/api/schemas/auth.py`

- [ ] 2. 认证中间件

  **What to do**:
  - 创建 `src/api/middleware.py`:
    - JWTAuthMiddleware 验证 Authorization: Bearer token
    - 提取用户信息注入 request.state.user
    - 定义免认证路径: /health, /feishu/*, /api/auth/login, /api/auth/refresh, /docs, /openapi.json
  - 创建 `src/api/dependencies.py`:
    - get_current_user() 依赖注入
    - require_role("boss") 装饰器
  - 修改 `src/api/main.py`:
    - 添加中间件
    - 保护 /api/system/stop 和 /api/system/resume 仅 boss 可访问

  **Must NOT do**:
  - 不修改 /feishu/* 路由逻辑
  - 不使用 session-based 认证

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T1)
  - **Blocks**: T3, T4, T5, T6
  - **Blocked By**: T1

  **References**:
  - `src/api/auth.py` (T1 产出) - JWT 验证函数
  - `src/api/main.py:feishu_webhook` - 保持不变的路由

  **Acceptance Criteria**:
  - [ ] src/api/middleware.py 存在
  - [ ] src/api/dependencies.py 存在
  - [ ] /api/system/stop 需要 boss 角色

  **QA Scenarios**:
  ```
  Scenario: 未认证访问 /api/system/status 返回 401
    Tool: Bash (curl)
    Steps:
      1. curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/system/status
    Expected Result: HTTP 401
    Evidence: .sisyphus/evidence/task-2-unauth-401.txt

  Scenario: Operator 访问 /api/system/stop 返回 403
    Tool: Bash (curl)
    Preconditions: 获取 operator 的 JWT token
    Steps:
      1. TOKEN=$(curl -s -X POST .../api/auth/login -d '{"username":"op1",...}' | jq -r '.access_token')
      2. curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/system/stop -H "Authorization: Bearer $TOKEN" -d '{"reason":"test"}'
    Expected Result: HTTP 403
    Evidence: .sisyphus/evidence/task-2-operator-403.txt

  Scenario: Boss 访问 /api/system/stop 返回 200
    Tool: Bash (curl)
    Steps:
      1. TOKEN=$(curl -s -X POST .../api/auth/login -d '{"username":"boss",...}' | jq -r '.access_token')
      2. curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/system/stop -H "Authorization: Bearer $TOKEN" -d '{"reason":"test"}'
    Expected Result: HTTP 200
    Evidence: .sisyphus/evidence/task-2-boss-200.txt
  ```

  **Commit**: YES
  - Message: `feat(auth): add JWT middleware protecting all /api/* routes`
  - Files: `src/api/middleware.py, src/api/dependencies.py, src/api/main.py`

- [ ] 3. 认证测试

  **What to do**:
  - 创建 `tests/api/test_auth.py`:
    - test_login_success - 有效凭证登录
    - test_login_invalid_password - 无效密码
    - test_login_invalid_username - 无效用户名
    - test_token_refresh - Token 刷新
    - test_me_endpoint - 获取当前用户
    - test_expired_token - 过期 Token
  - 创建 `tests/api/conftest.py`:
    - 认证测试 fixtures: boss_token, operator_token
    - TestClient 配置

  **Must NOT do**:
  - 不在测试中硬编码真实密码

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T1, T2)
  - **Blocks**: None
  - **Blocked By**: T1, T2

  **References**:
  - `tests/` - 现有测试结构
  - `src/api/auth.py` (T1) - 被测试的代码
  - `src/api/middleware.py` (T2) - 被测试的代码

  **Acceptance Criteria**:
  - [ ] tests/api/test_auth.py 存在且包含 6+ 测试用例
  - [ ] pytest tests/api/test_auth.py 全部通过
  - [ ] 覆盖率 ≥ 80%

  **QA Scenarios**:
  ```
  Scenario: 运行认证测试套件
    Tool: Bash
    Steps:
      1. cd /app && pytest tests/api/test_auth.py -v --cov=src/api/auth --cov=src/api/middleware
    Expected Result: 6+ tests passed, coverage ≥ 80%
    Evidence: .sisyphus/evidence/task-3-pytest-auth.txt
  ```

  **Commit**: YES
  - Message: `test(auth): add pytest tests for login, token, role enforcement`
  - Files: `tests/api/test_auth.py, tests/api/conftest.py`

- [ ] 4. Agent 触发 API

  **What to do**:
  - 创建 `src/api/agents.py` 路由器:
    - POST `/api/agents/{agent_type}/run` - 异步触发 Agent
      - agent_type: selection, listing, competitor, persona, ad_monitor
      - 返回 HTTP 202 + { "run_id": "uuid" }
      - 使用 FastAPI BackgroundTasks 执行
      - 记录到 agent_runs 表
    - 创建 run_agent_background() 函数包装各 Agent 的 execute/run
  - 创建 `src/api/schemas/agents.py`:
    - AgentRunRequest (可选参数)
    - AgentRunResponse (run_id)
    - AgentType enum
  - 添加并发控制: 同一 agent_type 同时只能有一个运行中

  **Must NOT do**:
  - 不引入 Celery
  - 不做 WebSocket 推送
  - 不同步等待 Agent 完成

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after T2)
  - **Parallel Group**: Wave 2 (with T5)
  - **Blocks**: T6, T10
  - **Blocked By**: T2

  **References**:
  - `src/agents/selection_agent/__init__.py` - run() 函数签名
  - `src/agents/listing_agent/__init__.py` - run() 函数签名
  - `src/agents/competitor_agent/__init__.py` - execute() 函数签名
  - `src/agents/persona_agent/__init__.py` - execute() 函数签名
  - `src/agents/ad_monitor_agent/__init__.py` - execute() 函数签名
  - `src/db/models.py:AgentRun` - agent_runs 表模型

  **Acceptance Criteria**:
  - [ ] src/api/agents.py 存在
  - [ ] POST /api/agents/selection/run 返回 202 + run_id
  - [ ] agent_runs 表记录新的运行

  **QA Scenarios**:
  ```
  Scenario: 触发 Selection Agent
    Tool: Bash (curl)
    Preconditions: 已登录获取 TOKEN
    Steps:
      1. curl -s -X POST http://localhost:8000/api/agents/selection/run -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"dry_run": true}'
      2. 解析响应获取 run_id
    Expected Result: HTTP 202, 响应包含 run_id (UUID 格式)
    Evidence: .sisyphus/evidence/task-4-agent-trigger.json

  Scenario: 并发限制 - 同类型 Agent 不能同时运行
    Tool: Bash (curl)
    Steps:
      1. 触发 selection agent (后台运行中)
      2. 立即再次触发 selection agent
    Expected Result: HTTP 409 Conflict, "Agent selection is already running"
    Evidence: .sisyphus/evidence/task-4-agent-conflict.json
  ```

  **Commit**: YES
  - Message: `feat(agents-api): add POST /api/agents/{type}/run endpoint`
  - Files: `src/api/agents.py, src/api/schemas/agents.py`

- [ ] 5. Agent 状态查询 API

  **What to do**:
  - 在 `src/api/agents.py` 添加:
    - GET `/api/agents/runs/{run_id}` - 查询单次运行状态
      - 返回: status (running/success/failed), result, error, started_at, completed_at
    - GET `/api/agents/runs` - 列出最近运行 (分页)
      - 参数: limit, offset, agent_type, status
  - 创建 `src/api/schemas/agents.py` 补充:
    - AgentRunStatus
    - AgentRunDetail
    - AgentRunList

  **Must NOT do**:
  - 不返回完整 LLM 输出（敏感）
  - 不做实时推送

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after T2)
  - **Parallel Group**: Wave 2 (with T4)
  - **Blocks**: T6, T9, T10
  - **Blocked By**: T2

  **References**:
  - `src/db/models.py:AgentRun` - 数据模型
  - `src/api/agents.py` (T4) - 同一文件

  **Acceptance Criteria**:
  - [ ] GET /api/agents/runs/{run_id} 返回运行状态
  - [ ] GET /api/agents/runs 返回分页列表

  **QA Scenarios**:
  ```
  Scenario: 查询运行状态
    Tool: Bash (curl)
    Preconditions: 已触发 Agent 获取 run_id
    Steps:
      1. curl -s http://localhost:8000/api/agents/runs/$RUN_ID -H "Authorization: Bearer $TOKEN"
    Expected Result: HTTP 200, 包含 status, started_at 字段
    Evidence: .sisyphus/evidence/task-5-agent-status.json

  Scenario: 列出最近运行
    Tool: Bash (curl)
    Steps:
      1. curl -s "http://localhost:8000/api/agents/runs?limit=10" -H "Authorization: Bearer $TOKEN"
    Expected Result: HTTP 200, 返回数组
    Evidence: .sisyphus/evidence/task-5-agent-list.json
  ```

  **Commit**: YES
  - Message: `feat(agents-api): add GET /api/agents/runs endpoints`
  - Files: `src/api/agents.py, src/api/schemas/agents.py`

- [ ] 6. Agent API 测试

  **What to do**:
  - 创建 `tests/api/test_agents.py`:
    - test_trigger_selection_agent
    - test_trigger_listing_agent
    - test_trigger_competitor_agent
    - test_trigger_persona_agent
    - test_trigger_ad_monitor_agent
    - test_get_run_status
    - test_list_runs
    - test_concurrent_run_rejected
    - test_unauthorized_trigger

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T4, T5)
  - **Blocks**: None
  - **Blocked By**: T4, T5

  **References**:
  - `tests/api/conftest.py` (T3) - 测试 fixtures
  - `src/api/agents.py` (T4, T5) - 被测试代码

  **Acceptance Criteria**:
  - [ ] tests/api/test_agents.py 存在且包含 9+ 测试
  - [ ] pytest tests/api/test_agents.py 全部通过

  **QA Scenarios**:
  ```
  Scenario: 运行 Agent API 测试
    Tool: Bash
    Steps:
      1. pytest tests/api/test_agents.py -v --cov=src/api/agents
    Expected Result: 9+ tests passed
    Evidence: .sisyphus/evidence/task-6-pytest-agents.txt
  ```

  **Commit**: YES
  - Message: `test(agents-api): add pytest tests for agent trigger and status`
  - Files: `tests/api/test_agents.py`

- [ ] 7. Next.js 脚手架 + 认证

  **What to do**:
  - 在项目根目录创建 `frontend/` 目录
  - 使用 Next.js 14 App Router 初始化:
    ```bash
    npx create-next-app@14 frontend --typescript --tailwind --app --no-src-dir
    ```
  - 配置:
    - TypeScript strict mode
    - Tailwind CSS
    - ESLint
  - 创建认证相关:
    - `frontend/lib/auth.ts` - JWT 存储 (httpOnly cookie)
    - `frontend/lib/api.ts` - API 客户端 (fetch wrapper with auth)
    - `frontend/middleware.ts` - 路由保护 (未登录重定向到 /login)
    - `frontend/contexts/AuthContext.tsx` - 认证上下文
  - 创建布局:
    - `frontend/app/layout.tsx` - 根布局
    - `frontend/components/Navbar.tsx` - 导航栏
    - `frontend/components/Sidebar.tsx` - 侧边栏

  **Must NOT do**:
  - 不使用 Redux/Zustand（用 React Context + TanStack Query）
  - 不做响应式 PWA

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: 前端脚手架和认证是 UI 工程核心
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T4, T5 API ready)
  - **Blocks**: T8, T9, T10, T11, T12
  - **Blocked By**: T4, T5

  **References**:
  - Next.js 14 文档: https://nextjs.org/docs/app
  - 现有后端 API: src/api/auth.py (T1), src/api/agents.py (T4, T5)

  **Acceptance Criteria**:
  - [ ] frontend/ 目录存在
  - [ ] npm run build 成功
  - [ ] middleware.ts 重定向未认证用户

  **QA Scenarios**:
  ```
  Scenario: Next.js 构建成功
    Tool: Bash
    Steps:
      1. cd frontend && npm install && npm run build
    Expected Result: 构建成功，无错误
    Evidence: .sisyphus/evidence/task-7-nextjs-build.txt

  Scenario: 未认证访问 /dashboard 重定向
    Tool: Playwright
    Steps:
      1. 直接访问 http://localhost:3000/dashboard
    Expected Result: 重定向到 /login
    Evidence: .sisyphus/evidence/task-7-auth-redirect.png
  ```

  **Commit**: YES
  - Message: `feat(frontend): scaffold Next.js 14 app with auth infrastructure`
  - Files: `frontend/*`

- [ ] 8. 登录页面

  **What to do**:
  - 创建 `frontend/app/login/page.tsx`:
    - 登录表单 (用户名、密码)
    - 调用 POST /api/auth/login
    - 成功后重定向到 /dashboard
    - 错误提示
  - 创建 `frontend/app/login/layout.tsx`:
    - 无侧边栏的简洁布局
  - 样式: Tailwind CSS，简洁专业风格

  **Must NOT do**:
  - 不做"记住我"功能
  - 不做密码重置

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after T7)
  - **Parallel Group**: Wave 3 (with T9, T10, T11)
  - **Blocks**: T12
  - **Blocked By**: T7

  **References**:
  - `frontend/lib/auth.ts` (T7) - 认证函数
  - `frontend/lib/api.ts` (T7) - API 客户端

  **Acceptance Criteria**:
  - [ ] /login 页面渲染
  - [ ] 有效凭证登录成功跳转 /dashboard
  - [ ] 无效凭证显示错误提示

  **QA Scenarios**:
  ```
  Scenario: 成功登录
    Tool: Playwright
    Steps:
      1. 打开 http://localhost:3000/login
      2. 输入用户名 "boss", 密码 "test123"
      3. 点击登录按钮
    Expected Result: 跳转到 /dashboard
    Evidence: .sisyphus/evidence/task-8-login-success.png

  Scenario: 失败登录显示错误
    Tool: Playwright
    Steps:
      1. 打开 /login
      2. 输入错误密码
      3. 点击登录
    Expected Result: 显示"用户名或密码错误"
    Evidence: .sisyphus/evidence/task-8-login-error.png
  ```

  **Commit**: YES
  - Message: `feat(frontend): add login page with form and validation`
  - Files: `frontend/app/login/*`

- [ ] 9. 仪表盘页面

  **What to do**:
  - 创建 `frontend/app/dashboard/page.tsx`:
    - 系统状态卡片 (调用 /api/system/status)
    - 最近 Agent 运行列表 (调用 /api/agents/runs?limit=5)
    - 调度任务列表 (调用 /api/scheduler/jobs)
    - LLM 费用统计卡片 (如果后端支持)
  - 使用 TanStack Query (React Query) 获取数据
  - 自动刷新 (30 秒轮询)

  **Must NOT do**:
  - 不做复杂图表（简单数字卡片即可）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after T7)
  - **Parallel Group**: Wave 3
  - **Blocks**: T12
  - **Blocked By**: T7, T5

  **References**:
  - `src/api/system.py` - /api/system/status
  - `src/api/agents.py` (T5) - /api/agents/runs
  - `src/api/main.py` - /api/scheduler/jobs

  **Acceptance Criteria**:
  - [ ] /dashboard 页面渲染
  - [ ] 显示系统状态
  - [ ] 显示最近 Agent 运行

  **QA Scenarios**:
  ```
  Scenario: 仪表盘显示数据
    Tool: Playwright
    Preconditions: 已登录
    Steps:
      1. 访问 /dashboard
      2. 等待数据加载
    Expected Result: 显示系统状态、Agent 运行列表、调度任务
    Evidence: .sisyphus/evidence/task-9-dashboard.png
  ```

  **Commit**: YES
  - Message: `feat(frontend): add dashboard page with status cards`
  - Files: `frontend/app/dashboard/*`

- [ ] 10. Agent 触发页面

  **What to do**:
  - 创建 `frontend/app/agents/page.tsx`:
    - Agent 列表概览 (5 个 Agent 卡片)
  - 为每个 Agent 创建独立页面:
    - `frontend/app/agents/selection/page.tsx`
    - `frontend/app/agents/listing/page.tsx`
    - `frontend/app/agents/competitor/page.tsx`
    - `frontend/app/agents/persona/page.tsx`
    - `frontend/app/agents/ad-monitor/page.tsx`
  - 每个页面包含:
    - Agent 描述
    - 输入参数表单 (如 ASIN, category)
    - "运行" 按钮
    - 运行状态显示 (轮询 /api/agents/runs/{id})
    - 结果展示

  **Must NOT do**:
  - 不做可视化工作流编辑器

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after T7)
  - **Parallel Group**: Wave 3
  - **Blocks**: T12
  - **Blocked By**: T7, T4, T5

  **References**:
  - `src/api/agents.py` (T4, T5) - Agent API
  - `src/agents/*/` - 各 Agent 参数

  **Acceptance Criteria**:
  - [ ] /agents 页面显示 5 个 Agent
  - [ ] 每个 Agent 页面可触发运行
  - [ ] 运行状态实时更新

  **QA Scenarios**:
  ```
  Scenario: 触发 Selection Agent
    Tool: Playwright
    Preconditions: 已登录
    Steps:
      1. 访问 /agents/selection
      2. 勾选 dry_run
      3. 点击"运行"按钮
      4. 等待状态更新
    Expected Result: 显示"运行中" -> "完成"，展示结果
    Evidence: .sisyphus/evidence/task-10-agent-run.png
  ```

  **Commit**: YES
  - Message: `feat(frontend): add agent trigger pages for all 5 agents`
  - Files: `frontend/app/agents/*`

- [ ] 11. 系统管理页面

  **What to do**:
  - 创建 `frontend/app/system/page.tsx`:
    - 紧急停机按钮 (调用 POST /api/system/stop) - 仅 boss 可见
    - 恢复系统按钮 (调用 POST /api/system/resume) - 仅 boss 可见
    - 审计日志列表 (调用 GET /api/system/audit-logs) - 仅 boss 可见
    - 当前用户角色显示
  - 角色检查: operator 访问显示"无权限"提示

  **Must NOT do**:
  - 不做用户管理功能

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after T7)
  - **Parallel Group**: Wave 3
  - **Blocks**: T12
  - **Blocked By**: T7, T2

  **References**:
  - `src/api/system.py` - 系统管理 API
  - `frontend/contexts/AuthContext.tsx` (T7) - 用户角色

  **Acceptance Criteria**:
  - [ ] Boss 用户看到紧急停机按钮
  - [ ] Operator 用户看到"无权限"
  - [ ] 审计日志正确显示

  **QA Scenarios**:
  ```
  Scenario: Boss 访问系统管理
    Tool: Playwright
    Preconditions: 以 boss 登录
    Steps:
      1. 访问 /system
    Expected Result: 显示紧急停机按钮、审计日志
    Evidence: .sisyphus/evidence/task-11-system-boss.png

  Scenario: Operator 访问系统管理
    Tool: Playwright
    Preconditions: 以 operator 登录
    Steps:
      1. 访问 /system
    Expected Result: 显示"您没有权限访问此页面"
    Evidence: .sisyphus/evidence/task-11-system-operator.png
  ```

  **Commit**: YES
  - Message: `feat(frontend): add system management page with role-based access`
  - Files: `frontend/app/system/*`

- [ ] 12. 前端 E2E 测试

  **What to do**:
  - 安装 Playwright: `npm install -D @playwright/test`
  - 创建 `frontend/playwright.config.ts`
  - 创建测试:
    - `frontend/tests/auth.spec.ts` - 登录流程测试
    - `frontend/tests/dashboard.spec.ts` - 仪表盘测试
    - `frontend/tests/agents.spec.ts` - Agent 触发测试
    - `frontend/tests/system.spec.ts` - 系统管理测试

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`playwright`]

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T8-T11)
  - **Blocks**: T16
  - **Blocked By**: T8, T9, T10, T11

  **References**:
  - `frontend/app/*` (T8-T11) - 被测试页面
  - Playwright 文档

  **Acceptance Criteria**:
  - [ ] npx playwright test 全部通过
  - [ ] 覆盖登录、仪表盘、Agent、系统管理

  **QA Scenarios**:
  ```
  Scenario: 运行 E2E 测试
    Tool: Bash
    Steps:
      1. cd frontend && npx playwright test
    Expected Result: 所有测试通过
    Evidence: .sisyphus/evidence/task-12-playwright.txt
  ```

  **Commit**: YES
  - Message: `test(e2e): add Playwright tests for auth, dashboard, agents, system`
  - Files: `frontend/tests/*, frontend/playwright.config.ts`

- [ ] 13. Nginx 配置更新

  **What to do**:
  - 修改 `deploy/nginx/nginx.conf`:
    - 添加 upstream 块: api (FastAPI:8000), frontend (Next.js:3000)
    - location /api/ → proxy_pass http://api
    - location /feishu/ → proxy_pass http://api (保持不变)
    - location /health → proxy_pass http://api
    - location / → proxy_pass http://frontend
    - 添加 WebSocket 支持 (Next.js HMR)
    - 添加 gzip 压缩
  - 配置 SSL (占位，T15 完成):
    - listen 443 ssl
    - ssl_certificate /etc/letsencrypt/live/siqiangshangwu.com/fullchain.pem
    - ssl_certificate_key /etc/letsencrypt/live/siqiangshangwu.com/privkey.pem
    - HTTP 80 重定向到 HTTPS

  **Must NOT do**:
  - 不改变 /feishu/* 的路由逻辑
  - 不引入 CDN 或负载均衡器

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after T7)
  - **Blocks**: T16
  - **Blocked By**: T7

  **References**:
  - `deploy/nginx/nginx.conf` - 现有配置

  **Acceptance Criteria**:
  - [ ] nginx.conf 包含 api 和 frontend upstream
  - [ ] /api/* 路由到 FastAPI
  - [ ] / 路由到 Next.js
  - [ ] /feishu/* 继续工作

  **QA Scenarios**:
  ```
  Scenario: Nginx 配置语法检查
    Tool: Bash
    Steps:
      1. nginx -t -c deploy/nginx/nginx.conf
    Expected Result: syntax is ok
    Evidence: .sisyphus/evidence/task-13-nginx-syntax.txt
  ```

  **Commit**: YES
  - Message: `feat(deploy): update nginx config for Next.js + FastAPI routing`
  - Files: `deploy/nginx/nginx.conf`

- [ ] 14. Docker Compose 更新

  **What to do**:
  - 修改 `deploy/docker/docker-compose.yml`:
    - 添加 frontend 服务:
      ```yaml
      frontend:
        build:
          context: ../../frontend
          dockerfile: Dockerfile
        ports:
          - "127.0.0.1:3000:3000"
        environment:
          - NEXT_PUBLIC_API_URL=http://localhost:8000
        depends_on:
          - app
      ```
  - 创建 `frontend/Dockerfile`:
    - Node.js 20 alpine 镜像
    - npm ci --production
    - npm run build
    - npm start

  **Must NOT do**:
  - 不引入 Kubernetes

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after T7)
  - **Blocks**: T16
  - **Blocked By**: T7

  **References**:
  - `deploy/docker/docker-compose.yml` - 现有配置
  - `frontend/` (T7) - 前端代码

  **Acceptance Criteria**:
  - [ ] docker-compose.yml 包含 frontend 服务
  - [ ] frontend/Dockerfile 存在
  - [ ] docker compose build 成功

  **QA Scenarios**:
  ```
  Scenario: Docker 构建前端
    Tool: Bash
    Steps:
      1. docker compose -f deploy/docker/docker-compose.yml build frontend
    Expected Result: 构建成功
    Evidence: .sisyphus/evidence/task-14-docker-build.txt
  ```

  **Commit**: YES
  - Message: `feat(deploy): add frontend service to docker-compose`
  - Files: `deploy/docker/docker-compose.yml, frontend/Dockerfile`

- [ ] 15. SSL 证书配置

  **What to do**:
  - 创建 `deploy/scripts/setup-ssl.sh`:
    - 检查 DNS 记录
    - 安装 certbot (如未安装)
    - 运行 certbot --nginx -d siqiangshangwu.com
    - 配置自动续期
  - 创建 `docs/deployment-ssl.md`:
    - 前置条件 (DNS A 记录)
    - 手动执行步骤
    - 故障排除

  **Must NOT do**:
  - 不自动执行 certbot (需要确认 DNS)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Blocks**: T16
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] setup-ssl.sh 存在且可执行
  - [ ] docs/deployment-ssl.md 存在

  **QA Scenarios**:
  ```
  Scenario: SSL 脚本语法检查
    Tool: Bash
    Steps:
      1. bash -n deploy/scripts/setup-ssl.sh
    Expected Result: 无语法错误
    Evidence: .sisyphus/evidence/task-15-ssl-syntax.txt
  ```

  **Commit**: YES
  - Message: `feat(deploy): add SSL setup script and documentation`
  - Files: `deploy/scripts/setup-ssl.sh, docs/deployment-ssl.md`

- [ ] 16. 部署脚本 + 验证

  **What to do**:
  - 创建 `deploy/scripts/deploy-phase3.sh`:
    - 停止现有服务
    - 拉取最新代码
    - 构建 Docker 镜像 (app + frontend)
    - 更新 nginx 配置
    - 重启服务
    - 运行健康检查
  - 创建 `deploy/scripts/verify-deployment.sh`:
    - 检查 HTTPS 可访问
    - 检查 HTTP 重定向
    - 检查 /health 返回 200
    - 检查 /api/system/status 返回 401 (未认证)
    - 检查 /feishu/webhook 可用
    - 检查前端页面加载
  - 执行部署到 52.221.207.30

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (final deployment)
  - **Blocks**: F1-F4
  - **Blocked By**: T12, T13, T14, T15

  **References**:
  - `deploy/scripts/deploy.sh` - 现有部署脚本参考
  - 服务器: ubuntu@52.221.207.30

  **Acceptance Criteria**:
  - [ ] https://siqiangshangwu.com 返回 200
  - [ ] http://siqiangshangwu.com 重定向 301
  - [ ] /api/system/status 无认证返回 401
  - [ ] /feishu/webhook 仍工作
  - [ ] 登录流程正常

  **QA Scenarios**:
  ```
  Scenario: 完整部署验证
    Tool: Bash (curl)
    Steps:
      1. curl -s -o /dev/null -w "%{http_code}" https://siqiangshangwu.com/
      2. curl -s -o /dev/null -w "%{http_code}" http://siqiangshangwu.com/
      3. curl -s -o /dev/null -w "%{http_code}" https://siqiangshangwu.com/api/system/status
      4. curl -s https://siqiangshangwu.com/feishu/webhook -X POST -d '{"type":"url_verification","challenge":"test"}'
    Expected Result: 200, 301, 401, {"challenge":"test"}
    Evidence: .sisyphus/evidence/task-16-verify-all.txt
  ```

  **Commit**: YES
  - Message: `feat(deploy): add deployment and verification scripts`
  - Files: `deploy/scripts/deploy-phase3.sh, deploy/scripts/verify-deployment.sh`

- [ ] 17. 凭证配置文档

  **What to do**:
  - 创建 `docs/credentials-setup.md`:
    - SP-API 凭证配置指南
    - 广告 API 凭证配置指南
    - OpenAI API Key 配置
    - WEB_USERS 配置 (如何生成 bcrypt hash)
    - JWT_SECRET 配置
    - 配置验证步骤
  - 更新 `.env.example`:
    - 添加所有 Phase 3 新增环境变量
    - 添加注释说明

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Blocks**: None
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] docs/credentials-setup.md 存在
  - [ ] .env.example 包含所有新变量

  **QA Scenarios**:
  ```
  Scenario: 文档完整性检查
    Tool: Bash
    Steps:
      1. grep -c "SP_API" docs/credentials-setup.md
      2. grep -c "WEB_USERS" docs/credentials-setup.md
      3. grep -c "JWT_SECRET" .env.example
    Expected Result: 每个命令返回 >= 1
    Evidence: .sisyphus/evidence/task-17-docs-check.txt
  ```

  **Commit**: YES
  - Message: `docs(deploy): add credentials setup guide`
  - Files: `docs/credentials-setup.md, .env.example`

- [ ] 18. DNS 配置（部署前必须完成）

  **What to do**:
  - 这是一个**手动操作任务**，需要你在域名服务商后台完成
  - 域名: siqiangshangwu.com
  - 目标 IP: 52.221.207.30
  - 操作步骤见下方详细说明

  **DNS 修改步骤**:
  1. 登录你的域名服务商后台（购买域名的地方）
  2. 找到 DNS 管理 / 域名解析 设置
  3. 删除或修改现有的 A 记录（当前指向 GitHub 185.199.x.x）
  4. 添加新的 A 记录:
     - 主机记录: @ (或留空)
     - 记录类型: A
     - 记录值: 52.221.207.30
     - TTL: 600 (10分钟) 或默认值
  5. 如果需要 www 子域名，也添加:
     - 主机记录: www
     - 记录类型: A
     - 记录值: 52.221.207.30
  6. 保存并等待 DNS 生效（通常 10-30 分钟，最长 24 小时）

  **验证 DNS 是否生效**:
  ```bash
  # Windows PowerShell
  nslookup siqiangshangwu.com
  # 期望看到: Address: 52.221.207.30

  # 或使用在线工具
  # https://www.whatsmydns.net/#A/siqiangshangwu.com
  ```

  **Must NOT do**:
  - 不要删除其他 DNS 记录（如 MX 邮件记录）
  - 不要修改 NS 记录

  **Recommended Agent Profile**:
  - **Category**: 手动操作 - 无需 Agent
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (可与开发并行)
  - **Blocks**: T16 (SSL 证书需要 DNS 生效)
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] nslookup siqiangshangwu.com 返回 52.221.207.30
  - [ ] curl http://52.221.207.30/health 返回 {"status":"ok"}

  **QA Scenarios**:
  ```
  Scenario: DNS 已正确配置
    Tool: Bash
    Steps:
      1. nslookup siqiangshangwu.com
    Expected Result: 返回 52.221.207.30
    Evidence: .sisyphus/evidence/task-18-dns-check.txt
  ```

  **Commit**: NO (手动操作，无代码变更)

---

## Final Verification Wave (MANDATORY — 所有实现任务完成后)

> 4 个审查 Agent 并行运行。全部必须 APPROVE。向用户呈现综合结果并获得明确"okay"后才能完成。

- [ ] F1. **计划合规审计** — `oracle`
  阅读完整计划。对每个"Must Have"：验证实现存在（读取文件、curl 端点、运行命令）。对每个"Must NOT Have"：搜索代码库中的禁止模式——如发现则拒绝并给出 file:line。检查 .sisyphus/evidence/ 中的证据文件存在。将交付物与计划对比。
  输出: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **代码质量审查** — `unspecified-high`
  运行 `tsc --noEmit`（前端）+ linter + `pytest`（后端）。审查所有变更文件：`as any`/`@ts-ignore`、空 catch、console.log in prod、注释掉的代码、未使用的导入。检查 AI 垃圾代码：过度注释、过度抽象、通用命名（data/result/item/temp）。
  输出: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **实际 QA 验证** — `unspecified-high` (+ `playwright` skill)
  从干净状态开始。执行每个任务的每个 QA 场景——按照精确步骤，捕获证据。测试跨任务集成（功能协同工作）。测试边缘情况：空状态、无效输入、快速操作。保存到 `.sisyphus/evidence/final-qa/`。
  输出: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **范围保真度检查** — `deep`
  对每个任务：阅读"What to do"，阅读实际 diff (git log/diff)。验证 1:1——规格中的一切都已构建（无遗漏），规格外的一切都未构建（无蔓延）。检查"Must NOT do"合规性。检测跨任务污染：任务 N 触及任务 M 的文件。标记未说明的变更。
  输出: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

| # | Commit Message | Files |
|---|----------------|-------|
| 1 | feat(auth): add JWT auth infrastructure | src/api/auth.py, requirements.txt |
| 2 | feat(auth): add auth middleware | src/api/middleware.py, src/api/main.py |
| 3 | test(auth): add pytest tests for auth | tests/api/test_auth.py |
| 4 | feat(agents-api): add agent trigger endpoint | src/api/agents.py |
| 5 | feat(agents-api): add agent status endpoint | src/api/agents.py |
| 6 | test(agents-api): add agent API tests | tests/api/test_agents.py |
| 7 | feat(frontend): scaffold Next.js 14 app | frontend/* |
| 8 | feat(frontend): add login page | frontend/app/login/* |
| 9 | feat(frontend): add dashboard page | frontend/app/dashboard/* |
| 10 | feat(frontend): add agent pages | frontend/app/agents/* |
| 11 | feat(frontend): add system page | frontend/app/system/* |
| 12 | test(e2e): add Playwright tests | frontend/tests/* |
| 13 | feat(deploy): update nginx config | deploy/nginx/nginx.conf |
| 14 | feat(deploy): update docker-compose | deploy/docker/docker-compose.yml |
| 15 | docs(deploy): add SSL setup guide | docs/deployment.md |

---

## Success Criteria

### 验证命令
```bash
# 认证层
curl -s -o /dev/null -w "%{http_code}" https://siqiangshangwu.com/api/system/status
# Expected: 401

curl -s -X POST https://siqiangshangwu.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "boss", "password": "PASSWORD"}' | jq '.access_token'
# Expected: eyJ... (JWT token)

# Agent API
curl -s -X POST https://siqiangshangwu.com/api/agents/selection/run \
  -H "Authorization: Bearer $TOKEN" | jq '.run_id'
# Expected: valid UUID

# 部署
curl -s -o /dev/null -w "%{http_code}" https://siqiangshangwu.com/
# Expected: 200

curl -s -o /dev/null -w "%{http_code}" http://siqiangshangwu.com/
# Expected: 301

# 飞书 Webhook
curl -s -X POST https://siqiangshangwu.com/feishu/webhook \
  -H "Content-Type: application/json" \
  -d '{"type":"url_verification","challenge":"test"}' | jq '.challenge'
# Expected: "test"
```

### 最终检查清单
- [ ] 所有"Must Have"存在
- [ ] 所有"Must NOT Have"不存在
- [ ] pytest 测试全部通过
- [ ] Playwright E2E 测试全部通过
- [ ] SSL 证书有效
- [ ] 飞书 Webhook 正常工作
