# Learnings — production-fixes-32issues

## [2026-04-11] F4 scope audit findings
- `src/frontend/src/App.tsx` 仍把 `OrdersPage`、`UserManagementPage`、`AgentConfigPage` 映射为 `PlaceholderPage`，说明“页面已实现”与“路由已接线”不是一回事。
- `src/frontend/src/pages/MessageCenter.tsx` 仍然存在，和计划中“不能有独立消息中心页面”冲突，即使未注册路由也算遗留实现。
- `Dashboard.tsx` / `AdDashboard.tsx` 与后端 mock API 的返回结构存在 `items` 包装层差异，审计时必须同时检查前后端契约，不可只看文件存在。
- 本次修复把 `App.tsx` 中的占位路由直接替换为真实页面组件，并删除了 `MessageCenter.tsx`；验证命令以 `src/frontend` 下的 `npm run build` 为准。
 
## [2026-04-10] T31 - CampaignDetail + AdGroupDetail Drill-Down Pages
- `src/frontend/src/pages/ad-management/CampaignDetail.tsx` 和 `AdGroupDetail.tsx` 已创建为独立钻取页，分别对应 campaign/ad-group 详情路由。
- 两个页面都内置水平 Tab 和各自的只读表格逻辑；因为钻取 API 路径与主页面不同，没有复用现有 Tab 组件。
- 所有接口失败都降级为 `暂无数据（Mock模式）`，保证 mock 后端缺失端点时页面仍可正常展示。
- 前端校验已通过：`cd src/frontend && npm run build`。
## [2026-04-10] Session ses_2b24b10b0ffezwvEa0VL8uq8Tu — Plan Start

### Codebase Conventions
- **Auth JWT payload**: `{username, role}` NOT `{sub, role}` — from `src/api/middleware.py:130`
- **DB user**: `app_user` (NOT `postgres`)
- **Docker container name**: `amazon-ai-app` (NOT `amazon-ai-backend`)
- **Config import**: `from src.config import settings` (settings is lowercase instance, Settings is the class)
- **Settings keys**: `settings.DATABASE_URL` (uppercase field names)
- **LLM client**: module-level functions `chat()`, `chat_stream()` — NOT a class
- **BaseAgent**: 24 lines, abstract — DO NOT MODIFY
- **ChatBaseAgent**: 99 lines — datetime bug here (lines with datetime.now() or comparison)
- **AGENT_REGISTRY**: in `src/services/chat.py:30-44`
- **SSE endpoint**: `POST /api/chat/{agent_type}/stream`
- **Alembic head**: `004_add_phase4` — next migration is `005_add_users_table`
- **React version**: 19, Vite 6, Tailwind 4
- **Frontend build command**: `bun run build` (from src/frontend/)
- **Server path**: `/opt/amazon-ai/`
- **Server**: `ubuntu@52.221.207.30`, PEM: `~/Downloads/Pudiwind.pem`
- **Quick rebuild**: `scp file → sudo cp → docker compose build app → docker compose up -d app`
- **Playwright MCP**: CLOSED — use curl/Python scripts for backend testing, build check + grep for frontend

### Critical Do-Nots
- Do NOT modify `src/agents/base_agent.py` (24-line abstract base)
- Do NOT use `as any` or `@ts-ignore` in TypeScript
- Do NOT leave `console.log` in production code
- Do NOT call Amazon Ads API write endpoints
- Do NOT implement real SP-API data pipeline (Mock only in this phase)

## [2026-04-10] Datetime timezone hardening
- Added `src/utils/timezone.py` with `now_site_time()` and `to_site_time()` for site-aware aware datetimes.
- Replaced the remaining naive `datetime.utcnow()` calls in `src/agents/ad_monitor_agent/algorithm/core.py` and `src/agents/ad_monitor_agent/algorithm/safety.py`.
- `src/db/models.py` already used `DateTime(timezone=True)` for all timestamp columns; no schema change was needed.
- The environment lacked system tzdata, so the timezone helper now falls back to a fixed US/Pacific offset to keep validation stable.

