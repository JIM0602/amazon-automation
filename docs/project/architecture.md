# PUDIWIND 亚马逊自动化运营系统架构说明

## 1. 总体架构
系统采用前后端分离架构：
- 前端：React 19 + TypeScript + Vite，负责工作台页面、路由与交互
- 后端：FastAPI，负责鉴权、业务 API、Agent 调用、审批与调度
- 数据层：PostgreSQL + pgvector，承载业务数据、知识库、审计与对话
- 部署层：Docker Compose，统一编排 app / nginx / postgres

当前整体运行模式为：
`Browser -> Nginx -> FastAPI -> Mock 数据 / PostgreSQL / LLM / 外部集成`

## 2. 前端结构
主前端位于 `src/frontend/`：
- `src/frontend/src/App.tsx`：路由总入口
- `src/frontend/src/components/`：布局、侧边栏、路由保护、表格等通用组件
- `src/frontend/src/pages/`：业务页面
- `src/frontend/src/pages/system/`：系统管理独立子页
- `src/frontend/src/api/client.ts`：Axios 实例，`baseURL=/api`
- `src/frontend/src/contexts/`：认证与主题上下文

前端约束：
- 组件中请求路径不能重复写 `/api`
- Boss 专属页面必须继续通过 `ProtectedRoute requiredRole="boss"` 保护
- API key 只展示状态，不允许在前端录入、保存或透传真实值

## 3. 后端结构
主后端位于 `src/api/` 与 `src/services/`：
- `src/api/main.py`：FastAPI 应用入口与聚合路由
- `src/api/auth.py`：JWT 登录、刷新、当前用户信息
- `src/api/middleware.py`：JWT 中间件，给 `request.state.user` 注入用户信息
- `src/api/dependencies.py`：`get_current_user` 与 `require_role`
- `src/api/chat.py`：聊天与 SSE 接口
- `src/api/dashboard.py` / `ads.py` / `orders.py` / `returns.py`：业务 Mock API
- `src/api/approvals.py` / `kb_review.py` / `system.py` / `monitoring.py`：审批与系统管理能力

## 4. 认证与权限
### JWT
- 登录端点：`POST /api/auth/login`
- 刷新端点：`POST /api/auth/refresh`
- 当前用户：`GET /api/auth/me`
- JWT payload 包含 `sub`、`role`、`type`

### 请求路径保护
- 公开路径只包括健康检查、登录、刷新、文档与飞书回调
- 其他 `/api/*` 请求默认经过 `JWTAuthMiddleware`
- 更细粒度的角色限制通过 `require_role()` 完成

### 权限边界
- `boss`：可访问系统管理、知识库审核、Boss 专属 Agent
- `operator`：仅可访问日常运营与普通 Agent 能力

## 5. 数据与业务流
### Mock-first
当前订单、退货、广告、看板等业务数据主要由 `data/mock/` 生成，目标是先验证页面交互、字段口径与流程完整性。

### 数据库存储
`src/db/models.py` 已定义核心实体，包括但不限于：
- `users`
- `documents` / `document_chunks`
- `products`
- `agent_runs` / `agent_tasks`
- `approval_requests`
- `daily_reports`
- `system_config`
- `audit_logs`
- `conversations` / `chat_messages`

数据库仍是后续真实集成的稳定承载面，但当前并不要求所有业务流程都已接入真实表读写。

## 6. Agent、审批与知识库
- Agent 调用由后端统一发起，前端只作为入口与展示层
- 聊天能力通过 `POST /api/chat/{agent_type}/stream` 提供 SSE 输出
- 审批中心负责承接需人工确认的动作
- 知识库与 RAG 已有基础设施，但当前更多是平台能力底座而非完整运营闭环

## 7. 调度器架构
调度能力由 APScheduler 提供：
- `src/scheduler/config.py`：定义预置任务配置
- `src/scheduler/__init__.py`：提供 scheduler 单例、启动与关闭逻辑
- `src/api/main.py`：暴露调度器查询、暂停、恢复、手动触发接口

当前已存在的 API：
- `GET /api/scheduler/jobs`
- `POST /api/scheduler/jobs/{job_id}/pause`
- `POST /api/scheduler/jobs/{job_id}/resume`
- `POST /api/scheduler/trigger/{job_id}`

因此计划任务能力当前缺的不是后端接口，而是前端独立页面接入。

## 8. 安全约束
- 本系统默认是公司内部私有系统，涉及敏感业务数据
- API key 只能放在服务端环境变量，不进前端、不进仓库
- 后端必须是唯一可信边界，不能依赖前端做授权判断
- 自动化动作必须留痕，满足可审计、可追溯、可回滚
- 新增功能应优先复用现有接口与鉴权，不得为了省事绕过安全边界

## 9. 部署基线
- Docker 多阶段构建前端与后端
- Docker Compose 统一编排 `app`、`nginx`、`postgres`
- Nginx 负责静态资源与 `/api/` 转发
- 生产部署目标为 AWS EC2

## 10. 架构迭代记录
- 2026-04-22：新增正式架构基线文档。原因：当前仓库已有多份背景/历史文档，但缺少面向持续开发的正式架构事实基线，容易导致后续开发偏离当前真实实现。