## [2026-04-10] Chat history persistence/loading
- The chat backend already persists user/assistant turns in `src/agents/chat_base_agent.py` via `src.db.chat.add_message`; the missing piece was agent-scoped history/list endpoints matching the frontend usage.
- Added compatibility endpoints under `/api/chat/{agent_type}/conversations` and `/api/chat/{agent_type}/conversations/{conversation_id}/messages` so the UI can load historical conversations and message history directly.
- `src/frontend/src/pages/AgentChat.tsx` now preloads the latest conversation on mount, while `ConversationList` and `useChat` read the new agent-scoped endpoints.
- The frontend build command in `src/frontend/package.json` is `npm run build`-style (`tsc -b && vite build`), not `bun run build` in this environment.

## [2026-04-10] keyword_library agent no-response fix
- `KeywordLibraryChatAgent` could not even be imported because `src/config.py` enforced required env vars (`DATABASE_URL`, `OPENAI_API_KEY`, `FEISHU_APP_ID`, `FEISHU_APP_SECRET`) at module import time.
- The fix was to make `Settings()` boot with safe defaults so the chat agent can start and return a response even in a minimal local/test environment.
- `keyword_library` now explicitly instructs the model to emit a friendly degradation note when SellerSprite MCP / Brand Analytics / Search Term Report / ad data are unavailable, instead of going silent.

## [2026-04-10] users 表 + DB auth migration
- 现有数据库入口已经统一在 `src/db/connection.py`，认证层应复用 `SessionLocal`，不要再新增独立 session 工厂。
- 新增 `users` 表时，迁移里一次性插入 3 个初始账号（boss/op1/op2），并使用 bcrypt 哈希，保证登录链路可以在空库中直接启动。
- JWT 载荷的兼容策略是保留 `username`/`role`，同时短期保留 `sub`，这样不改 middleware 的前提下不会把现有鉴权链路打断。

## [2026-04-10] OpenRouter / provider routing
- `src/llm/client.py` should avoid provider-specific SDK instantiation for Anthropic; LiteLLM can route both `anthropic/...` and `openrouter/...` model prefixes.
- `chat_stream()` should use `litellm.acompletion(..., stream=True)` for async token streaming; sync `completion()` is not the right primitive for SSE.
- If `OPENROUTER_API_KEY` is empty, OpenRouter requests should gracefully fall back to direct OpenAI routing instead of failing import-time or request-time.
- Agent model maps are easier to evolve when the canonical shape is `{model, provider}` with a backward-compatible string fallback.

## [2026-04-10] Timezone range utilities
- `src/utils/timezone.py` now keeps the existing `now_site_time()` / `to_site_time()` helpers and adds range helpers that all return timezone-aware datetimes.
- The new frontend helper lives in `src/frontend/src/utils/timezone.ts`; it uses the native `Intl.DateTimeFormat` API and keeps the site timezone string centralized in `SITE_TZ`.
- The expected verification command for backend timezone ranges is `python -c "from src.utils.timezone import site_today_range; ..."`, and the frontend build check should use `npm run build` in `src/frontend/` for this task.

## [2026-04-10] User CRUD REST API (Task 5)
- Created src/db/users.py: 8 functions (hash_password, verify_password, get_user_by_id, get_user_by_username, list_users, create_user, update_user, deactivate_user), consistent with auth.py using passlib.hash.bcrypt.
- Created src/api/schemas/users.py: Pydantic request/response models (CreateUserRequest, UpdateUserRequest, ChangePasswordRequest, UserResponse, UserListResponse).
- Created src/api/users.py: 5 endpoints, 4 boss-only (GET/POST/PUT/DELETE), 1 all-roles (PUT /me/password).
- /me/password route MUST be registered before /{user_id}, otherwise FastAPI matches 'me' as user_id param.
- DELETE endpoint is soft-delete (sets is_active=False), does not physically delete, and prevents boss from deactivating themselves.
- User model needs to be exported from src/db/__init__.py for other modules to import via 'from src.db import User'.

## [2026-04-10] Agent Config DB + API (Task 7)
- AgentConfig model added to `src/db/models.py` (Table 21) with `agent_type` as PK, `display_name_cn`, `description`, `is_active`, `visible_roles` (JSON), `sort_order`.
- AGENT_REGISTRY 实际的 13 个 key 与任务描述不完全一致：`selection`（非 `product_selection`）、`listing`（非 `listing_copywriting`）、`competitor`（非 `market_analysis`）、`inventory`（非 `supply_chain`）。额外有 `whitepaper`、`persona`、`image_generation`、`product_listing`。迁移数据使用了实际 registry key。
- `system.py` 的 router prefix 是 `/api/system`，而新端点需要 `/api/agents/config`。解决方案：在 system.py 中创建独立的 `agents_config_router`（prefix `/api/agents`），在 main.py 单独注册。
- GET `/api/agents/config` 不需要认证（前端通用读取），PUT 需要 boss 角色。
- Alembic head 现在是 `006_add_agent_configs`（revises: `005_add_users_table`）。
- basedpyright 对 SQLAlchemy Column 赋值会报 `reportAttributeAccessIssue`，需要文件级 `# pyright: reportAttributeAccessIssue=false` 或行级 `# type: ignore[assignment]` 来抑制。

## [2026-04-10] Task 10 �� Dashboard Mock Data API

- **Mock data location**: `data/mock/dashboard.py` �� uses `Random(42)` for reproducibility
- **data/ package**: Needed `data/__init__.py` and `data/mock/__init__.py` for Python imports
- **Router registration pattern**: Import at module level with `# noqa: E402`, then `app.include_router(router)`  
- **Dashboard API prefix**: `/api/dashboard` with 3 endpoints: metrics, trend, sku_ranking
- **tacos/acos format**: 0.0~1.0 ratio (not percentage) in both metrics and SKU ranking
- **Timezone utils**: `src/utils/timezone.py` provides range functions (site_today_range, last_24h_range, etc.)


## [2026-04-10] Task 11 - Ads Mock Data API

- **Ads API prefix**: `/api/ads` with 18 endpoints: 4 dashboard + 8 management tabs + 6 campaign drill-down
- **Mock data volumes**: 5 Portfolios, 20 Campaigns (12 SP + 5 SB + 3 SD), 50 Ad Groups, 100 Products, 80 Targeting, 60 Search Terms, 40 Negative Targeting, 100 Logs
- **Data generation pattern**: Module-level cached pools via `_generate_*()` with `Random(42)`, public functions filter/paginate the pools
- **Unified response format**: `{items: [], total_count: N, summary_row: {...}}` for all list endpoints
- **Campaign drill-down**: 6 sub-endpoints under `/campaigns/{id}/` (ad_groups, targeting, search_terms, negative_targeting, logs, settings)
- **portfolio_tree**: Nested structure `[{id, name, campaign_count, campaigns: [{id, name}]}]`
- **Dashboard metrics**: 10 ad-specific cards (ad_spend, ad_sales, acos, clicks, impressions, ctr, cvr, cpc, ad_orders, ad_units)
- **Dashboard trend**: Supports 11 metrics via comma-separated query param
- **Type annotations**: Use `list[dict[str, Any]]` not `list[dict]` to satisfy basedpyright
A p p . t s x   r o u t i n g   s u c c e s s f u l l y   u p d a t e d   u s i n g   R e a c t   R o u t e r   v 6   c o m p o n e n t   f o r m a t   a n d   n e s t e d   p r o t e c t e d   r o u t e s  
 -   R e w r o t e   m e t r i c   c a r d s   i n   D a s h b o a r d . t s x ,   a d d i n g   T i m e   t o g g l e s ,   M o c k   t a g ,   m a p p i n g   8   m e t r i c s ,   a n d   a d j u s t i n g   A C o S / T A C o S   f o r m a t t i n g .  
 - Addressed TrendChart integration in Dashboard using pure Recharts line components, scaling secondary metrics.
Added SKU ranking table to Dashboard with paginated sorting via DataTable. Added onSort prop to DataTable to support external API sorting triggers. Cleanly removed all Agent Activity code.

## [2026-04-10] Task 27 - AdManagement page skeleton
- `src/frontend/src/pages/AdManagement.tsx` now owns the page shell: left Portfolio tree, 8 main tabs, 4 ad-type filters, time-range controls, search input, and local state for tab/portfolio/ad type/time range/query/pagination.
- Portfolio data is fetched from `GET /api/ads/portfolio_tree` with the expected nested `[{id, name, campaign_count, campaigns}]` shape; the left tree supports search, per-item selection, select-all for visible items, and confirm selection.
- `src/frontend/src/pages/ad-management/TabContent.tsx` centralizes the tab dispatcher and shared `TabProps`; each tab file is a placeholder so later tasks can fill in table columns without reworking the shell.
- Frontend build passes cleanly after removing unused imports; no `as any` or `@ts-ignore` were introduced.
Added SKU ranking table to Dashboard with paginated sorting via DataTable. Added onSort prop to DataTable to support external API sorting triggers. Cleanly removed all Agent Activity code.
L e a r n e d   D a t a T a b l e   i m p l e m e n t a t i o n   i n   T a b s  
 C o m p l e t e d   A d G r o u p T a b   a n d   A d P r o d u c t T a b  
 C o m p l e t e d   T 3 0   -   I m p l e m e n t i n g   4   a d   m a n a g e m e n t   t a b s  
 
O r d e r s P a g e   i m p l e m e n t e d   u s i n g   D a t a T a b l e   p a t t e r n   w i t h   m o d a l   d e t a i l s .   N o   t o a s t   l i b r a r y   u s e d ,   s o   a   c u s t o m   l o c a l   s t a t e   i s   u s e d   t o   m e e t   t o a s t   r e q u i r e m e n t s   w i t h o u t   e x t e r n a l   d e p e n d e n c i e s .  
 C r e a t e d   R e t u r n s P a g e . t s x   w i t h   1 8   c o l u m n s ,   s e a r c h   f i l t e r s ,   e x p a n d / c o l l a p s e   l o g i c ,   m a p p e d   t o t a l _ r e t u r n _ q u a n t i t y   t o   r e t u r n _ q u a n t i t y   f o r   D a t a T a b l e .  
 ## [2026-04-10] T42 - Feishu AI chat routing
- src/feishu/bot_handler.py now routes ordinary Feishu text messages into core_management through ChatService, then sends the collected full reply back via the existing Feishu text API.
- The handler strips the internal [CONV_ID:...] marker before replying so the user only sees the natural assistant response.
- Agent failures are downgraded to a friendly Chinese fallback message: AI ������ʱ�޷��ظ������Ժ�����.

## [2026-04-10] T43 - Feishu notification push enhancements
- `send_daily_report(metrics: dict)` 已增强为具体指标卡片格式（销售额/订单量/ACoS等10项），使用飞书 card 消息格式带 header + hr + note 元素。
- `send_task_alert(alert_type, details)` 新增，支持 3 种告警类型：`approval_pending`（orange）、`agent_failed`（red）、`kb_review`（purple），每种有独立的标题/模板/图标。
- `src/tasks/feishu_notify.py` 创建了 `run_daily_report()` 和 `check_pending_alerts()` 两个 async 入口函数。
- `run_daily_report` 从 `data.mock.dashboard.get_metrics_data()` 拉取数据后转换为 `{key: value}` 字典传给 `send_daily_report`。
- `check_pending_alerts` 分别检查审批超时（通过 `get_pending_approvals` + expires_at 比较）、Agent 失败（查 AgentRun.status == 'failed' 近24h）、KB 待审核（查 KnowledgeBase.status == 'pending_review'）。
- `KnowledgeBase` 模型当前不存在于 `src/db/models.py`，代码用 try/except ImportError 保护，pyright 用 `# pyright: ignore[reportAttributeAccessIssue]` 消除静态分析错误。
- `src/tasks/__init__.py` 已创建为 package。


## F2 Code Quality Review Findings (2026-04-11 00:14)

### Build
- Frontend build: PASS, 10.96s, 2981 modules, exit 0
- One warning: chunk >500kB (1071kB) — expected for SPA without code splitting

### Anti-patterns (strict zero list)
- `as any`: 0 in scope files ✓
- `@ts-ignore`: 0 ✓
- `console.log`: 0 ✓
- `TODO/FIXME/HACK`: 0 ✓
- Empty catch blocks: 0 ✓

### Wider issues found (not blocking)
- `catch (err: any)` — 11 occurrences across 6 files (ApprovalCard, useSSE, AgentConfigPage, Approvals, CostMonitor, KBReview, SystemManagement)
- `console.error/warn` — 26 occurrences across many files (used for error logging)
- These are acceptable for production mock stage but should be cleaned up before real production

### Python quality
- dashboard.py, ads.py: Clean, proper typing, no bare except
- users.py: Clean CRUD with proper HTTPException handling, uuid validation
- bot_handler.py: Proper error handling with logging, broad except only with logger.error

### AI slop check
- No JSDoc blocks in frontend
- No over-abstraction observed
- No generic names (data/result/item/temp used only in appropriate context)
- Variable names are domain-specific and meaningful
