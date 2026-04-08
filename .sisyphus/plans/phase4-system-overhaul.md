# Phase 4: Amazon AI System — Major Overhaul

## TL;DR

> **Quick Summary**: Redesign the entire Amazon automation platform from a Feishu-centric batch system to a web-centric real-time chat system with SSE streaming, per-agent multi-turn conversations, human-in-the-loop approval workflows, RBAC, 2 new agents, ad optimization engine with simulation, complete React+Vite frontend, knowledge base expansion, and multi-model AI support.
> 
> **Deliverables**:
> - New React 19 + Vite + Tailwind 4 frontend with per-agent chat UI, dashboards, and admin panels
> - SSE streaming backend with multi-turn conversation support (LangGraph checkpointer)
> - RBAC middleware enforcing Boss vs Operator permissions
> - 2 new agents: Keyword Library Builder, Auditor (Boss-only)
> - Ad optimization core algorithm + simulation engine + dashboard
> - Knowledge base: quality audit + 1,118 doc import + AI self-iteration with Boss review UI
> - SP-API Brand Analytics automation + Google Trends API (optional/pluggable)
> - API cost monitoring dashboard
> - Feishu stripped to notification-only
> 
> **Estimated Effort**: XL (6 waves, ~40 tasks)
> **Parallel Execution**: YES — 6 waves with max 8 concurrent tasks
> **Critical Path**: Wave 1a (DB+RBAC) → Wave 1b (SSE+ChatBase) → Wave 1c (Chat service) → Wave 2 (Frontend foundation) → Wave 3 (First agents+KB) → Wave 4 (Remaining agents) → Wave 5 (Ad engine) → Wave 6 (Import+Polish) → Final Verification

---

## Context

### Original Request
User rethought the entire system after Phase 3b completion, incorporating feedback from operations team. The `构思补充.md` document describes a complete shift from Feishu-centric batch processing to web-centric real-time interaction with per-agent chat interfaces, human-in-the-loop approvals, and significant new capabilities (ad optimization, keyword library, auditing).

### Interview Summary
**Key Discussions**:
- **SSE vs WebSocket**: SSE chosen — simpler, unidirectional (server→client), perfect for AI streaming
- **Multi-turn vs Single-turn**: Multi-turn chosen — chat history preserved, context continuity, iterative work
- **React Router vs Tabs**: React Router chosen — URL navigation, bookmarkable, browser history
- **Ad Algorithm Scope**: Core + Simulation first — build algorithm + test in simulation, then real deployment
- **Auditor Mode**: Hybrid — auto-block severe violations, warn on minor issues
- **Keyword Data Sources**: Full automation — Seller Sprite MCP + SP-API (Brand Analytics + Search Term Report), human reviews only
- **DB Migration**: Incremental — new tables/columns only, preserve existing schema
- **Competitor Monitoring**: Enhance existing agent — add monthly auto-monitoring capability
- **Google Trends**: YES, use official Google API (not scraper), but design as optional/pluggable (Alpha API)
- **Knowledge Base**: Quality audit existing 550 docs + import 1,118 friend docs (clean personal content/QR codes)
- **AI KB Self-Iteration**: Requires Boss approval via web review interface before writing to KB
- **Frontend Model**: Gemini 2.5 Pro for frontend development work
- **Multi-model AI**: Different models for different agents based on strengths

**Research Findings**:
- Current `BaseAgent` is 24 lines, abstract, no streaming — must create NEW `ChatBaseAgent` alongside
- LLM client has `chat()` only, no streaming — must add `chat_stream()` parallel method
- JWT middleware validates tokens but NEVER checks roles — RBAC enforcement missing
- SP-API reports.py missing `GET_BRAND_ANALYTICS_SEARCH_TERMS` report type
- Nginx needs `proxy_buffering off` for SSE routes
- 33 existing test files with `--mock-external-apis` option
- Gemini reference code has 16 components, glass-morphism style, React 19 + Vite + Tailwind 4

### Metis Review
**Identified Gaps** (all addressed in plan):
- RBAC doesn't exist on endpoints → Wave 1a applies existing `require_role()` to all agent endpoints
- LLM client has no streaming → Wave 1b adds `chat_stream()`
- Google Trends API is Alpha-only → Designed as optional/pluggable, not hard dependency
- SP-API Brand Analytics not in REPORT_TYPES → Wave 4 adds it
- Phase 1 was mega-bottleneck → Split into 1a/1b/1c sub-waves
- BaseAgent v2 must be ADDITIVE → New `ChatBaseAgent` class, don't modify existing
- Nginx needs SSE config → Wave 1b includes nginx.conf update
- 1,118 .docx on Windows, server on Ubuntu → Process locally, transfer cleaned text
- 33 test files exist → Leverage existing pytest infrastructure

---

## Work Objectives

### Core Objective
Transform the Amazon AI automation platform from a Feishu-centric batch system into a web-centric real-time chat platform with SSE streaming, RBAC, human-in-the-loop workflows, ad optimization engine, and knowledge base expansion — while preserving all existing working functionality.

### Concrete Deliverables
- New frontend at `src/frontend/` (React 19 + Vite + Tailwind 4 + React Router)
- SSE streaming endpoints at `/api/chat/{agent_type}/stream`
- `ChatBaseAgent` class in `src/agents/chat_base_agent.py`
- `chat_stream()` method in `src/llm/client.py`
- RBAC enforcement applying existing `require_role()` to all endpoints
- LangGraph PostgreSQL checkpointer for conversation persistence
- Keyword Library Builder agent in `src/agents/keyword_library/`
- Auditor agent in `src/agents/auditor/`
- Ad optimization engine in `src/agents/ad_monitor_agent/` (core algorithm + simulation)
- Ad dashboard and management pages in frontend
- KB review/approval web interface
- KB quality audit pipeline + 1,118 doc import script
- Google Trends API integration (optional module)
- SP-API Brand Analytics report automation
- Feishu stripped to notification webhooks only
- Alembic migration scripts for all schema changes
- API cost monitoring with per-agent breakdown

### Definition of Done
- [ ] `docker compose build` succeeds with zero errors
- [ ] `alembic upgrade head` applies all migrations cleanly
- [ ] `pytest --mock-external-apis` passes all existing + new tests
- [ ] All 13 agent chat interfaces accessible via SSE streaming
- [ ] Boss can access Auditor; Operator cannot (RBAC verified)
- [ ] Human-in-the-loop: agent output → review → approve/reject → DB write flow works
- [ ] Ad simulation runs without touching real Amazon Ads API
- [ ] KB review queue shows AI-generated content for Boss approval
- [ ] Frontend serves on production with Nginx reverse proxy

### Must Have
- SSE streaming for all agent chat interfaces
- Multi-turn conversation with history persistence
- RBAC: Boss sees everything, Operator sees permitted agents only
- Auditor agent: Boss-only visibility and access
- Brand Planning agent: Boss-only full access, Operator download-only
- Human confirmation before any agent writes to DB
- All actions logged for audit trail
- Ad optimization simulation mode (no live API calls)
- Knowledge base review/approval interface
- Incremental DB migration (no breaking existing tables)

### Must NOT Have (Guardrails)
- ❌ DO NOT modify existing `base_agent.py` — create `ChatBaseAgent` as NEW file
- ❌ DO NOT modify existing `workflow.invoke()` calls — add new `astream()` paths alongside
- ❌ DO NOT call Amazon Ads API write endpoints from simulation mode
- ❌ DO NOT build KB self-iteration pipeline without review UI being complete first
- ❌ DO NOT treat Google Trends as required dependency — must be optional/pluggable
- ❌ DO NOT auto-execute SP-API write operations (must go through approval)
- ❌ DO NOT add `as any` / `@ts-ignore` in TypeScript frontend code
- ❌ DO NOT skip Alembic for schema changes (no raw SQL migrations)
- ❌ DO NOT remove existing Feishu bot functionality — strip to notifications, don't delete
- ❌ DO NOT store secrets in code — use existing `Settings()` config pattern
- ❌ DO NOT add content to listings that deviates from planning documents (字符级一致)
- ❌ DO NOT let agents write directly to DB without human confirmation step

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.
> Acceptance criteria requiring "user manually tests/confirms" are FORBIDDEN.

### Test Decision
- **Infrastructure exists**: YES (33 test files, pytest with `--mock-external-apis`)
- **Automated tests**: YES (Tests-after) — add tests for new components after implementation
- **Framework**: pytest (backend), vitest (frontend — to be set up)
- **Coverage**: New agents, RBAC middleware, SSE endpoints, chat service, ad simulation

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Frontend/UI**: Use Playwright — Navigate, interact, assert DOM, screenshot
- **TUI/CLI**: Use interactive_bash (tmux) — Run command, validate output
- **API/Backend**: Use Bash (curl) — Send requests, assert status + response fields
- **Library/Module**: Use Bash (python REPL) — Import, call functions, compare output

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1a (Foundation — DB + RBAC, start immediately):
├── Task 1: Alembic setup + schema migrations (new tables)
├── Task 2: RBAC enforcement (apply existing require_role to endpoints)
└── Task 3: Chat/conversation DB models + Alembic migration

Wave 1b (Streaming Infrastructure — after 1a):
├── Task 4: LLM client chat_stream() method
├── Task 5: ChatBaseAgent class (new file, extends BaseAgent pattern)
├── Task 6: SSE endpoint framework + Nginx config
└── Task 7: LangGraph PostgreSQL checkpointer setup

Wave 1c (Chat Service Layer — after 1b):
├── Task 8: Chat service (conversation CRUD, message persistence)
├── Task 9: Chat REST + SSE API routes
└── Task 10: HITL approval workflow service

Wave 2 (Frontend Foundation — after 1a for auth, parallel with 1b/1c for UI shell):
├── Task 11: Vite + React 19 + Tailwind 4 project scaffolding
├── Task 12: Auth (login page + JWT + protected routes + RBAC context)
├── Task 13: Layout (Sidebar + TopBar + React Router)
├── Task 14: SSE client hook + Chat component (reusable)
├── Task 15: Agent catalog page (MoreFunctions equivalent)
└── Task 16: Data Dashboard page (sales metrics)

Wave 3 (First Agents Chat Mode + KB — after 1c + Wave 2):
├── Task 17: Core Management agent → chat mode
├── Task 18: Brand Planning agent → chat mode (Boss-only, PDF output)
├── Task 19: Selection agent → chat mode
├── Task 20: KB review/approval web interface
├── Task 21: KB quality audit pipeline (existing 550 docs)
├── Task 22: HITL approval UI component (approve/reject/comment)
└── Task 23: Feishu notification-only refactor

Wave 4 (Remaining Agents + New Agents — after Wave 3 core):
├── Task 24: Product Whitepaper agent → chat mode
├── Task 25: Competitor agent → chat mode + monthly auto
├── Task 26: User Persona agent → chat mode
├── Task 27: Keyword Library Builder agent (NEW)
├── Task 28: Listing Planning agent → chat mode
├── Task 29: Listing Images agent → chat mode
├── Task 30: Product Listing Upload agent → chat mode
├── Task 31: Inventory & Shipping agent → chat mode
├── Task 32: Auditor agent (NEW, Boss-only)
├── Task 33: SP-API Brand Analytics integration
└── Task 34: Multi-model agent configuration

Wave 5 (Ad Optimization Engine — after Wave 4 for Keyword Library):
├── Task 35: Ad optimization core algorithm
├── Task 36: Ad simulation engine
├── Task 37: Ad dashboard + management frontend pages
└── Task 38: Ad optimization agent → chat mode

Wave 6 (Import + Polish + Integration — after Wave 5):
├── Task 39: 1,118 doc import pipeline (clean + embed + store)
├── Task 40: AI KB self-iteration pipeline (with Boss review)
├── Task 41: Google Trends API integration (optional module)
├── Task 42: API cost monitoring dashboard
├── Task 43: Message Center + System Management pages
└── Task 44: Docker build + Nginx + deployment config update

Wave FINAL (After ALL tasks — 4 parallel reviews + user okay):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)
-> Present results -> Get explicit user okay
```

**Critical Path**: T1 → T2 → T5 → T8 → T9 → T14 → T17 → T27 → T35 → T44 → F1-F4 → user okay
**Parallel Speedup**: ~65% faster than sequential
**Max Concurrent**: 6 (Waves 3 & 4)

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| T1 | — | T2, T3, T8, T11 |
| T2 | T1 | T9, T12, T32 |
| T3 | T1 | T7, T8 |
| T4 | — | T5, T6 |
| T5 | T4 | T8, T17-T19, T24-T32 |
| T6 | T4 | T9, T14 |
| T7 | T3 | T8 |
| T8 | T3, T5, T7 | T9, T10 |
| T9 | T2, T6, T8 | T14, T17-T19 |
| T10 | T8 | T20, T22 |
| T11 | — | T12, T13, T14, T15, T16 |
| T12 | T2, T11 | T13, T15, T17 |
| T13 | T11, T12 | T15, T16, T17 |
| T14 | T6, T11, T13 | T17-T19, T24-T32 |
| T15 | T13 | — |
| T16 | T13 | T37 |
| T17 | T5, T9, T14 | T18, T19 |
| T18 | T17 | — |
| T19 | T17 | — |
| T20 | T10, T13 | T40 |
| T21 | T1 | T39 |
| T22 | T10, T14 | T20 |
| T23 | — | — |
| T24-T26 | T17 | — |
| T27 | T17, T33 | T35 |
| T28-T31 | T17 | — |
| T32 | T2, T17 | — |
| T33 | T1 | T27 |
| T34 | T5 | — |
| T35 | T27, T33 | T36 |
| T36 | T35 | T37, T38 |
| T37 | T16, T36 | — |
| T38 | T36, T14 | — |
| T39 | T21 | T40 |
| T40 | T20, T39 | — |
| T41 | T1 | — |
| T42 | T13 | — |
| T43 | T13 | — |
| T44 | all T1-T43 | F1-F4 |

### Agent Dispatch Summary

| Wave | Tasks | Categories |
|------|-------|-----------|
| 1a | 3 | T1→`quick`, T2→`deep`, T3→`quick` |
| 1b | 4 | T4→`deep`, T5→`deep`, T6→`unspecified-high`, T7→`quick` |
| 1c | 3 | T8→`deep`, T9→`unspecified-high`, T10→`deep` |
| 2 | 6 | T11→`quick`, T12→`visual-engineering`, T13→`visual-engineering`, T14→`visual-engineering`, T15→`visual-engineering`, T16→`visual-engineering` |
| 3 | 7 | T17→`deep`, T18→`deep`, T19→`deep`, T20→`visual-engineering`, T21→`unspecified-high`, T22→`visual-engineering`, T23→`quick` |
| 4 | 11 | T24-T26→`unspecified-high`, T27→`deep`, T28-T31→`unspecified-high`, T32→`deep`, T33→`unspecified-high`, T34→`quick` |
| 5 | 4 | T35→`ultrabrain`, T36→`ultrabrain`, T37→`visual-engineering`, T38→`deep` |
| 6 | 6 | T39→`unspecified-high`, T40→`deep`, T41→`unspecified-high`, T42→`visual-engineering`, T43→`visual-engineering`, T44→`unspecified-high` |
| FINAL | 4 | F1→`oracle`, F2→`unspecified-high`, F3→`unspecified-high`, F4→`deep` |

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info + QA Scenarios.

### Wave 1a — Foundation: DB Schema + RBAC (Start Immediately)

- [ ] 1. Alembic Setup + Schema Migrations (New Tables)

  **What to do**:
  - **IMPORTANT**: Alembic is ALREADY initialized — `alembic/`, `alembic.ini`, `alembic/env.py` all exist with 3 existing migrations in `alembic/versions/` (`001_add_llm_cache_table.py`, `001_add_metadata_columns.py`, `002_add_decisions_table.py`). Do NOT run `alembic init`.
  - **CRITICAL — Multi-head reconciliation**: All 3 existing migrations have `down_revision = None` (they are independent heads, not a chain). Before creating any new migration:
    1. Run `alembic heads` to confirm multiple heads
    2. Create a merge migration: `alembic merge heads -m "merge_existing_heads"` — this creates a single merge point that depends on all 3 existing migrations
    3. Verify: `alembic heads` should now show exactly 1 head
    4. Test: `alembic upgrade head` should apply cleanly (all 3 existing + merge)
  - After merge, verify `alembic/env.py` uses `settings.DATABASE_URL` and imports models — update if needed to also import new models
  - Create a NEW migration revision (extending the merged head) for new tables:
    - `conversations` (id, user_id, agent_type, title, created_at, updated_at, metadata_json)
    - `chat_messages` (id, conversation_id FK, role enum[user/assistant/system/tool], content text, metadata_json, created_at)
    - `keyword_libraries` (id, product_id FK, keyword text, search_volume int, relevance_tier enum[high/weak/related/unrelated], source enum[seller_sprite/brand_analytics/search_term_report/manual], category text, monthly_rank int, last_updated, created_at)
    - `ad_simulations` (id, campaign_id text, simulation_params json, results json, created_by, created_at)
    - `ad_optimization_logs` (id, campaign_id text, action_type text, old_value json, new_value json, reason text, applied boolean, approved_by, created_at)
    - `kb_review_queue` (id, content text, source text, agent_type text, summary text, status enum[pending/approved/rejected], reviewer_id, review_comment text, created_at, reviewed_at)
    - `auditor_logs` (id, agent_type text, agent_run_id FK, severity enum[critical/warning/info], finding text, auto_action enum[blocked/warned/passed], created_at)
  - Add new columns to existing tables:
    - `agent_runs`: add `conversation_id` FK (nullable), `is_chat_mode` boolean default false
    - `products`: add `brand_analytics_keywords` json (nullable)
  - Test: `alembic upgrade head` then `alembic downgrade -1` then `alembic upgrade head` (reversibility)

  **Must NOT do**:
  - Do NOT modify existing column types or constraints
  - Do NOT drop any existing tables or columns
  - Do NOT use raw SQL — Alembic only

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Schema definitions are straightforward, Alembic setup is well-documented
  - **Skills**: []
    - No specialized skills needed — standard Python/SQLAlchemy work

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T4, T11, T23)
  - **Parallel Group**: Wave 1a
  - **Blocks**: T2, T3, T8, T21, T33, T41
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `src/db/models.py:1-373` — All 12 existing table definitions (Base, Document, Chunk, Product, Selection, AgentRun, Task, ApprovalRequest, DailyReport, SystemConfig, AuditLog, LLMCache, Decision) — follow SQLAlchemy declarative style
  - `alembic/versions/` — 3 existing migrations (`001_add_llm_cache_table.py`, `001_add_metadata_columns.py`, `002_add_decisions_table.py`) — follow same migration code style and naming convention
  - `alembic/env.py` — Existing Alembic config — verify it imports all models and uses correct DB URL
  - `src/config.py:Settings.DATABASE_URL` — Database connection string (uppercase attribute, accessed as `settings.DATABASE_URL`)
  - `src/db/__init__.py` — Database session factory and engine setup

  **API/Type References**:
  - `src/api/schemas/agents.py:AgentType` — Enum of all agent types (for agent_type columns)

  **External References**:
  - Alembic docs: https://alembic.sqlalchemy.org/en/latest/tutorial.html

  **WHY Each Reference Matters**:
  - `models.py` — Must follow exact same Base class, naming convention, and column style for consistency
  - `config.py` — Must use same database URL source, not hardcode connection strings
  - `AgentType` enum — Must reference same enum for agent_type fields to maintain type safety

  **Acceptance Criteria**:
  - [ ] `alembic heads` shows exactly 1 head after merge migration
  - [ ] Merge migration file created in `alembic/versions/` that depends on all 3 existing migrations
  - [ ] `alembic/env.py` updated to import all new models
  - [ ] New tables migration revision file created (depending on the merge head)
  - [ ] New tables migration created with all 7 tables + 2 column additions
  - [ ] `alembic upgrade head` succeeds on existing DB (with existing data intact)
  - [ ] `alembic downgrade -1; alembic upgrade head` succeeds (reversibility of new tables migration)
  - [ ] All new models importable: `from src.db.models import Conversation, ChatMessage, KeywordLibrary, AdSimulation, AdOptimizationLog, KBReviewQueue, AuditorLog`
  - [ ] Existing 3 migrations remain untouched in `alembic/versions/`

  **QA Scenarios**:

  ```
  Scenario: Alembic heads merged and migration applies cleanly
    Tool: Bash (docker exec)
    Preconditions: Container running, DB accessible
    Steps:
      1. sudo docker exec amazon-ai-app alembic heads → verify exactly 1 head (after merge migration)
      2. sudo docker exec amazon-ai-app alembic upgrade head
      3. sudo docker exec amazon-ai-app python3 -c "from src.db.models import Conversation, ChatMessage, KeywordLibrary, AdSimulation, KBReviewQueue, AuditorLog; print('ALL IMPORTS OK')"
      4. sudo docker exec amazon-ai-app python3 -c "from src.db import SessionLocal; s=SessionLocal(); print(s.execute('SELECT count(*) FROM information_schema.tables WHERE table_schema=\\'public\\'').scalar())"
    Expected Result: Step 1 shows 1 head only. Step 2 succeeds. Step 3 prints "ALL IMPORTS OK". Step 4 shows table count = 12 (existing) + 7 (new) = 19
    Failure Indicators: Multiple heads in step 1, alembic error in step 2, ImportError in step 3, table count != 19
    Evidence: .sisyphus/evidence/task-1-alembic-upgrade.txt

  Scenario: Migration is reversible
    Tool: Bash (docker exec)
    Preconditions: Alembic head applied
    Steps:
      1. sudo docker exec amazon-ai-app alembic downgrade -1
      2. sudo docker exec amazon-ai-app alembic upgrade head
    Expected Result: Both commands succeed with no errors
    Failure Indicators: Any SQL error or alembic error during downgrade/upgrade
    Evidence: .sisyphus/evidence/task-1-alembic-reversible.txt
  ```

  **Commit**: YES (group with T2, T3 as Wave 1a)
  - Message: `feat(db): add Alembic migrations + 7 new tables + RBAC schema`
  - Files: `alembic/`, `src/db/models.py`
  - Pre-commit: `alembic upgrade head`

- [ ] 2. RBAC Enforcement — Apply Existing `require_role()` to All Endpoints

  **What to do**:
  - **IMPORTANT**: `require_role()` ALREADY EXISTS in `src/api/dependencies.py` (lines 29-58). JWT tokens ALREADY include `role` field (see `src/api/auth.py` lines 86-93). Auth uses env-backed `USERS` dict (NOT a DB table) in `src/api/auth.py` (lines 35-77). There is NO `User` model or `users` table in the DB.
  - Do NOT create `src/api/rbac.py` — use existing `require_role` from `src/api/dependencies.py`
  - Do NOT modify JWT token creation — role is already included
  - **The ACTUAL work** is applying `require_role()` as a dependency to all agent endpoints:
    - Import `require_role` from `src.api.dependencies` in `src/api/agents.py` and all agent routers
    - Auditor endpoints: `Depends(require_role("boss"))`
    - Brand Planning full access: `Depends(require_role("boss"))`
    - System Management / admin: `Depends(require_role("boss"))`
    - All other agent endpoints: `Depends(require_role("boss", "operator"))`
  - Verify that the existing `require_role()` implementation handles edge cases:
    - Missing role in JWT token → should return 403
    - Invalid role value → should return 403
    - If any edge case is not handled, fix in `src/api/dependencies.py`
  - Write pytest tests: test boss access, operator access, operator blocked from boss-only endpoints

  **Must NOT do**:
  - Do NOT create a new `src/api/rbac.py` file — use existing `src/api/dependencies.py`
  - Do NOT create a `users` DB table — keep using env-backed USERS dict
  - Do NOT change existing JWT token structure — role is already there
  - Do NOT create a complex permission system — just boss/operator for now

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Security-critical code requiring careful implementation of auth middleware
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (can start immediately — does NOT depend on T1)
  - **Parallel Group**: Wave 1a (with T1, T4, T11, T23)
  - **Blocks**: T9, T12, T32
  - **Blocked By**: None — `require_role()` already exists, just needs to be applied

  **References**:

  **Pattern References**:
  - `src/api/dependencies.py:29-58` — `require_role()` ALREADY EXISTS here — read it, understand its signature, use it as `Depends(require_role("boss"))` etc.
  - `src/api/auth.py:35-77` — Env-backed `USERS` dict — DO NOT create DB users table. Lines 86-93 show JWT already includes `role`.
  - `src/api/agents.py` — Agent endpoint definitions — this is where `require_role` must be APPLIED as `Depends()`
  - `src/api/middleware.py:1-50` — Current JWT middleware (validates token, extracts user) — may need to verify role extraction works

  **API/Type References**:
  - `src/api/schemas/agents.py` — Agent endpoint definitions that need RBAC applied

  **Test References**:
  - `tests/` — Follow existing pytest patterns for writing RBAC tests

  **WHY Each Reference Matters**:
  - `dependencies.py` — CRITICAL: This contains the existing `require_role()` implementation. Do NOT recreate it.
  - `auth.py` — Shows that role is already in JWT and users are env-backed. No DB changes needed.
  - `agents.py` — The actual file that needs editing to add `Depends(require_role(...))` to each endpoint
  - `middleware.py` — May need minor update to ensure role is extracted from JWT and available to dependencies

  **Acceptance Criteria**:
  - [ ] `require_role()` from `src/api/dependencies.py` is applied to ALL agent endpoints
  - [ ] Boss can access all endpoints (200)
  - [ ] Operator gets 403 on boss-only endpoints (auditor, brand_planning write, admin)
  - [ ] Operator can access standard agent endpoints (200)
  - [ ] pytest tests for RBAC pass
  - [ ] NO new `src/api/rbac.py` file created (use existing dependencies.py)

  **QA Scenarios**:

  ```
  Scenario: Boss accesses boss-only endpoint
    Tool: Bash (curl)
    Preconditions: Server running, boss user exists
    Steps:
      1. curl -s -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"username":"boss","password":"test123"}' → extract token
      2. curl -s -w "%{http_code}" -H "Authorization: Bearer $BOSS_TOKEN" -H "Content-Type: application/json" -X POST http://localhost:8000/api/agents/auditor/run -d '{"params":{}}'
    Expected Result: Step 1 returns JWT with role="boss". Step 2 returns 200 (or agent-specific response, NOT 403)
    Failure Indicators: 403 on step 2 (boss should have access)
    Evidence: .sisyphus/evidence/task-2-boss-access.txt

  Scenario: Operator blocked from boss-only endpoint
    Tool: Bash (curl)
    Preconditions: Server running, operator user exists
    Steps:
      1. curl -s -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"username":"op1","password":"test123"}' → extract token
      2. curl -s -w "%{http_code}" -H "Authorization: Bearer $OP_TOKEN" -H "Content-Type: application/json" -X POST http://localhost:8000/api/agents/auditor/run -d '{"params":{}}'
    Expected Result: Step 2 returns HTTP 403 with {"detail": "Insufficient permissions"}
    Failure Indicators: 200 on step 2 (RBAC not enforced)
    Evidence: .sisyphus/evidence/task-2-operator-blocked.txt

  Scenario: Unauthenticated request rejected
    Tool: Bash (curl)
    Preconditions: Server running
    Steps:
      1. curl -s -w "%{http_code}" -X POST http://localhost:8000/api/agents/selection/run -H "Content-Type: application/json" -d '{"params":{}}'
    Expected Result: HTTP 401
    Failure Indicators: 200 (no auth required)
    Evidence: .sisyphus/evidence/task-2-unauth-rejected.txt
  ```

  **Commit**: YES (group with T1, T3 as Wave 1a)
  - Message: `feat(db): add Alembic migrations + 7 new tables + RBAC schema`
  - Files: `src/api/agents.py`, `src/api/dependencies.py` (if edge case fixes), `tests/test_rbac.py`
  - Pre-commit: `pytest tests/test_rbac.py`

- [ ] 3. Chat/Conversation DB Models + Alembic Migration

  **What to do**:
  - This task ensures T1's conversation/message models are properly integrated with LangGraph checkpointer requirements
  - Add `langgraph-checkpoint-postgres` to requirements/dependencies
  - Verify `conversations` and `chat_messages` table schemas are compatible with LangGraph's `PostgresSaver` expected format
  - If LangGraph checkpointer has its own tables (e.g., `checkpoints`, `checkpoint_writes`), add them to migration
  - Create utility functions in `src/db/chat.py`:
    - `create_conversation(user_id, agent_type, title) → Conversation`
    - `add_message(conversation_id, role, content, metadata) → ChatMessage`
    - `get_conversation_history(conversation_id, limit=50) → list[ChatMessage]`
    - `list_user_conversations(user_id, agent_type=None) → list[Conversation]`
  - Write pytest tests for CRUD operations

  **Must NOT do**:
  - Do NOT create custom checkpointer — use `langgraph-checkpoint-postgres` official package
  - Do NOT duplicate LangGraph's internal tables — let the library manage its own schema

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: CRUD utilities with well-defined interfaces, straightforward SQLAlchemy
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T1, can start after T1's model definitions)
  - **Parallel Group**: Wave 1a (after T1)
  - **Blocks**: T7, T8
  - **Blocked By**: T1 (needs conversation/message tables)

  **References**:

  **Pattern References**:
  - `src/db/models.py:Conversation, ChatMessage` — The models defined in T1
  - `src/db/__init__.py` — SessionLocal factory and engine pattern

  **External References**:
  - langgraph-checkpoint-postgres: https://langchain-ai.github.io/langgraph/reference/checkpoints/#langgraph.checkpoint.postgres
  - LangGraph PostgresSaver setup docs

  **WHY Each Reference Matters**:
  - `models.py` — Must use exact same model classes for CRUD operations
  - LangGraph checkpointer docs — Must verify our schema doesn't conflict with LangGraph's internal tables

  **Acceptance Criteria**:
  - [ ] `langgraph-checkpoint-postgres` in project dependencies
  - [ ] `src/db/chat.py` exists with 4 CRUD functions
  - [ ] LangGraph checkpointer tables created (if any) via migration
  - [ ] pytest tests for all 4 CRUD functions pass
  - [ ] `create_conversation` → `add_message` → `get_conversation_history` flow works end-to-end

  **QA Scenarios**:

  ```
  Scenario: Full conversation CRUD flow
    Tool: Bash (docker exec python3)
    Preconditions: DB migrated, models available
    Steps:
      1. sudo docker exec amazon-ai-app python3 -c "
         from src.db.chat import create_conversation, add_message, get_conversation_history, list_user_conversations
         from src.db import SessionLocal
         db = SessionLocal()
         conv = create_conversation(db, user_id=1, agent_type='core_management', title='Test')
         msg1 = add_message(db, conv.id, role='user', content='Hello')
         msg2 = add_message(db, conv.id, role='assistant', content='Hi there')
         history = get_conversation_history(db, conv.id)
         convs = list_user_conversations(db, user_id=1)
         print(f'Conv: {conv.id}, Messages: {len(history)}, User convs: {len(convs)}')
         db.close()
         "
    Expected Result: Prints "Conv: <id>, Messages: 2, User convs: 1"
    Failure Indicators: Any ImportError, IntegrityError, or wrong counts
    Evidence: .sisyphus/evidence/task-3-chat-crud.txt

  Scenario: LangGraph checkpointer compatible
    Tool: Bash (docker exec python3)
    Preconditions: DB migrated, langgraph-checkpoint-postgres installed
    Steps:
      1. sudo docker exec amazon-ai-app python3 -c "
         from langgraph.checkpoint.postgres import PostgresSaver
         from src.config import Settings
         s = Settings()
         print(f'PostgresSaver importable, DB: {s.DATABASE_URL[:20]}...')
         "
    Expected Result: Import succeeds, DB URL printed
    Failure Indicators: ImportError or ModuleNotFoundError
    Evidence: .sisyphus/evidence/task-3-checkpointer-import.txt
  ```

  **Commit**: YES (group with T1, T2 as Wave 1a)
  - Message: `feat(db): add Alembic migrations + 7 new tables + RBAC schema`
  - Files: `src/db/chat.py`, `requirements.txt` (or pyproject.toml)
  - Pre-commit: `pytest tests/test_chat_db.py`

### Wave 1b — Streaming Infrastructure (After Wave 1a)

- [ ] 4. LLM Client chat_stream() Method

  **What to do**:
  - Add `async def chat_stream()` method to existing LLM client in `src/llm/client.py`
  - Method signature: `chat_stream(messages, model=None, temperature=None, max_tokens=None) → AsyncGenerator[str, None]`
  - Support both OpenAI and Anthropic streaming APIs:
    - OpenAI: `client.chat.completions.create(stream=True)` → yield `chunk.choices[0].delta.content`
    - Anthropic: `client.messages.stream()` → yield text deltas
  - Integrate with existing cost tracking (`_track_usage`) — accumulate streaming token counts
  - Integrate with existing rate limiting and cost limit ($50/day)
  - Handle errors gracefully: yield error message if API fails, don't crash stream
  - DO NOT modify existing `chat()` method — `chat_stream()` is parallel, additive
  - Write pytest test with mocked streaming responses

  **Must NOT do**:
  - Do NOT modify existing `chat()` method signature or behavior
  - Do NOT remove any existing methods from the client
  - Do NOT skip cost tracking for streaming calls

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Must handle async generators, multi-provider streaming, error recovery, cost tracking integration
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (independent of T1-T3)
  - **Parallel Group**: Wave 1b (can start with T1)
  - **Blocks**: T5, T6
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `src/llm/client.py:1-200` — Full LLM client: `chat()` method, model routing, cost tracking (`_track_usage`), rate limiting, provider detection — must follow same patterns for `chat_stream()`
  - `src/llm/client.py:_track_usage` — Token usage tracking method — must integrate streaming token counts here

  **External References**:
  - OpenAI streaming: https://platform.openai.com/docs/api-reference/streaming
  - Anthropic streaming: https://docs.anthropic.com/en/api/streaming

  **WHY Each Reference Matters**:
  - `client.py` — The entire file is the reference. `chat_stream()` must mirror `chat()` in provider detection, model routing, error handling, and cost tracking — just with streaming output

  **Acceptance Criteria**:
  - [ ] `chat_stream()` method exists in LLM client
  - [ ] Yields string chunks for both OpenAI and Anthropic providers
  - [ ] Cost tracking works for streaming (token counts accumulated)
  - [ ] Rate limiting respected during streaming
  - [ ] Error handling: yields error message instead of crashing
  - [ ] pytest test with mocked streaming passes

  **QA Scenarios**:

  ```
  Scenario: Streaming response from OpenAI model
    Tool: Bash (docker exec python3)
    Preconditions: Container running, OpenAI API key configured
    Steps:
      1. sudo docker exec amazon-ai-app python3 -c "
         import asyncio
         from src.llm.client import chat_stream
         async def test():
           chunks = []
           async for chunk in chat_stream([{'role':'user','content':'Say hello in 3 words'}], model='gpt-4o-mini'):
             chunks.append(chunk)
           full = ''.join(chunks)
           print(f'Chunks: {len(chunks)}, Full: {full[:100]}')
         asyncio.run(test())
         "
    Expected Result: Multiple chunks received, concatenated to form coherent response
    Failure Indicators: 0 chunks, ImportError (chat_stream not found), error message, crash
    Evidence: .sisyphus/evidence/task-4-streaming-openai.txt

  Scenario: Cost tracking works for streaming
    Tool: Bash (docker exec python3)
    Preconditions: Container running
    Steps:
      1. sudo docker exec amazon-ai-app python3 -c "
         import asyncio
         from src.llm.client import chat_stream
         from src.llm.cost_monitor import check_daily_limit
         async def test():
           async for chunk in chat_stream([{'role':'user','content':'Hi'}], model='gpt-4o-mini'):
             pass
           # Verify cost was tracked by checking cost monitor (not raising limit exceeded)
           cost_ok = check_daily_limit()
           print(f'Cost check passed: {cost_ok is None or cost_ok}')
         asyncio.run(test())
         "
    Expected Result: "Cost check passed: True" — streaming call was tracked in cost system
    Failure Indicators: ImportError, cost monitor errors
    Evidence: .sisyphus/evidence/task-4-streaming-cost.txt
  ```

  **Commit**: YES (group with T5, T6, T7 as Wave 1b)
  - Message: `feat(streaming): add ChatBaseAgent + SSE endpoints + LLM streaming`
  - Files: `src/llm/client.py`
  - Pre-commit: `pytest tests/test_llm_streaming.py`

- [ ] 5. ChatBaseAgent Class (New File)

  **What to do**:
  - Create `src/agents/chat_base_agent.py` with `ChatBaseAgent` class
  - `ChatBaseAgent` extends the pattern of `BaseAgent` but adds:
    - `async def chat(self, message: str, conversation_id: str, user_id: int) → AsyncGenerator[str, None]` — main entry point
    - Conversation history loading from DB (via `src/db/chat.py`)
    - System prompt construction with agent-specific context + conversation history
    - LLM streaming via `client.chat_stream()`
    - Message persistence (save user message + assistant response to DB)
    - Tool/function calling support within chat context
    - LangGraph `StateGraph` integration with `astream()` for streaming workflow execution
  - Keep existing `BaseAgent.run()` working — `ChatBaseAgent` adds `chat()` alongside
  - Each agent subclass will override: `system_prompt`, `available_tools`, `model_preference`
  - Create abstract methods that subclasses must implement:
    - `get_system_prompt() → str`
    - `get_tools() → list[Tool]` (optional)
    - `get_model() → str` (returns preferred model name)
  - Write pytest test with mocked LLM

  **Must NOT do**:
  - Do NOT modify `src/agents/base_agent.py` — this is a NEW file
  - Do NOT break existing `workflow.invoke()` patterns — add `astream()` alongside
  - Do NOT make ChatBaseAgent inherit from BaseAgent (parallel class, not subclass)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Core architectural class, async generators, LangGraph integration, must be extensible for all 13 agents
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T4 for chat_stream)
  - **Parallel Group**: Wave 1b (after T4)
  - **Blocks**: T8, T17-T19, T24-T32, T34
  - **Blocked By**: T4 (needs chat_stream)

  **References**:

  **Pattern References**:
  - `src/agents/base_agent.py:1-24` — Existing abstract base (abstract `run()`, `agent_type` property) — DO NOT MODIFY, create parallel class
  - `src/agents/core_agent/agent.py:1-100` — Example agent implementation (StateGraph, nodes, `run()` override) — follow this pattern for `chat()` method
  - `src/agents/brand_planning_agent/agent.py` — Another agent example showing tool usage and multi-step workflows
  - `src/llm/client.py:chat_stream` — The streaming method from T4 that ChatBaseAgent wraps

  **API/Type References**:
  - `src/db/chat.py` — CRUD functions from T3 for conversation persistence

  **External References**:
  - LangGraph StateGraph streaming: https://langchain-ai.github.io/langgraph/how-tos/streaming-tokens/

  **WHY Each Reference Matters**:
  - `base_agent.py` — Shows the interface pattern to mirror (but NOT modify or inherit from)
  - `core_agent/agent.py` — Shows how agents use StateGraph nodes, how to add streaming `astream()` alongside existing `invoke()`
  - `chat.py` — The persistence layer ChatBaseAgent uses for conversation history

  **Acceptance Criteria**:
  - [ ] `src/agents/chat_base_agent.py` exists
  - [ ] `ChatBaseAgent` has `chat()` async generator method
  - [ ] Abstract methods: `get_system_prompt()`, `get_tools()`, `get_model()`
  - [ ] Loads conversation history from DB before each turn
  - [ ] Persists messages after each turn
  - [ ] Streams via `chat_stream()` from LLM client
  - [ ] `src/agents/base_agent.py` UNCHANGED (git diff shows no changes)
  - [ ] pytest test passes

  **QA Scenarios**:

  ```
  Scenario: ChatBaseAgent is importable and base_agent unchanged
    Tool: Bash (docker exec)
    Preconditions: Code deployed
    Steps:
      1. sudo docker exec amazon-ai-app python3 -c "from src.agents.chat_base_agent import ChatBaseAgent; print('ChatBaseAgent imported')"
      2. sudo docker exec amazon-ai-app python3 -c "from src.agents.base_agent import BaseAgent; print('BaseAgent still works')"
      3. sudo docker exec amazon-ai-app python3 -c "import hashlib; h=hashlib.md5(open('src/agents/base_agent.py','rb').read()).hexdigest(); print(f'base_agent.py hash: {h}')"
    Expected Result: Both imports succeed. base_agent.py hash matches pre-change value (record hash before any changes)
    Failure Indicators: ImportError, hash mismatch (base_agent was modified)
    Evidence: .sisyphus/evidence/task-5-chatbase-import.txt

  Scenario: ChatBaseAgent abstract methods enforced
    Tool: Bash (docker exec python3)
    Preconditions: Code deployed
    Steps:
      1. sudo docker exec amazon-ai-app python3 -c "
         from src.agents.chat_base_agent import ChatBaseAgent
         try:
           agent = ChatBaseAgent()
           print('ERROR: Should not instantiate abstract class')
         except TypeError as e:
           print(f'Correctly abstract: {e}')
         "
    Expected Result: TypeError showing abstract methods must be implemented
    Failure Indicators: Successfully instantiates (not abstract)
    Evidence: .sisyphus/evidence/task-5-chatbase-abstract.txt
  ```

  **Commit**: YES (group with T4, T6, T7 as Wave 1b)
  - Message: `feat(streaming): add ChatBaseAgent + SSE endpoints + LLM streaming`
  - Files: `src/agents/chat_base_agent.py`
  - Pre-commit: `pytest tests/test_chat_base_agent.py`

- [ ] 6. SSE Endpoint Framework + Nginx Config

  **What to do**:
  - Create `src/api/sse.py` with SSE response utilities:
    - `sse_response(generator: AsyncGenerator) → StreamingResponse` — wraps async generator into SSE format
    - SSE format: `data: {json}\n\n` with event types: `message`, `thinking`, `tool_call`, `error`, `done`
    - Heartbeat: send `data: {"type":"heartbeat"}\n\n` every 15 seconds to keep connection alive
    - Error handling: catch exceptions in generator, yield error event, close stream
  - Create SSE chat endpoint pattern in `src/api/chat.py`:
    - `POST /api/chat/{agent_type}/stream` — accepts `{"message": "...", "conversation_id": "..."}`, returns SSE stream
    - Requires JWT auth (uses existing middleware)
    - Validates agent_type against `AgentType` enum
  - Update Nginx config (`deploy/nginx/nginx.conf`):
    - Add `proxy_buffering off;` for `/api/chat/` location
    - Add `X-Accel-Buffering: no` header
    - Add `proxy_read_timeout 300s;` for long-running streams
    - Add `proxy_set_header Connection '';` for SSE
  - Write pytest test for SSE response formatting

  **Must NOT do**:
  - Do NOT use WebSocket — SSE only (user decision)
  - Do NOT modify existing REST endpoints in `src/api/agents.py` — add new SSE routes alongside
  - Do NOT disable Nginx buffering globally — only for `/api/chat/` routes

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: SSE infrastructure + Nginx config requires understanding of HTTP streaming, reverse proxy, and FastAPI async
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T5, T7)
  - **Parallel Group**: Wave 1b
  - **Blocks**: T9, T14
  - **Blocked By**: T4 (needs streaming concept established)

  **References**:

  **Pattern References**:
  - `src/api/agents.py:1-100` — Existing REST agent endpoints pattern (router, auth dependency, agent_type validation) — SSE endpoints follow same auth pattern
  - `src/api/main.py` — Router registration pattern — must register new chat router here
  - `deploy/nginx/nginx.conf` — Current Nginx config — add SSE-specific location block

  **API/Type References**:
  - `src/api/schemas/agents.py:AgentType` — Agent type enum for endpoint validation
  - `src/api/middleware.py` — JWT auth dependency to reuse

  **External References**:
  - FastAPI StreamingResponse: https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse
  - SSE spec: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events
  - Nginx SSE config: https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_buffering

  **WHY Each Reference Matters**:
  - `agents.py` — Must follow same auth pattern and router structure for consistency
  - `nginx.conf` — Critical for production: without `proxy_buffering off`, Nginx buffers SSE and client gets no streaming
  - SSE spec — Must follow exact `data: ...\n\n` format for browser EventSource compatibility

  **Acceptance Criteria**:
  - [ ] `src/api/sse.py` exists with SSE utilities
  - [ ] `src/api/chat.py` exists with `/api/chat/{agent_type}/stream` endpoint
  - [ ] Nginx config updated with SSE-specific settings
  - [ ] SSE stream format correct (`data: {...}\n\n`)
  - [ ] Heartbeat mechanism works (15s interval)
  - [ ] JWT auth required for SSE endpoints
  - [ ] pytest test for SSE formatting passes

  **QA Scenarios**:

  ```
  Scenario: SSE endpoint returns streaming response
    Tool: Bash (curl with -N flag)
    Preconditions: Server running with SSE endpoints registered
    Steps:
      1. Get boss token: curl -s -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"username":"boss","password":"test123"}'
      2. curl -N -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -X POST http://localhost:8000/api/chat/core_management/stream -d '{"message":"hello","conversation_id":null}' --max-time 30
    Expected Result: Receives SSE events in format "data: {...}\n\n" with type fields (message, done)
    Failure Indicators: Non-SSE response, 404, 401, buffered (all at once instead of streaming)
    Evidence: .sisyphus/evidence/task-6-sse-stream.txt

  Scenario: SSE requires authentication
    Tool: Bash (curl)
    Preconditions: Server running
    Steps:
      1. curl -s -w "%{http_code}" -X POST http://localhost:8000/api/chat/core_management/stream -d '{"message":"hello"}'
    Expected Result: HTTP 401 or 403
    Failure Indicators: 200 (no auth check)
    Evidence: .sisyphus/evidence/task-6-sse-auth.txt
  ```

  **Commit**: YES (group with T4, T5, T7 as Wave 1b)
  - Message: `feat(streaming): add ChatBaseAgent + SSE endpoints + LLM streaming`
  - Files: `src/api/sse.py`, `src/api/chat.py`, `deploy/nginx/nginx.conf`
  - Pre-commit: `pytest tests/test_sse.py`

- [ ] 7. LangGraph PostgreSQL Checkpointer Setup

  **What to do**:
  - Configure `langgraph-checkpoint-postgres` to use existing PostgreSQL database
  - Create `src/agents/checkpointer.py` with:
    - `get_checkpointer() → PostgresSaver` — singleton/factory that returns configured checkpointer
    - Uses `settings.DATABASE_URL` for connection (import `from src.config import settings`)
    - Handles connection pooling (share with existing SQLAlchemy pool or create separate)
  - Initialize checkpointer tables: call `checkpointer.setup()` on startup (add to `src/api/main.py` startup event)
  - Verify checkpointer works with a simple LangGraph workflow test
  - This enables conversation state persistence across server restarts

  **Must NOT do**:
  - Do NOT create custom checkpointer implementation — use official `PostgresSaver`
  - Do NOT create a separate database for checkpointing — use existing DB

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Configuration task, well-documented library setup
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T5, T6)
  - **Parallel Group**: Wave 1b
  - **Blocks**: T8
  - **Blocked By**: T3 (needs langgraph-checkpoint-postgres dependency)

  **References**:

  **Pattern References**:
  - `src/config.py:Settings.DATABASE_URL` — Connection string to reuse (accessed as `settings.DATABASE_URL`)
  - `src/db/__init__.py` — Existing DB initialization pattern (engine, SessionLocal)
  - `src/api/main.py:startup` — App startup event where checkpointer.setup() should be called

  **External References**:
  - langgraph-checkpoint-postgres: https://langchain-ai.github.io/langgraph/reference/checkpoints/#langgraph.checkpoint.postgres.PostgresSaver

  **WHY Each Reference Matters**:
  - `config.py` — Must use same DB connection, not hardcode a different URL
  - `main.py startup` — Checkpointer tables must be created on app startup before any chat request

  **Acceptance Criteria**:
  - [ ] `src/agents/checkpointer.py` exists with `get_checkpointer()` factory
  - [ ] Checkpointer setup runs on app startup
  - [ ] Checkpointer tables created in DB
  - [ ] Simple workflow can save and restore state via checkpointer

  **QA Scenarios**:

  ```
  Scenario: Checkpointer initializes on startup
    Tool: Bash (docker exec)
    Preconditions: Container running with updated code
    Steps:
      1. sudo docker exec amazon-ai-app python3 -c "
         from src.agents.checkpointer import get_checkpointer
         cp = get_checkpointer()
         print(f'Checkpointer type: {type(cp).__name__}')
         "
    Expected Result: Prints "Checkpointer type: PostgresSaver"
    Failure Indicators: ImportError or connection error
    Evidence: .sisyphus/evidence/task-7-checkpointer-init.txt
  ```

  **Commit**: YES (group with T4, T5, T6 as Wave 1b)
  - Message: `feat(streaming): add ChatBaseAgent + SSE endpoints + LLM streaming`
  - Files: `src/agents/checkpointer.py`, `src/api/main.py`
  - Pre-commit: `pytest`

### Wave 1c — Chat Service Layer (After Wave 1b)

- [ ] 8. Chat Service (Conversation CRUD, Message Persistence, Agent Dispatch)

  **What to do**:
  - Create `src/services/chat.py` with `ChatService` class:
    - `create_conversation(user_id, agent_type) → Conversation` — creates new conversation
    - `send_message(conversation_id, user_id, message) → AsyncGenerator[str, None]` — sends user message, dispatches to correct agent, streams response
    - `get_history(conversation_id, user_id) → list[ChatMessage]` — returns conversation history
    - `list_conversations(user_id, agent_type=None) → list[Conversation]` — lists user's conversations
    - `delete_conversation(conversation_id, user_id) → bool` — soft delete
  - Agent dispatch: `send_message` determines agent_type from conversation → instantiates correct `ChatBaseAgent` subclass → calls `agent.chat()` → streams response
  - Agent registry: dict mapping `AgentType` → `ChatBaseAgent` subclass (lazy import)
  - Persist both user message and full assistant response to DB
  - Integrate with LangGraph checkpointer (from T7) for state persistence
  - Handle concurrent conversations per user (different agent types)

  **Must NOT do**:
  - Do NOT expose DB sessions directly — service layer handles all DB interactions
  - Do NOT block on agent execution — must be fully async/streaming

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Orchestration layer connecting DB, agents, streaming, checkpointer — core business logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T3, T5, T7)
  - **Parallel Group**: Wave 1c
  - **Blocks**: T9, T10
  - **Blocked By**: T3 (chat DB), T5 (ChatBaseAgent), T7 (checkpointer)

  **References**:

  **Pattern References**:
  - `src/db/chat.py` — CRUD functions from T3 (ChatService wraps these with business logic)
  - `src/agents/chat_base_agent.py` — ChatBaseAgent from T5 (service dispatches to agents)
  - `src/agents/checkpointer.py` — Checkpointer from T7 (service integrates for state persistence)
  - `src/api/agents.py` — Current agent dispatch pattern (agent_type → agent class mapping)

  **WHY Each Reference Matters**:
  - `chat.py` — Direct dependency for persistence
  - `chat_base_agent.py` — Service calls `agent.chat()` and streams result
  - `agents.py` — Shows existing agent dispatch pattern to mirror for chat mode

  **Acceptance Criteria**:
  - [ ] `src/services/chat.py` exists with `ChatService` class
  - [ ] `send_message` correctly dispatches to agent and streams response
  - [ ] Messages persisted to DB after each exchange
  - [ ] Conversation listing and history retrieval work
  - [ ] pytest test passes

  **QA Scenarios**:

  ```
  Scenario: Full chat flow (create → send → history)
    Tool: Bash (curl)
    Preconditions: Server running, all Wave 1a/1b deployed
    Steps:
      1. Login as boss, get token
      2. curl -s -H "Authorization: Bearer $TOKEN" -X POST http://localhost:8000/api/chat/conversations -d '{"agent_type":"core_management"}' → get conversation_id
      3. curl -N -H "Authorization: Bearer $TOKEN" -X POST http://localhost:8000/api/chat/core_management/stream -d '{"message":"What are my daily tasks?","conversation_id":"$CONV_ID"}'
      4. curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/chat/conversations/$CONV_ID/history
    Expected Result: Step 2 returns conversation ID. Step 3 streams SSE response. Step 4 returns 2 messages (user + assistant)
    Failure Indicators: Empty history, no streaming, wrong message count
    Evidence: .sisyphus/evidence/task-8-chat-flow.txt
  ```

  **Commit**: YES (group with T9, T10 as Wave 1c)
  - Message: `feat(chat): add chat service + HITL approval + API routes`
  - Files: `src/services/chat.py`
  - Pre-commit: `pytest tests/test_chat_service.py`

- [ ] 9. Chat REST + SSE API Routes (Full API Surface)

  **What to do**:
  - Expand `src/api/chat.py` (from T6) with full REST API surface:
    - `POST /api/chat/conversations` — create conversation (body: `{agent_type}`)
    - `GET /api/chat/conversations` — list user's conversations (query: `?agent_type=...`)
    - `GET /api/chat/conversations/{id}` — get conversation details
    - `GET /api/chat/conversations/{id}/history` — get message history (query: `?limit=50`)
    - `DELETE /api/chat/conversations/{id}` — delete conversation
    - `POST /api/chat/{agent_type}/stream` — send message + stream response (SSE, from T6)
  - All endpoints use JWT auth + RBAC:
    - Auditor conversations: `require_role("boss")`
    - Brand Planning conversations: `require_role("boss")` for write, all for read
    - Other agents: `require_role("boss", "operator")`
  - Request/response schemas in `src/api/schemas/chat.py`:
    - `CreateConversationRequest`, `ConversationResponse`, `MessageResponse`, `ChatStreamRequest`
  - Wire to `ChatService` from T8

  **Must NOT do**:
  - Do NOT expose internal IDs — use UUIDs for conversation IDs
  - Do NOT allow cross-user conversation access
  - Do NOT modify existing `/api/agents/` endpoints

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Full REST API with auth, schemas, RBAC integration, error handling
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T10)
  - **Parallel Group**: Wave 1c
  - **Blocks**: T14, T17-T19
  - **Blocked By**: T2 (RBAC), T6 (SSE framework), T8 (ChatService)

  **References**:

  **Pattern References**:
  - `src/api/agents.py` — Existing REST endpoint patterns (router, Depends, response models)
  - `src/api/schemas/agents.py` — Schema definition patterns (Pydantic models)
  - `src/api/chat.py` — SSE endpoint from T6 (expand this file)
  - `src/api/dependencies.py` — RBAC dependency (`require_role`) from T2

  **WHY Each Reference Matters**:
  - `agents.py` — Must follow exact same FastAPI patterns for consistency
  - `rbac.py` — Must apply correct role requirements per agent type (use `require_role` from `dependencies.py`)

  **Acceptance Criteria**:
  - [ ] All 6 endpoints implemented and accessible
  - [ ] RBAC enforced (operator cannot create auditor conversations)
  - [ ] Pydantic schemas validate request/response
  - [ ] Cross-user access blocked (user A can't read user B's conversations)
  - [ ] pytest test passes

  **QA Scenarios**:

  ```
  Scenario: Operator cannot create auditor conversation
    Tool: Bash (curl)
    Preconditions: Server running, operator user exists
    Steps:
      1. Login as op1, get token
      2. curl -s -w "%{http_code}" -H "Authorization: Bearer $OP_TOKEN" -X POST http://localhost:8000/api/chat/conversations -d '{"agent_type":"auditor"}'
    Expected Result: HTTP 403
    Failure Indicators: 200 or 201 (RBAC not enforced)
    Evidence: .sisyphus/evidence/task-9-rbac-auditor.txt

  Scenario: Conversation CRUD via API
    Tool: Bash (curl)
    Preconditions: Server running
    Steps:
      1. Login as boss
      2. POST /api/chat/conversations {agent_type: "core_management"} → 201
      3. GET /api/chat/conversations → list includes new conversation
      4. GET /api/chat/conversations/{id} → conversation details
      5. DELETE /api/chat/conversations/{id} → 200
      6. GET /api/chat/conversations → list excludes deleted
    Expected Result: Full CRUD cycle works
    Failure Indicators: Any non-2xx status, deleted conversation still visible
    Evidence: .sisyphus/evidence/task-9-crud-cycle.txt
  ```

  **Commit**: YES (group with T8, T10 as Wave 1c)
  - Message: `feat(chat): add chat service + HITL approval + API routes`
  - Files: `src/api/chat.py`, `src/api/schemas/chat.py`
  - Pre-commit: `pytest`

- [ ] 10. HITL Approval Workflow Service

  **What to do**:
  - Create `src/services/approval.py` with `ApprovalService`:
    - `submit_for_review(agent_type, agent_run_id, content, summary, target_action) → ApprovalRequest` — agent submits output for human review
    - `list_pending(user_id, role) → list[ApprovalRequest]` — returns pending items for user
    - `approve(approval_id, user_id, comment=None) → bool` — approves and executes target_action
    - `reject(approval_id, user_id, comment) → bool` — rejects with comment
    - `get_approval_status(approval_id) → ApprovalRequest` — check status
  - Target actions (executed after approval):
    - `write_to_db`: Writes agent output to appropriate table
    - `write_to_kb`: Writes to knowledge base (via existing RAG engine)
    - `create_report`: Generates and stores PDF/markdown report
    - `update_listing`: Queues listing update via SP-API
    - `adjust_bid`: Queues ad bid adjustment via Ads API
  - Integrate with existing `approval_requests` table in DB (model: `ApprovalRequest` in `src/db/models.py`, table name: `approval_requests`) — extend if needed
  - Approval states: pending → approved/rejected
  - Notifications: trigger Feishu webhook on new approval request (for boss)
  - Create REST endpoints:
    - `GET /api/approvals` — list pending approvals
    - `POST /api/approvals/{id}/approve` — approve
    - `POST /api/approvals/{id}/reject` — reject with comment
  - RBAC: Boss can approve all. Operator can approve own agent outputs (except auditor/brand_planning).

  **Must NOT do**:
  - Do NOT auto-approve anything (every agent output goes through review)
  - Do NOT execute target_action before approval
  - Do NOT allow operator to approve auditor findings

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex state machine, RBAC-aware, integrates with multiple downstream systems
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T9)
  - **Parallel Group**: Wave 1c
  - **Blocks**: T20, T22
  - **Blocked By**: T8 (chat service for context)

  **References**:

  **Pattern References**:
  - `src/db/models.py:ApprovalRequest` — Existing `approval_requests` table (class `ApprovalRequest`, line 228) — extend if needed for new fields
  - `src/db/models.py:Decision` — 7-state machine pattern (may inform approval states)
  - `src/feishu/bot_handler.py` — Feishu webhook for notification trigger

  **WHY Each Reference Matters**:
  - `ApprovalRequest` model — Must extend existing `approval_requests` table, not create duplicate
  - `Decision` model — Shows state machine pattern already in codebase
  - `bot_handler.py` — Notification mechanism for approval requests

  **Acceptance Criteria**:
  - [ ] `src/services/approval.py` exists with `ApprovalService`
  - [ ] Approval REST endpoints work (list, approve, reject)
  - [ ] Approved action executes target_action
  - [ ] Rejected action records comment, no execution
  - [ ] RBAC enforced on approvals
  - [ ] pytest test passes

  **QA Scenarios**:

  ```
  Scenario: Full approval flow (submit → list → approve → action executed)
    Tool: Bash (curl)
    Preconditions: Server running, Wave 1a/1b deployed
    Steps:
      1. Login as boss
      2. Trigger an agent that produces output requiring approval (e.g., core_management via chat)
      3. GET /api/approvals → should list pending item
      4. POST /api/approvals/{id}/approve → 200
      5. GET /api/approvals/{id} → status should be "approved"
      6. Verify target action was executed (check DB for written data)
    Expected Result: Full flow works, data written to DB after approval
    Failure Indicators: No pending items, approval fails, action not executed
    Evidence: .sisyphus/evidence/task-10-approval-flow.txt

  Scenario: Rejection prevents action
    Tool: Bash (curl)
    Preconditions: Pending approval exists
    Steps:
      1. POST /api/approvals/{id}/reject -d '{"comment":"Needs revision"}'
      2. Verify target action was NOT executed
    Expected Result: Status "rejected", no DB write
    Failure Indicators: Action executed despite rejection
    Evidence: .sisyphus/evidence/task-10-rejection.txt
  ```

  **Commit**: YES (group with T8, T9 as Wave 1c)
  - Message: `feat(chat): add chat service + HITL approval + API routes`
  - Files: `src/services/approval.py`, `src/api/approvals.py`
  - Pre-commit: `pytest tests/test_approval.py`

### Wave 2 — Frontend Foundation (After Wave 1a for auth, parallel with 1b/1c for UI shell)

- [ ] 11. Vite + React 19 + Tailwind 4 Project Scaffolding

  **What to do**:
  - Create `src/frontend/` directory with Vite + React 19 + TypeScript project
  - Install dependencies: `react@19`, `react-dom@19`, `react-router-dom@7`, `tailwindcss@4`, `@tailwindcss/vite`, `motion`, `recharts`, `lucide-react`, `react-markdown`, `axios`
  - Configure Vite: dev proxy to `http://localhost:8000/api/` for API calls
  - Configure Tailwind 4 with design tokens matching Gemini reference:
    - Color palette: business blue (#1E3A5F primary), glass-morphism backgrounds
    - Dark mode support (preference-based)
    - Custom animations (fade-in, slide-up)
  - Create `src/frontend/src/types.ts` — shared TypeScript types:
    - `Agent`, `Conversation`, `ChatMessage`, `User`, `ApprovalRequest`, `AgentType` enum
  - Create `src/frontend/src/api/client.ts` — Axios instance with JWT interceptor
  - Set up `vite.config.ts` with production build output to `src/frontend/dist/`
  - Docker integration: Nginx serves `dist/` for frontend, proxies `/api/` to backend

  **Must NOT do**:
  - Do NOT use Next.js — pure Vite + React (user decision)
  - Do NOT use `@google/genai` from Gemini reference — backend handles AI
  - Do NOT copy Gemini reference code directly — use as style reference only

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Frontend scaffolding with design system setup, Tailwind config, component architecture
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T1-T3, T4)
  - **Parallel Group**: Wave 2 (can start immediately)
  - **Blocks**: T12, T13, T14, T15, T16
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `temp_frontend_ref/package.json` — Gemini reference dependencies (React 19, Vite, Tailwind 4, Motion) — use as dependency reference
  - `temp_frontend_ref/src/App.tsx` — App structure (tab-based, will change to React Router)
  - `temp_frontend_ref/index.html` — Vite entry point pattern
  - `temp_frontend_ref/vite.config.ts` — Vite config (Tailwind plugin setup)

  **API/Type References**:
  - `temp_frontend_ref/src/types.ts` — Type definitions (TabType, Message, Agent) — adapt for our needs
  - `src/api/schemas/chat.py` — Backend schema shapes to mirror in frontend types

  **External References**:
  - Vite: https://vitejs.dev/guide/
  - Tailwind CSS 4: https://tailwindcss.com/docs/installation/vite
  - React Router 7: https://reactrouter.com/start/framework/installation

  **WHY Each Reference Matters**:
  - `temp_frontend_ref/` — Style and dependency reference only. Our app uses React Router (not tabs), real API (not Gemini AI), and SSE streaming
  - Backend schemas — Frontend types must match backend response shapes exactly

  **Acceptance Criteria**:
  - [ ] `src/frontend/` exists with complete Vite + React 19 project
  - [ ] `npm run dev` starts dev server at localhost:5173
  - [ ] `npm run build` produces `dist/` directory with no TypeScript errors
  - [ ] Tailwind 4 configured with design tokens
  - [ ] API client with JWT interceptor created
  - [ ] Types file matches backend schemas

  **QA Scenarios**:

  ```
  Scenario: Frontend dev server starts
    Tool: Bash
    Preconditions: Node.js installed, dependencies installed
    Steps:
      1. cd src/frontend && npm install
      2. npm run build
      3. ls dist/index.html
    Expected Result: Build succeeds, dist/index.html exists
    Failure Indicators: TypeScript errors, build failure, missing dist
    Evidence: .sisyphus/evidence/task-11-frontend-build.txt

  Scenario: Tailwind styles applied
    Tool: Bash
    Preconditions: Build succeeded
    Steps:
      1. Check dist/assets/*.css for Tailwind utility classes
      2. Verify file size > 1KB (not empty)
    Expected Result: CSS file exists with Tailwind classes
    Failure Indicators: Empty CSS, no Tailwind classes
    Evidence: .sisyphus/evidence/task-11-tailwind-check.txt
  ```

  **Commit**: YES (group with T12-T16 as Wave 2)
  - Message: `feat(frontend): React 19 + Vite scaffolding with auth + layout + SSE chat`
  - Files: `src/frontend/`
  - Pre-commit: `npm run build`

- [ ] 12. Auth (Login Page + JWT + Protected Routes + RBAC Context)

  **What to do**:
  - Create `src/frontend/src/pages/Login.tsx`:
    - Username + password form with glass-morphism card style
    - Calls `POST /api/auth/login` → stores JWT in localStorage
    - Redirect to dashboard on success
    - Error display for wrong credentials
  - Create `src/frontend/src/contexts/AuthContext.tsx`:
    - `AuthProvider` wrapping entire app
    - `useAuth()` hook returning: `user`, `role`, `login()`, `logout()`, `isAuthenticated`
    - Decode JWT to get role (`boss` vs `operator`)
    - Auto-redirect to login on 401 responses (Axios interceptor)
  - Create `src/frontend/src/components/ProtectedRoute.tsx`:
    - Checks auth state, redirects to `/login` if not authenticated
    - Optional `requiredRole` prop — hides route if user role doesn't match
  - RBAC in UI: hide menu items operator shouldn't see (Auditor, System Management)
  - Token refresh: if token expired, redirect to login (no silent refresh for now)

  **Must NOT do**:
  - Do NOT store JWT in cookies — use localStorage (simple, sufficient for SPA)
  - Do NOT implement OAuth — username/password only (existing auth system)
  - Do NOT show hidden boss-only features to operators with disabled state — completely hide them

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Login UI + auth flow + RBAC context, frontend-heavy
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T13 after T11)
  - **Parallel Group**: Wave 2 (after T11 + T2)
  - **Blocks**: T13 (layout needs auth), T15, T17
  - **Blocked By**: T2 (RBAC backend), T11 (project scaffolding)

  **References**:

  **Pattern References**:
  - `temp_frontend_ref/src/components/Login.tsx` — Gemini reference login page (glass-morphism style reference)
  - `src/api/auth.py` — Backend auth endpoints (POST /api/auth/login, JWT format)
  - `src/frontend/src/api/client.ts` — Axios client from T11 (add auth interceptor here)

  **WHY Each Reference Matters**:
  - `Login.tsx` (Gemini) — Visual style reference only. Our auth hits real backend, not Gemini API
  - `auth.py` — Must match exact request/response format (username/password → JWT with role)

  **Acceptance Criteria**:
  - [ ] Login page renders at `/login`
  - [ ] Successful login stores JWT and redirects to `/`
  - [ ] Failed login shows error message
  - [ ] `useAuth()` hook returns correct role
  - [ ] Protected routes redirect to login when not authenticated
  - [ ] Boss-only items hidden from operator

  **QA Scenarios**:

  ```
  Scenario: Login flow end-to-end
    Tool: Playwright
    Preconditions: Backend running, frontend served via Nginx
    Steps:
      1. Navigate to https://52.221.207.30/login
      2. Fill username "boss", password "test123"
      3. Click login button
      4. Wait for redirect to /
      5. Check localStorage for JWT token
      6. Verify sidebar shows "Auditor" menu item (boss-only)
    Expected Result: Redirected to dashboard, JWT stored, boss-only items visible
    Failure Indicators: Stays on login, no JWT, missing boss items
    Evidence: .sisyphus/evidence/task-12-login-boss.png

  Scenario: Operator cannot see auditor
    Tool: Playwright
    Preconditions: Backend running
    Steps:
      1. Navigate to /login
      2. Login as op1/test123
      3. Check sidebar for "Auditor" menu item
    Expected Result: "Auditor" NOT visible in sidebar
    Failure Indicators: "Auditor" visible to operator
    Evidence: .sisyphus/evidence/task-12-login-operator.png
  ```

  **Commit**: YES (group with T11, T13-T16 as Wave 2)
  - Message: `feat(frontend): React 19 + Vite scaffolding with auth + layout + SSE chat`
  - Files: `src/frontend/src/pages/Login.tsx`, `src/frontend/src/contexts/AuthContext.tsx`, `src/frontend/src/components/ProtectedRoute.tsx`
  - Pre-commit: `npm run build`

- [ ] 13. Layout (Sidebar + TopBar + React Router)

  **What to do**:
  - Create `src/frontend/src/components/Layout.tsx`:
    - Left sidebar (collapsible) with navigation items
    - Top bar with user info, logout button, breadcrumbs
    - Main content area with React Router `<Outlet />`
  - Create `src/frontend/src/components/Sidebar.tsx`:
    - Navigation items with lucide-react icons:
      - Dashboard (LayoutDashboard icon)
      - AI Supervisor (Bot icon) — main agent hub
      - Ad Dashboard (BarChart3 icon)
      - Ad Management (Target icon)
      - Orders (ShoppingCart icon)
      - Refund Orders (RotateCcw icon)
      - Message Center (MessageSquare icon)
      - System Management (Settings icon) — boss only
    - Active route highlighting
    - RBAC-aware: hide boss-only items for operators
  - Create `src/frontend/src/components/TopBar.tsx`:
    - User avatar + name + role badge
    - Notification bell (count badge)
    - Logout button
  - Set up React Router in `src/frontend/src/App.tsx`:
    - Routes: `/login`, `/`, `/agents/:type`, `/ads`, `/ads/manage`, `/orders`, `/refunds`, `/messages`, `/system`, `/approvals`
    - Wrap with `AuthProvider` and `Layout`
  - Glass-morphism sidebar style matching Gemini reference

  **Must NOT do**:
  - Do NOT use tab-based navigation from Gemini reference — use React Router (user decision)
  - Do NOT create mobile-responsive layout (excluded from scope)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Core layout component with sidebar, routing, glass-morphism styling
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T12, after T11)
  - **Parallel Group**: Wave 2
  - **Blocks**: T15, T16, T17, T20, T22, T42, T43
  - **Blocked By**: T11 (project scaffolding), T12 (auth context for RBAC)

  **References**:

  **Pattern References**:
  - `temp_frontend_ref/src/components/Sidebar.tsx:1-143` — Gemini sidebar (navigation items, icons, glass-morphism style) — adapt from tabs to routes
  - `temp_frontend_ref/src/components/TopBar.tsx` — Top bar pattern (if exists in reference)
  - `temp_frontend_ref/src/App.tsx` — App structure (adapt tab switching to React Router)

  **WHY Each Reference Matters**:
  - Gemini sidebar — Visual style reference. Convert tab-based `onTabChange` to `<Link to="...">` with React Router
  - App.tsx — Shows component hierarchy. Replace `activeTab` state with `<Routes>`

  **Acceptance Criteria**:
  - [ ] Layout with sidebar + top bar + content area renders
  - [ ] All routes defined and navigable
  - [ ] Active route highlighted in sidebar
  - [ ] Boss-only items hidden for operators
  - [ ] Sidebar collapsible
  - [ ] URL navigation works (direct URL, back/forward)

  **QA Scenarios**:

  ```
  Scenario: Route navigation works
    Tool: Playwright
    Preconditions: Frontend deployed, logged in as boss
    Steps:
      1. Navigate to https://52.221.207.30/
      2. Click "AI Supervisor" in sidebar
      3. Verify URL changed to /agents or similar
      4. Click browser back button
      5. Verify returned to /
      6. Navigate directly to /ads
      7. Verify Ad Dashboard renders
    Expected Result: All navigation paths work, URL reflects current page
    Failure Indicators: 404, blank page, URL not updating
    Evidence: .sisyphus/evidence/task-13-routing.png

  Scenario: Sidebar RBAC
    Tool: Playwright
    Preconditions: Logged in as operator
    Steps:
      1. Count sidebar menu items
      2. Verify "System Management" not present
      3. Verify "AI Supervisor" present
    Expected Result: Operator sees reduced menu
    Failure Indicators: System Management visible to operator
    Evidence: .sisyphus/evidence/task-13-sidebar-rbac.png
  ```

  **Commit**: YES (group with T11, T12, T14-T16 as Wave 2)
  - Message: `feat(frontend): React 19 + Vite scaffolding with auth + layout + SSE chat`
  - Files: `src/frontend/src/components/Layout.tsx`, `src/frontend/src/components/Sidebar.tsx`, `src/frontend/src/components/TopBar.tsx`, `src/frontend/src/App.tsx`
  - Pre-commit: `npm run build`

- [ ] 14. SSE Client Hook + Chat Component (Reusable)

  **What to do**:
  - Create `src/frontend/src/hooks/useSSE.ts`:
    - `useSSE(url, options)` — custom hook that connects to SSE endpoint
    - Handles: connection, reconnection (3 retries), error handling, heartbeat detection
    - Returns: `{ messages, isConnected, error, send }` (send triggers POST then listens)
    - Uses `EventSource` API or `fetch` with `ReadableStream` for POST-based SSE
  - Create `src/frontend/src/hooks/useChat.ts`:
    - `useChat(agentType, conversationId)` — wraps useSSE for chat-specific logic
    - Manages: message list, typing indicator, auto-scroll, message persistence
    - Returns: `{ messages, sendMessage, isTyping, error, conversationId }`
  - Create `src/frontend/src/components/ChatWindow.tsx`:
    - Reusable chat UI component used by all agent pages
    - Props: `agentType`, `conversationId`, `agentName`, `agentIcon`
    - Features:
      - Message bubbles (user right, agent left) with markdown rendering
      - Typing indicator (animated dots while streaming)
      - Auto-scroll to bottom on new message
      - Input box with send button (Enter to send, Shift+Enter for newline)
      - Conversation history loaded on mount
      - Stream indicator showing "thinking..." during agent processing
    - Style: match Gemini reference chat UI (glass-morphism cards, blue accent)
  - Create `src/frontend/src/components/ConversationList.tsx`:
    - Sidebar list of past conversations for current agent
    - Create new conversation button
    - Click to switch conversation

  **Must NOT do**:
  - Do NOT use WebSocket client — SSE/fetch streaming only
  - Do NOT store messages in global state — component-level state per chat instance

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Complex interactive UI with SSE streaming, animations, markdown rendering
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T15, T16, after T13)
  - **Parallel Group**: Wave 2
  - **Blocks**: T17-T19, T24-T32, T38
  - **Blocked By**: T6 (SSE endpoint format), T11 (project), T13 (layout)

  **References**:

  **Pattern References**:
  - `temp_frontend_ref/src/components/AISupervisor.tsx:1-228` — Chat UI pattern (message list, input box, send handler, typing indicator) — primary visual reference
  - `temp_frontend_ref/src/components/AgentDetail.tsx:1-257` — Per-agent chat with file sidebar — secondary reference
  - `src/api/sse.py` — SSE event format from T6 (must match: `data: {"type":"message","content":"..."}`)

  **External References**:
  - EventSource API: https://developer.mozilla.org/en-US/docs/Web/API/EventSource
  - react-markdown: https://github.com/remarkjs/react-markdown

  **WHY Each Reference Matters**:
  - `AISupervisor.tsx` — Primary UI reference for chat layout, message rendering, input handling
  - `sse.py` — Must parse exact SSE event format from backend (type, content fields)

  **Acceptance Criteria**:
  - [ ] `useSSE` hook connects to SSE endpoint and receives events
  - [ ] `useChat` hook manages message state and streaming
  - [ ] `ChatWindow` renders messages with markdown, shows typing indicator
  - [ ] Auto-scroll works on new messages
  - [ ] Input sends message and streams response
  - [ ] Conversation list shows/switches past conversations
  - [ ] `npm run build` passes with no TypeScript errors

  **QA Scenarios**:

  ```
  Scenario: Chat message sends and streams response
    Tool: Playwright
    Preconditions: Full stack running (backend + frontend + Nginx)
    Steps:
      1. Navigate to /agents/core_management (or equivalent)
      2. Type "What are my tasks?" in chat input
      3. Press Enter or click Send
      4. Observe typing indicator appears
      5. Wait for response to stream in (character by character or chunk by chunk)
      6. Verify response is rendered as markdown
    Expected Result: Message sent, typing indicator shown, response streams in, markdown rendered
    Failure Indicators: No response, no typing indicator, no streaming (all at once)
    Evidence: .sisyphus/evidence/task-14-chat-stream.png

  Scenario: Conversation history loads on revisit
    Tool: Playwright
    Preconditions: Previous conversation exists
    Steps:
      1. Navigate to agent page
      2. Select existing conversation from list
      3. Verify previous messages displayed
    Expected Result: Historical messages appear with correct user/agent alignment
    Failure Indicators: Empty chat, missing messages
    Evidence: .sisyphus/evidence/task-14-chat-history.png
  ```

  **Commit**: YES (group with T11-T13, T15-T16 as Wave 2)
  - Message: `feat(frontend): React 19 + Vite scaffolding with auth + layout + SSE chat`
  - Files: `src/frontend/src/hooks/useSSE.ts`, `src/frontend/src/hooks/useChat.ts`, `src/frontend/src/components/ChatWindow.tsx`, `src/frontend/src/components/ConversationList.tsx`
  - Pre-commit: `npm run build`

- [ ] 15. Agent Catalog Page (MoreFunctions Equivalent)

  **What to do**:
  - Create `src/frontend/src/pages/AgentCatalog.tsx`:
    - Grid of agent cards showing all available agents
    - Each card: agent icon, name, description, status badge (online/offline), last activity
    - Click card → navigate to `/agents/{type}` (per-agent chat page)
    - RBAC-aware: hide Auditor card from operators
    - Search/filter by agent name or category
    - Categories: Analysis, Content, Operations, Monitoring
  - This is the "AI Supervisor" or "More Functions" page equivalent
  - Style: glass-morphism cards with hover animations (motion library)

  **Must NOT do**:
  - Do NOT show disabled cards for boss-only agents — hide completely from operators

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Visual grid layout with animations, card components, RBAC filtering
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T14, T16)
  - **Parallel Group**: Wave 2
  - **Blocks**: None
  - **Blocked By**: T13 (layout + routing)

  **References**:

  **Pattern References**:
  - `temp_frontend_ref/src/components/MoreFunctions.tsx:1-135` — Agent catalog cards (grid layout, agent descriptions, click handler)
  - `temp_frontend_ref/src/components/AISupervisor.tsx` — Agent list section

  **WHY Each Reference Matters**:
  - `MoreFunctions.tsx` — Direct visual reference for card grid layout and agent metadata display

  **Acceptance Criteria**:
  - [ ] Page renders at `/agents` with grid of agent cards
  - [ ] Click card navigates to `/agents/{type}`
  - [ ] RBAC: operator cannot see Auditor
  - [ ] Search/filter works
  - [ ] Cards have hover animation

  **QA Scenarios**:

  ```
  Scenario: Agent cards render with RBAC
    Tool: Playwright
    Preconditions: Logged in as operator
    Steps:
      1. Navigate to /agents (or AI Supervisor page)
      2. Count visible agent cards
      3. Search for "Auditor"
      4. Verify no results
    Expected Result: Cards render for all operator-visible agents (no Auditor)
    Failure Indicators: Auditor card visible, zero cards
    Evidence: .sisyphus/evidence/task-15-agent-catalog.png
  ```

  **Commit**: YES (group with T11-T14, T16 as Wave 2)
  - Message: `feat(frontend): React 19 + Vite scaffolding with auth + layout + SSE chat`
  - Files: `src/frontend/src/pages/AgentCatalog.tsx`
  - Pre-commit: `npm run build`

- [ ] 16. Data Dashboard Page (Sales Metrics)

  **What to do**:
  - Create `src/frontend/src/pages/Dashboard.tsx`:
    - Top KPI cards: Total Sales, Total Orders, Ad Spend, ACOS, Conversion Rate
    - Sales trend chart (Recharts line chart, 30-day)
    - Top products table (sortable by sales, revenue, units)
    - Recent agent activity feed (latest 10 agent runs with status)
    - Date range picker for filtering
  - Fetch data from existing backend endpoints:
    - `GET /api/dashboard/summary` (or adapt existing)
    - `GET /api/agents/runs` (recent agent runs)
  - If dashboard API doesn't exist, create minimal backend endpoint that aggregates from existing data
  - Style: match Gemini reference DataDashboard (card grid, Recharts charts)

  **Must NOT do**:
  - Do NOT create fake/demo data — use real DB data or show empty state
  - Do NOT spend excessive time on dashboard API — focus on frontend, API can be minimal

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Data visualization, Recharts integration, responsive card layout
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T14, T15)
  - **Parallel Group**: Wave 2
  - **Blocks**: T37 (Ad Dashboard builds on this pattern)
  - **Blocked By**: T13 (layout + routing)

  **References**:

  **Pattern References**:
  - `temp_frontend_ref/src/components/DataDashboard.tsx:1-331` — Sales dashboard (KPI cards, line chart, product table) — primary visual reference
  - `src/api/agents.py` — Existing agent run endpoints (adapt for recent activity feed)

  **WHY Each Reference Matters**:
  - `DataDashboard.tsx` — Direct visual reference for layout, Recharts config, table structure

  **Acceptance Criteria**:
  - [ ] Dashboard renders at `/`
  - [ ] KPI cards show real or empty-state data
  - [ ] Sales chart renders (even if empty data)
  - [ ] Agent activity feed shows recent runs
  - [ ] Date picker filters data
  - [ ] `npm run build` passes

  **QA Scenarios**:

  ```
  Scenario: Dashboard renders with data
    Tool: Playwright
    Preconditions: Logged in, some agent runs exist in DB
    Steps:
      1. Navigate to /
      2. Verify KPI cards visible (at least 5 cards)
      3. Verify chart area visible
      4. Verify recent activity list has items
    Expected Result: All dashboard sections render without errors
    Failure Indicators: Blank page, JS errors in console, missing sections
    Evidence: .sisyphus/evidence/task-16-dashboard.png
  ```

  **Commit**: YES (group with T11-T15 as Wave 2)
  - Message: `feat(frontend): React 19 + Vite scaffolding with auth + layout + SSE chat`
  - Files: `src/frontend/src/pages/Dashboard.tsx`
  - Pre-commit: `npm run build`

### Wave 3 — First Agents Chat Mode + KB Review + HITL UI (After Wave 1c + Wave 2)

- [ ] 17. Core Management Agent → Chat Mode

  **What to do**:
  - Create `src/agents/core_agent/chat_agent.py` extending `ChatBaseAgent`:
    - `get_system_prompt()` — Core management context (daily reports, task management, KPI overview)
    - `get_model()` — GPT-4o (strong reasoning for management decisions)
    - `get_tools()` — tools for: query daily reports, list tasks, check agent statuses, query knowledge base
  - The chat version should be able to:
    - Answer questions about daily business status
    - Generate daily report (5 sections: sales, ads, inventory, competitor moves, action items)
    - List and manage tasks
    - Query knowledge base for business context
  - Keep existing `agent.py` `run()` method working for backward compatibility (cron jobs still use it)
  - Register chat agent in `ChatService` agent registry
  - Create `src/frontend/src/pages/AgentChat.tsx` — generic per-agent chat page:
    - Uses `ChatWindow` component from T14
    - Route: `/agents/:type`
    - Loads agent metadata (name, description, icon) from agent catalog data
    - Shows conversation list sidebar + active chat
    - This single page component serves ALL agents (agent-specific behavior comes from backend)

  **Must NOT do**:
  - Do NOT duplicate agent logic — chat_agent should reuse existing workflow nodes where possible
  - Do NOT break existing cron-triggered `run()` method

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: First agent migration sets the pattern for all others, must be robust reference implementation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (first agent, sets pattern for T18-T19)
  - **Parallel Group**: Wave 3 (first in wave, others follow pattern)
  - **Blocks**: T18, T19, T24-T32
  - **Blocked By**: T5 (ChatBaseAgent), T9 (API routes), T14 (ChatWindow)

  **References**:

  **Pattern References**:
  - `src/agents/core_agent/agent.py` — Existing agent (StateGraph, run(), nodes) — keep working, add chat_agent.py alongside
  - `src/agents/chat_base_agent.py` — Base class from T5 to extend
  - `src/services/chat.py` — ChatService from T8 for agent registry
  - `temp_frontend_ref/src/components/AgentDetail.tsx` — Per-agent chat UI reference

  **WHY Each Reference Matters**:
  - `agent.py` — Must NOT modify. New `chat_agent.py` lives alongside and may import shared utilities
  - `chat_base_agent.py` — Extend this for chat mode
  - `AgentDetail.tsx` — Visual reference for per-agent chat page layout

  **Acceptance Criteria**:
  - [ ] `src/agents/core_agent/chat_agent.py` exists extending `ChatBaseAgent`
  - [ ] Can chat with core management agent via SSE
  - [ ] Agent responds with relevant business context
  - [ ] Existing `run()` method still works (backward compatible)
  - [ ] `AgentChat.tsx` page renders at `/agents/core_management`
  - [ ] Conversation history persists across page reloads

  **QA Scenarios**:

  ```
  Scenario: Chat with Core Management agent
    Tool: Playwright
    Preconditions: Full stack deployed
    Steps:
      1. Login as boss, navigate to /agents/core_management
      2. Type "Give me a summary of today's status"
      3. Wait for SSE response to complete
      4. Verify response contains structured content (not error)
      5. Send follow-up: "What about inventory levels?"
      6. Verify response references previous context
    Expected Result: Agent responds with relevant info, multi-turn context works
    Failure Indicators: Error response, no streaming, context lost between messages
    Evidence: .sisyphus/evidence/task-17-core-chat.png

  Scenario: Existing REST endpoint still works
    Tool: Bash (curl)
    Preconditions: Backend deployed
    Steps:
      1. curl -X POST http://localhost:8000/api/agents/core_management/run -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"params":{}}'
    Expected Result: 200 with task_id (existing fire-and-forget behavior preserved)
    Failure Indicators: 404 or error (endpoint removed)
    Evidence: .sisyphus/evidence/task-17-backward-compat.txt
  ```

  **Commit**: YES (group with T18-T23 as Wave 3)
  - Message: `feat(agents): first 3 agents chat mode + KB review + HITL UI + Feishu refactor`
  - Files: `src/agents/core_agent/chat_agent.py`, `src/frontend/src/pages/AgentChat.tsx`
  - Pre-commit: `pytest; npm run build`

- [ ] 18. Brand Planning Agent → Chat Mode (Boss-Only, PDF Output)

  **What to do**:
  - Create `src/agents/brand_planning_agent/chat_agent.py` extending `ChatBaseAgent`:
    - `get_system_prompt()` — Brand planning context with PUDIWIND V2 report format reference
    - `get_model()` — Claude-3.5-sonnet (strong analytical writing)
    - `get_tools()` — tools for: query Seller Sprite MCP (ASIN detail, keyword research), query knowledge base, generate PDF report
  - Chat flow:
    - User provides brand/product context via chat
    - Agent asks clarifying questions (interactive, multi-turn)
    - Agent generates brand analysis report following PUDIWIND V2 structure (3 parts: 势能分析, 品牌定位, 最小单元模型)
    - Report submitted to HITL approval (via ApprovalService from T10)
    - After approval: stored as markdown + PDF in DB/filesystem
  - RBAC: Boss-only full access, operator can only download completed reports
  - Self-iteration: agent can propose updates to existing brand reports → goes through Boss approval
  - PDF generation: use `python-docx` or `weasyprint` for report output

  **Must NOT do**:
  - Do NOT allow operators to create or edit brand reports
  - Do NOT auto-save reports without HITL approval
  - Do NOT deviate from PUDIWIND V2 report structure (3-part format)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex multi-turn workflow, PDF generation, HITL integration, RBAC constraints
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T19, T20-T23, after T17)
  - **Parallel Group**: Wave 3
  - **Blocks**: None
  - **Blocked By**: T17 (pattern established), T10 (HITL service)

  **References**:

  **Pattern References**:
  - `src/agents/brand_planning_agent/agent.py` — Existing brand planning agent (workflow, tools, knowledge base query)
  - `src/agents/core_agent/chat_agent.py` — Chat pattern from T17 (follow this for chat_agent.py)
  - PUDIWIND V2 structure in draft: Part 1 势能分析 (6 sections), Part 2 品牌定位 (5 sections), Part 3 最小单元模型 (7 sections)

  **External References**:
  - python-docx for report generation: https://python-docx.readthedocs.io/
  - PUDIWIND_V2_complete_report.docx — Format reference (18 sections, 40 tables)

  **WHY Each Reference Matters**:
  - `agent.py` — Existing tools and knowledge base queries to reuse in chat mode
  - PUDIWIND V2 — Exact report structure to follow (agent output format specification)

  **Acceptance Criteria**:
  - [ ] Chat agent works for brand planning with multi-turn interaction
  - [ ] Report follows PUDIWIND V2 3-part structure
  - [ ] HITL: report goes to approval queue before storage
  - [ ] Boss can access fully, operator can only download completed reports
  - [ ] PDF output generated after approval

  **QA Scenarios**:

  ```
  Scenario: Brand planning chat with HITL
    Tool: Playwright + Bash
    Preconditions: Full stack, logged in as boss
    Steps:
      1. Navigate to /agents/brand_planning
      2. Chat: "Analyze the pet leash market for PUDIWIND brand"
      3. Respond to agent's clarifying questions
      4. Wait for report generation (may take multiple turns)
      5. Check /approvals for pending brand report
      6. Approve the report
      7. Verify report stored and downloadable
    Expected Result: Full flow works, report in PUDIWIND structure
    Failure Indicators: No approval created, report structure wrong, operator can create reports
    Evidence: .sisyphus/evidence/task-18-brand-planning-chat.png

  Scenario: Operator blocked from brand planning write
    Tool: Playwright
    Preconditions: Logged in as operator
    Steps:
      1. Navigate to /agents/brand_planning
      2. Attempt to send a message
    Expected Result: Either chat disabled or 403 error, only download option available
    Failure Indicators: Operator can chat with brand planning agent
    Evidence: .sisyphus/evidence/task-18-brand-rbac.png
  ```

  **Commit**: YES (group with T17, T19-T23 as Wave 3)
  - Message: `feat(agents): first 3 agents chat mode + KB review + HITL UI + Feishu refactor`
  - Files: `src/agents/brand_planning_agent/chat_agent.py`
  - Pre-commit: `pytest`

- [ ] 19. Selection Agent → Chat Mode

  **What to do**:
  - Create `src/agents/selection_agent/chat_agent.py` extending `ChatBaseAgent`:
    - `get_system_prompt()` — Product selection methodology, market analysis focus
    - `get_model()` — GPT-4o (strong analytical reasoning)
    - `get_tools()` — tools for: Seller Sprite MCP (get_category_data, get_asin_data), SP-API catalog search, knowledge base query
  - Chat flow:
    - Operator provides category/niche of interest
    - Agent collects data from Seller Sprite + SP-API
    - Agent produces structured selection analysis (market size, competition, profit potential)
    - Output submitted to HITL approval before DB storage
  - Keep existing `run()` for weekly cron compatibility

  **Must NOT do**:
  - Do NOT auto-store selection results — must go through HITL

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Multi-source data collection, structured analysis, HITL integration
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T18, T20-T23)
  - **Parallel Group**: Wave 3
  - **Blocks**: None
  - **Blocked By**: T17 (pattern established)

  **References**:

  **Pattern References**:
  - `src/agents/selection_agent/agent.py` — Existing selection agent
  - `src/agents/core_agent/chat_agent.py` — Chat pattern from T17

  **Acceptance Criteria**:
  - [ ] Chat agent works for selection analysis
  - [ ] Seller Sprite + SP-API tools integrated
  - [ ] HITL approval before storage
  - [ ] Existing weekly cron `run()` preserved

  **QA Scenarios**:

  ```
  Scenario: Selection chat produces analysis
    Tool: Playwright
    Preconditions: Full stack, logged in
    Steps:
      1. Navigate to /agents/selection
      2. Chat: "Analyze the pet water fountain category on Amazon US"
      3. Wait for response with market data
    Expected Result: Agent returns structured analysis with market data
    Failure Indicators: No data, error, Seller Sprite not called
    Evidence: .sisyphus/evidence/task-19-selection-chat.png
  ```

  **Commit**: YES (group with T17-T18, T20-T23 as Wave 3)
  - Message: `feat(agents): first 3 agents chat mode + KB review + HITL UI + Feishu refactor`
  - Files: `src/agents/selection_agent/chat_agent.py`
  - Pre-commit: `pytest`

- [ ] 20. KB Review/Approval Web Interface

  **What to do**:
  - Create `src/frontend/src/pages/KBReview.tsx`:
    - Route: `/kb-review` (boss-only)
    - List of pending KB entries from `kb_review_queue` table
    - Each item shows: source agent, summary, full content (expandable), timestamp
    - Actions: Approve (writes to knowledge base), Reject (with comment), Edit before approve
    - Bulk approve/reject for efficiency
    - Filters: by agent source, date range, status
  - Create backend endpoints in `src/api/kb_review.py`:
    - `GET /api/kb-review` — list pending items (boss-only)
    - `POST /api/kb-review/{id}/approve` — approve and write to KB
    - `POST /api/kb-review/{id}/reject` — reject with comment
    - `PUT /api/kb-review/{id}` — edit content before approval
  - Integration with existing `knowledge_base/` RAG engine for the actual write operation
  - RBAC: Boss-only access

  **Must NOT do**:
  - Do NOT allow operators to access KB review
  - Do NOT auto-approve any KB entries
  - Do NOT bypass RAG engine for KB writes (use existing embedding + storage pipeline)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Review interface with list/detail views, inline editing, bulk actions
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T17-T19, T21-T23)
  - **Parallel Group**: Wave 3
  - **Blocks**: T40 (KB self-iteration needs review UI)
  - **Blocked By**: T10 (HITL service), T13 (layout)

  **References**:

  **Pattern References**:
  - `src/knowledge_base/` — Existing RAG engine (embedding generation, document storage, retrieval)
  - `src/db/models.py:KBReviewQueue` — Review queue model from T1
  - `src/services/approval.py` — HITL service pattern from T10

  **WHY Each Reference Matters**:
  - RAG engine — The actual write target. Approved content goes through existing embedding pipeline
  - `KBReviewQueue` — DB model for the review list
  - approval.py — Pattern for approve/reject workflows

  **Acceptance Criteria**:
  - [ ] KB review page renders at `/kb-review` for boss
  - [ ] Pending items listed with content preview
  - [ ] Approve → content written to KB via RAG engine
  - [ ] Reject → comment recorded, content NOT written
  - [ ] Edit before approve works
  - [ ] Operator gets 403 on KB review endpoints

  **QA Scenarios**:

  ```
  Scenario: KB review approve flow
    Tool: Playwright
    Preconditions: KB review queue has pending items, logged in as boss
    Steps:
      1. Navigate to /kb-review
      2. Verify pending items listed
      3. Click on first item to expand
      4. Click "Approve"
      5. Verify item moves to "Approved" status
      6. Query knowledge base to verify content was written
    Expected Result: Approved content appears in KB
    Failure Indicators: Content not in KB after approve, approve button doesn't work
    Evidence: .sisyphus/evidence/task-20-kb-review.png

  Scenario: Operator blocked from KB review
    Tool: Bash (curl)
    Preconditions: Operator token available
    Steps:
      1. curl -s -w "%{http_code}" -H "Authorization: Bearer $OP_TOKEN" http://localhost:8000/api/kb-review
    Expected Result: HTTP 403
    Failure Indicators: 200 (no RBAC)
    Evidence: .sisyphus/evidence/task-20-kb-rbac.txt
  ```

  **Commit**: YES (group with T17-T19, T21-T23 as Wave 3)
  - Message: `feat(agents): first 3 agents chat mode + KB review + HITL UI + Feishu refactor`
  - Files: `src/frontend/src/pages/KBReview.tsx`, `src/api/kb_review.py`
  - Pre-commit: `npm run build; pytest`

- [ ] 21. KB Quality Audit Pipeline (Existing 550 Docs)

  **What to do**:
  - Create `src/knowledge_base/audit.py` with `KBAuditor` class:
    - `audit_all() → AuditReport` — scans all 550 existing documents
    - Quality checks per document:
      - Content length (too short < 100 chars → flag)
      - Language detection (should be relevant Chinese/English)
      - Relevance scoring via LLM (is this e-commerce/Amazon relevant?)
      - Duplicate detection (cosine similarity > 0.95 → flag as duplicate)
      - Embedding quality (vector exists, correct dimensions)
    - Generate audit report: total docs, quality distribution, flagged docs, recommendations
  - Output: audit report stored in `kb_review_queue` for Boss review before any deletions
  - DO NOT auto-delete anything — Boss reviews and decides
  - Add CLI command: `python -m src.knowledge_base.audit` for manual trigger

  **Must NOT do**:
  - Do NOT auto-delete flagged documents — everything goes through review
  - Do NOT re-embed all documents — only flag quality issues

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Batch processing, LLM-assisted quality scoring, similarity computation, report generation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T17-T20, T22-T23)
  - **Parallel Group**: Wave 3
  - **Blocks**: T39 (import pipeline should run after audit)
  - **Blocked By**: T1 (KB review queue table)

  **References**:

  **Pattern References**:
  - `src/knowledge_base/` — Existing RAG engine (Document model, embedding generation, pgvector search)
  - `src/db/models.py:Document, Chunk` — Existing document storage schema

  **WHY Each Reference Matters**:
  - `knowledge_base/` — Audit reads from existing document store and uses embedding for similarity checks

  **Acceptance Criteria**:
  - [ ] `src/knowledge_base/audit.py` exists
  - [ ] Audit scans all 550 docs and generates report
  - [ ] Flagged docs (low quality, duplicates) identified
  - [ ] Report submitted to KB review queue for Boss review
  - [ ] CLI command works

  **QA Scenarios**:

  ```
  Scenario: Audit pipeline runs on existing docs
    Tool: Bash (docker exec)
    Preconditions: Container running, 550 docs in DB
    Steps:
      1. sudo docker exec amazon-ai-app python3 -m src.knowledge_base.audit
    Expected Result: Prints audit summary (total, flagged, quality distribution)
    Failure Indicators: Error, zero docs scanned, crash
    Evidence: .sisyphus/evidence/task-21-kb-audit.txt
  ```

  **Commit**: YES (group with T17-T20, T22-T23 as Wave 3)
  - Message: `feat(agents): first 3 agents chat mode + KB review + HITL UI + Feishu refactor`
  - Files: `src/knowledge_base/audit.py`
  - Pre-commit: `pytest`

- [ ] 22. HITL Approval UI Component (Approve/Reject/Comment)

  **What to do**:
  - Create `src/frontend/src/pages/Approvals.tsx`:
    - Route: `/approvals`
    - List of all pending approval requests from all agents
    - Filterable by: agent type, date, severity
    - Each item shows: agent name, action type, content preview, timestamp
    - Detail view: full content, agent reasoning, target action description
    - Actions: Approve (green button), Reject (red button + comment field)
    - Real-time update via polling or SSE when new approvals arrive
    - Badge count in sidebar showing pending approvals
  - Create `src/frontend/src/components/ApprovalCard.tsx`:
    - Reusable card showing approval request details
    - Expandable content section
    - Inline approve/reject buttons
  - Wire to `GET /api/approvals`, `POST /api/approvals/{id}/approve`, `POST /api/approvals/{id}/reject` from T10

  **Must NOT do**:
  - Do NOT show auditor-related approvals to operators
  - Do NOT allow approve without reviewing content

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Interactive list/detail UI with real-time updates, approval workflow
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T17-T21, T23)
  - **Parallel Group**: Wave 3
  - **Blocks**: None (T20 handles KB-specific review)
  - **Blocked By**: T10 (HITL backend), T14 (chat component patterns)

  **References**:

  **Pattern References**:
  - `src/services/approval.py` — Backend approval service from T10
  - `src/frontend/src/pages/KBReview.tsx` — Similar list/detail/action pattern from T20

  **Acceptance Criteria**:
  - [ ] Approvals page renders at `/approvals`
  - [ ] Pending items listed with correct agent attribution
  - [ ] Approve triggers backend action
  - [ ] Reject records comment
  - [ ] Badge count in sidebar updates
  - [ ] RBAC: operator cannot see auditor approvals

  **QA Scenarios**:

  ```
  Scenario: Approve flow via UI
    Tool: Playwright
    Preconditions: Pending approval exists, logged in as boss
    Steps:
      1. Navigate to /approvals
      2. Verify pending count badge visible
      3. Click first pending item
      4. Review content
      5. Click "Approve"
      6. Verify item removed from pending list
    Expected Result: Approval processed, list updated
    Failure Indicators: Item still pending after approve, error
    Evidence: .sisyphus/evidence/task-22-approval-ui.png
  ```

  **Commit**: YES (group with T17-T21, T23 as Wave 3)
  - Message: `feat(agents): first 3 agents chat mode + KB review + HITL UI + Feishu refactor`
  - Files: `src/frontend/src/pages/Approvals.tsx`, `src/frontend/src/components/ApprovalCard.tsx`
  - Pre-commit: `npm run build`

- [ ] 23. Feishu Notification-Only Refactor

  **What to do**:
  - Refactor `src/feishu/bot_handler.py`:
    - Remove interactive chat handling (Q&A, RAG queries) — web handles this now
    - Keep notification methods:
      - `send_daily_report(report)` — daily summary notification
      - `send_approval_request(request)` — notify boss of pending approval
      - `send_task_completion(task)` — notify when agent task completes
      - `send_alert(alert)` — urgent alerts (inventory low, ad budget exceeded)
    - Keep webhook endpoint for receiving Feishu events (but respond with "Please use web interface")
  - Create `src/feishu/notifications.py` — clean notification service:
    - Simple methods for each notification type
    - Configurable: enable/disable per notification type
    - Format messages with Feishu card template (rich format)
  - Update cron jobs to use new notification methods
  - Remove Feishu as primary interaction channel from documentation/comments

  **Must NOT do**:
  - Do NOT delete `bot_handler.py` entirely — refactor to minimal
  - Do NOT remove webhook endpoint — keep for receiving events
  - Do NOT break existing Feishu bot token/app configuration

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Mostly deletion + cleanup + simple notification methods, well-scoped
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (independent of all other tasks)
  - **Parallel Group**: Wave 3 (or earlier)
  - **Blocks**: None
  - **Blocked By**: None (can start anytime)

  **References**:

  **Pattern References**:
  - `src/feishu/bot_handler.py` — Current Feishu bot (full interactive handler) — strip to notifications
  - `src/scheduler/config.py` — Cron jobs that trigger Feishu notifications

  **WHY Each Reference Matters**:
  - `bot_handler.py` — The file being refactored. Understand what to keep (notifications) vs remove (chat)
  - `scheduler/config.py` — Must update to use new notification methods

  **Acceptance Criteria**:
  - [ ] `src/feishu/notifications.py` exists with clean notification methods
  - [ ] Interactive chat removed from bot_handler
  - [ ] Daily report notification still works
  - [ ] Alert notifications still works
  - [ ] Webhook endpoint responds with "use web interface" message

  **QA Scenarios**:

  ```
  Scenario: Notification methods work
    Tool: Bash (docker exec python3)
    Preconditions: Feishu config valid
    Steps:
      1. sudo docker exec amazon-ai-app python3 -c "
         from src.feishu.notifications import send_alert
         result = send_alert('Test alert from Phase 4 refactor')
         print(f'Sent: {result}')
         "
    Expected Result: Notification sent successfully (or returns true if Feishu configured)
    Failure Indicators: ImportError, send failure
    Evidence: .sisyphus/evidence/task-23-feishu-notification.txt

  Scenario: Interactive chat removed
    Tool: Bash (grep)
    Preconditions: Code deployed
    Steps:
      1. Search bot_handler.py for RAG/chat handling code
      2. Verify those functions are removed or simplified
    Expected Result: No complex chat handling in bot_handler.py
    Failure Indicators: Still has full chat/RAG pipeline in Feishu handler
    Evidence: .sisyphus/evidence/task-23-feishu-stripped.txt
  ```

  **Commit**: YES (group with T17-T22 as Wave 3)
  - Message: `feat(agents): first 3 agents chat mode + KB review + HITL UI + Feishu refactor`
  - Files: `src/feishu/bot_handler.py`, `src/feishu/notifications.py`
  - Pre-commit: `pytest`

### Wave 4 — Remaining Agents Chat Mode + New Agents (After Wave 3 Core)

- [ ] 24. Product Whitepaper Agent → Chat Mode

  **What to do**:
  - Create `src/agents/whitepaper_agent/chat_agent.py` extending `ChatBaseAgent`:
    - Chat flow: user provides product details → agent asks clarifying questions → generates product whitepaper
    - Support image upload context (user can reference uploaded images in chat)
    - Output format: structured markdown with sections matching product listing needs
    - HITL: whitepaper goes to approval before storage, named by SKU+date
  - Follow T17 pattern exactly (ChatBaseAgent extension, tool registration, HITL integration)

  **Must NOT do**:
  - Do NOT auto-store whitepapers without approval
  - Do NOT break existing `run()` method

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Standard agent migration following T17 pattern
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T25-T34)
  - **Parallel Group**: Wave 4
  - **Blocks**: None
  - **Blocked By**: T17 (pattern established)

  **References**:
  - `src/agents/whitepaper_agent/agent.py` — Existing agent
  - `src/agents/core_agent/chat_agent.py` — T17 pattern reference

  **Acceptance Criteria**:
  - [ ] Chat agent works with product whitepaper workflow
  - [ ] HITL approval before storage
  - [ ] Existing `run()` preserved

  **QA Scenarios**:
  ```
  Scenario: Whitepaper chat with approval
    Tool: Playwright
    Steps:
      1. Navigate to /agents/whitepaper, chat about a product
      2. Verify structured whitepaper output generated
      3. Check /approvals for pending whitepaper
    Expected Result: Whitepaper in approval queue
    Evidence: .sisyphus/evidence/task-24-whitepaper-chat.png
  ```

  **Commit**: YES (group with T25-T34 as Wave 4)
  - Message: `feat(agents): remaining 8 agents chat mode + keyword builder + auditor + SP-API Brand Analytics`
  - Files: `src/agents/whitepaper_agent/chat_agent.py`
  - Pre-commit: `pytest`

- [ ] 25. Competitor Agent → Chat Mode + Monthly Auto-Monitor

  **What to do**:
  - Create `src/agents/competitor_agent/chat_agent.py` extending `ChatBaseAgent`:
    - Chat flow: user specifies competitors or category → agent collects data → produces analysis
    - Tools: Seller Sprite MCP (get_asin_data, reverse_lookup), SP-API catalog
    - Support up to 200 competitor samples per analysis
    - Monthly auto-monitoring: scheduler triggers monthly competitor scan for tracked products
    - Alert on significant changes (price drop >10%, new competitor, review surge)
  - Add monthly competitor scan to scheduler config
  - HITL: analysis goes to approval before storage

  **Must NOT do**:
  - Do NOT auto-act on competitor changes — alert only
  - Do NOT exceed 200 samples per analysis run

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Standard agent migration + scheduler integration
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T24, T26-T34)
  - **Parallel Group**: Wave 4
  - **Blocks**: None
  - **Blocked By**: T17 (pattern)

  **References**:
  - `src/agents/competitor_agent/agent.py` — Existing competitor research agent
  - `src/scheduler/config.py` — Add monthly schedule

  **Acceptance Criteria**:
  - [ ] Chat agent works for competitor analysis
  - [ ] Monthly auto-scan scheduled
  - [ ] Supports up to 200 samples
  - [ ] HITL approval before storage

  **QA Scenarios**:
  ```
  Scenario: Competitor analysis chat
    Tool: Playwright
    Steps:
      1. Navigate to /agents/competitor, ask "Analyze top 10 pet leash competitors"
      2. Verify response includes competitor data
    Expected Result: Structured competitor analysis
    Evidence: .sisyphus/evidence/task-25-competitor-chat.png
  ```

  **Commit**: YES (group with Wave 4)
  - Files: `src/agents/competitor_agent/chat_agent.py`, `src/scheduler/config.py`
  - Pre-commit: `pytest`

- [ ] 26. User Persona Agent → Chat Mode

  **What to do**:
  - Create `src/agents/persona_agent/chat_agent.py` extending `ChatBaseAgent`:
    - Chat flow: user provides product/category → agent generates user persona analysis
    - Tools: Seller Sprite, knowledge base, review analysis
    - Monthly auto-refresh for tracked products
    - HITL: persona analysis goes to approval
  - Follow T17 pattern

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T24-T25, T27-T34)
  - **Parallel Group**: Wave 4
  - **Blocked By**: T17

  **References**:
  - `src/agents/persona_agent/agent.py` — Existing agent
  - `src/agents/core_agent/chat_agent.py` — T17 pattern

  **Acceptance Criteria**:
  - [ ] Chat agent produces persona analysis
  - [ ] HITL approval
  - [ ] Monthly auto-refresh scheduled

  **QA Scenarios**:
  ```
  Scenario: Persona analysis
    Tool: Playwright
    Steps: Navigate to /agents/persona, ask for persona analysis
    Expected Result: Structured persona with demographics, pain points, buying behavior
    Evidence: .sisyphus/evidence/task-26-persona-chat.png
  ```

  **Commit**: YES (group with Wave 4)
  - Files: `src/agents/persona_agent/chat_agent.py`

- [ ] 27. Keyword Library Builder Agent (NEW)

  **What to do**:
  - Create `src/agents/keyword_library/` directory with:
    - `agent.py` — BaseAgent `run()` for scheduled execution
    - `chat_agent.py` — ChatBaseAgent for interactive chat mode
    - `tools.py` — Tools for keyword collection and categorization
  - Implement 4-step SOP from `产品词库搭建SOP.docx`:
    - Step 1: Collect ASINs (20 main + 5-10 related) — user provides or auto-detect from product catalog
    - Step 2: Mine keywords via Seller Sprite MCP (`search_keyword`, `reverse_lookup`) + SP-API Brand Analytics (T33) + SP-API Search Term Report
    - Step 3: De-duplicate, categorize by search volume (>500 high, 100-500 medium, <100 low)
    - Step 4: Judge relevance (high / weak / seemingly-related-but-not / completely-unrelated) — AI-assisted + human review
  - Store in `keyword_libraries` table (from T1)
  - Monthly monitoring: track keyword rank changes, new keywords, dropped keywords
  - Chat mode: user can ask questions about keyword library, request new keyword research, review and approve/reject keywords
  - HITL: keyword categorization and relevance judgment go to human review

  **Must NOT do**:
  - Do NOT auto-add keywords without human relevance review
  - Do NOT skip de-duplication step
  - Do NOT hardcode ASIN lists — must be configurable per product

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: New agent from scratch, complex 4-step SOP, multi-source data integration, classification logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T24-T26, T28-T34)
  - **Parallel Group**: Wave 4
  - **Blocks**: T35 (ad optimization needs keyword library)
  - **Blocked By**: T17 (ChatBaseAgent pattern), T33 (Brand Analytics for data source)

  **References**:

  **Pattern References**:
  - `src/agents/core_agent/chat_agent.py` — Chat pattern from T17
  - `src/agents/selection_agent/agent.py` — Similar Seller Sprite tool usage pattern
  - `src/seller_sprite/client.py` — MCP client for search_keyword, reverse_lookup, get_asin_data, get_category_data methods
  - `src/amazon_sp_api/reports.py` — SP-API report request pattern (for Search Term Report)

  **External References**:
  - `产品词库搭建SOP.docx` — The 4-step SOP specification (complete workflow)
  - Seller Sprite MCP: `https://open.sellersprite.com/mcp` — keyword mining endpoints

  **WHY Each Reference Matters**:
  - SOP document — Defines the EXACT 4-step workflow, not to be deviated from
  - Seller Sprite client — Data source #1 for keyword mining
  - SP-API reports — Data source #2 (Brand Analytics) and #3 (Search Term Report)

  **Acceptance Criteria**:
  - [ ] `src/agents/keyword_library/` directory with agent.py, chat_agent.py, tools.py
  - [ ] 4-step SOP implemented: collect ASINs → mine keywords → categorize → judge relevance
  - [ ] Keywords stored in `keyword_libraries` table with source, volume, tier, relevance
  - [ ] Seller Sprite MCP integration working
  - [ ] Chat mode allows interactive keyword research
  - [ ] HITL: relevance judgments go to approval
  - [ ] Monthly monitoring scheduled

  **QA Scenarios**:

  ```
  Scenario: Keyword research for a product
    Tool: Playwright
    Preconditions: Full stack, Seller Sprite MCP configured
    Steps:
      1. Navigate to /agents/keyword_library
      2. Chat: "Build keyword library for ASIN B0FPFZ7XFJ (pet water fountain)"
      3. Wait for agent to collect and categorize keywords
      4. Verify response includes keywords with volume and relevance tiers
      5. Check /approvals for pending keyword relevance review
    Expected Result: Keywords collected, categorized, submitted for review
    Failure Indicators: No keywords, no categories, no approval created
    Evidence: .sisyphus/evidence/task-27-keyword-library.png

  Scenario: Keyword data from multiple sources
    Tool: Bash (docker exec)
    Preconditions: After keyword research run
    Steps:
      1. Query keyword_libraries table for sources
      2. Verify entries from multiple sources (seller_sprite, brand_analytics, search_term_report)
    Expected Result: Keywords from at least 2 different sources
    Failure Indicators: Only one source
    Evidence: .sisyphus/evidence/task-27-multi-source.txt
  ```

  **Commit**: YES (group with Wave 4)
  - Message: `feat(agents): remaining 8 agents chat mode + keyword builder + auditor + SP-API Brand Analytics`
  - Files: `src/agents/keyword_library/`
  - Pre-commit: `pytest`

- [ ] 28. Listing Planning Agent → Chat Mode

  **What to do**:
  - Create `src/agents/listing_agent/chat_agent.py` extending `ChatBaseAgent`:
    - Chat flow: user provides product + keyword library → agent creates listing plan (title, bullets, description, backend keywords)
    - Tools: knowledge base, keyword library query, competitor listings reference
    - Monthly monitoring: compare live listing with plan, generate optimization report
    - HITL: listing plan goes to approval before any action
  - Follow T17 pattern

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T24-T27, T29-T34)
  - **Parallel Group**: Wave 4
  - **Blocked By**: T17

  **References**:
  - `src/agents/listing_agent/agent.py` — Existing agent
  - `src/agents/core_agent/chat_agent.py` — T17 pattern

  **Acceptance Criteria**:
  - [ ] Chat agent generates listing plans
  - [ ] HITL approval before action
  - [ ] Monthly optimization reports scheduled

  **QA Scenarios**:
  ```
  Scenario: Listing plan generation
    Tool: Playwright
    Steps: Navigate to /agents/listing, request listing plan for a product
    Expected Result: Structured listing (title, 5 bullets, description, keywords)
    Evidence: .sisyphus/evidence/task-28-listing-chat.png
  ```

  **Commit**: YES (group with Wave 4)
  - Files: `src/agents/listing_agent/chat_agent.py`

- [ ] 29. Listing Images Agent → Chat Mode

  **What to do**:
  - Create `src/agents/image_gen_agent/chat_agent.py` extending `ChatBaseAgent`:
    - Chat flow: user describes image needs → agent generates 4 image prompts per request
    - User selects preferred images, provides feedback for iteration
    - HITL: final images go to approval before upload
  - Follow T17 pattern

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4
  - **Blocked By**: T17

  **References**:
  - `src/agents/image_gen_agent/agent.py` — Existing agent

  **Acceptance Criteria**:
  - [ ] Chat agent supports image prompt generation
  - [ ] 4 images per request
  - [ ] HITL approval before upload

  **QA Scenarios**:
  ```
  Scenario: Image generation chat
    Tool: Playwright
    Steps: Navigate to /agents/image_generation, request product images
    Expected Result: Agent produces 4 image descriptions/prompts
    Evidence: .sisyphus/evidence/task-29-images-chat.png
  ```

  **Commit**: YES (group with Wave 4)
  - Files: `src/agents/image_gen_agent/chat_agent.py`

- [ ] 30. Product Listing Upload Agent → Chat Mode

  **What to do**:
  - Create `src/agents/product_listing_agent/chat_agent.py` extending `ChatBaseAgent`:
    - Chat flow: user selects listing plan → agent prepares upload payload → preview → confirm → execute
    - Preview: show exact field values that will be uploaded (字符级一致 with planning document)
    - Field-level updates: can update individual fields without full re-upload
    - HITL: mandatory preview + confirm before SP-API call
  - Strict constraint: uploaded text must EXACTLY match planning document (zero character deviation)

  **Must NOT do**:
  - Do NOT modify text during upload — exact copy from approved listing plan
  - Do NOT auto-execute SP-API writes — mandatory preview + confirm

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4
  - **Blocked By**: T17

  **References**:
  - `src/agents/product_listing_agent/agent.py` — Existing agent
  - `src/amazon_sp_api/` — SP-API client for actual upload

  **Acceptance Criteria**:
  - [ ] Preview shows exact upload payload
  - [ ] Confirm step before SP-API call
  - [ ] Text matches planning document exactly (zero deviation)
  - [ ] Field-level updates supported

  **QA Scenarios**:
  ```
  Scenario: Listing upload preview
    Tool: Playwright
    Steps: Navigate to /agents/product_listing, select a listing plan, verify preview matches plan exactly
    Expected Result: Preview shows identical text to planning document
    Evidence: .sisyphus/evidence/task-30-upload-preview.png
  ```

  **Commit**: YES (group with Wave 4)
  - Files: `src/agents/product_listing_agent/chat_agent.py`

- [ ] 31. Inventory & Shipping Agent → Chat Mode

  **What to do**:
  - Create `src/agents/inventory_agent/chat_agent.py` extending `ChatBaseAgent`:
    - Chat flow: user asks about inventory status → agent provides analysis + recommendations
    - Daily monitoring: 60-day threshold alerts for low stock
    - Shipment creation assistance via chat
    - HITL: shipment creation goes to approval
  - Follow T17 pattern

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4
  - **Blocked By**: T17

  **References**:
  - `src/agents/inventory_agent/agent.py` — Existing agent

  **Acceptance Criteria**:
  - [ ] Chat agent provides inventory analysis
  - [ ] 60-day threshold alerts work
  - [ ] Shipment creation with HITL approval

  **QA Scenarios**:
  ```
  Scenario: Inventory status check
    Tool: Playwright
    Steps: Navigate to /agents/inventory, ask "What's our current inventory status?"
    Expected Result: Structured inventory report with recommendations
    Evidence: .sisyphus/evidence/task-31-inventory-chat.png
  ```

  **Commit**: YES (group with Wave 4)
  - Files: `src/agents/inventory_agent/chat_agent.py`

- [ ] 32. Auditor Agent (NEW, Boss-Only)

  **What to do**:
  - Create `src/agents/auditor/` directory with:
    - `agent.py` — BaseAgent `run()` for automated scanning
    - `chat_agent.py` — ChatBaseAgent for boss interactive queries
    - `rules.py` — Auditing rule definitions
  - Auditor functionality:
    - Reviews ALL agent outputs before/after execution
    - Rules engine:
      - **Critical (auto-block)**: Budget overrun >20%, unauthorized SP-API writes, missing HITL approval, data inconsistency
      - **Warning (alert)**: Unusual spending patterns, keyword stuffing, duplicate content, deviation from brand guidelines
      - **Info (log)**: Normal operations, performance metrics
    - Stores findings in `auditor_logs` table
    - Chat mode (boss-only): boss can ask auditor questions about agent behavior, compliance, trends
  - RBAC: STRICTLY boss-only — all endpoints, all UI, all logs
  - Operator cannot see auditor in sidebar, cannot access endpoints, cannot see logs

  **Must NOT do**:
  - Do NOT make auditor visible to operators in any way
  - Do NOT auto-fix findings — report only (boss decides action)
  - Do NOT audit auditor itself (no recursive auditing)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: New agent, rules engine, cross-agent monitoring, strict RBAC, complex logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T24-T31, T33-T34)
  - **Parallel Group**: Wave 4
  - **Blocks**: None
  - **Blocked By**: T2 (RBAC), T17 (ChatBaseAgent pattern)

  **References**:

  **Pattern References**:
  - `src/agents/core_agent/chat_agent.py` — T17 chat pattern
  - `src/db/models.py:AuditorLog` — Auditor log table from T1
  - `src/db/models.py:AuditLog` — Existing audit log table (different from auditor — this is system audit trail)
  - `src/api/dependencies.py` — RBAC from T2 (`require_role`) for strict boss-only enforcement

  **WHY Each Reference Matters**:
  - `AuditorLog` vs `AuditLog` — Different tables! AuditorLog is for the auditor agent's findings. AuditLog is the system audit trail. Don't confuse them.
  - `dependencies.py` — Every auditor endpoint MUST use `Depends(require_role("boss"))` imported from `src/api/dependencies.py`

  **Acceptance Criteria**:
  - [ ] `src/agents/auditor/` directory with complete agent
  - [ ] Rules engine with critical/warning/info severity levels
  - [ ] Critical findings auto-block the action
  - [ ] Warnings logged, alerts sent to boss
  - [ ] Chat mode for boss queries about agent compliance
  - [ ] 100% boss-only (operator cannot access any auditor feature)
  - [ ] Operator cannot see auditor in sidebar, API returns 403

  **QA Scenarios**:

  ```
  Scenario: Auditor blocks critical violation
    Tool: Bash (curl)
    Preconditions: Auditor configured, simulate a budget overrun scenario
    Steps:
      1. Trigger an agent action that violates a critical rule (e.g., ad budget >20% over limit)
      2. Check auditor_logs for the finding
      3. Verify the action was blocked
    Expected Result: Action blocked, auditor log entry with severity="critical", auto_action="blocked"
    Failure Indicators: Action executed despite violation
    Evidence: .sisyphus/evidence/task-32-auditor-block.txt

  Scenario: Operator cannot access auditor
    Tool: Bash (curl)
    Preconditions: Operator token
    Steps:
      1. curl -s -w "%{http_code}" -H "Authorization: Bearer $OP_TOKEN" -H "Content-Type: application/json" -X POST http://localhost:8000/api/agents/auditor/run -d '{"params":{}}'
      2. curl -s -w "%{http_code}" -H "Authorization: Bearer $OP_TOKEN" http://localhost:8000/api/chat/conversations -d '{"agent_type":"auditor"}'
    Expected Result: Both return 403
    Failure Indicators: Any 200 response
    Evidence: .sisyphus/evidence/task-32-auditor-rbac.txt
  ```

  **Commit**: YES (group with Wave 4)
  - Message: `feat(agents): remaining 8 agents chat mode + keyword builder + auditor + SP-API Brand Analytics`
  - Files: `src/agents/auditor/`
  - Pre-commit: `pytest`

- [ ] 33. SP-API Brand Analytics Integration

  **What to do**:
  - Add `GET_BRAND_ANALYTICS_SEARCH_TERMS` to `REPORT_TYPES` dict in `src/amazon_sp_api/reports.py`
  - Add `GET_BRAND_ANALYTICS_REPEAT_PURCHASE` report type (bonus if available)
  - Create `src/amazon_sp_api/brand_analytics.py`:
    - `request_search_terms_report(marketplace, date_range) → report_id`
    - `get_search_terms_data(report_id) → list[SearchTermRecord]`
    - `parse_search_terms(raw_data) → list[dict]` — extract: search term, search frequency rank, clicked ASINs, conversion share
  - Integrate with keyword library builder (T27):
    - Brand Analytics search terms feed into keyword library as a data source
    - Source tagged as `brand_analytics` in keyword_libraries table
  - Note: Requires Brand Registry. Add graceful fallback if store is not Brand Registered

  **Must NOT do**:
  - Do NOT hardcode marketplace — parameterize
  - Do NOT fail catastrophically if Brand Registry not available — graceful degradation

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: SP-API integration, report parsing, data pipeline
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T24-T32, T34)
  - **Parallel Group**: Wave 4
  - **Blocks**: T27 (keyword library data source)
  - **Blocked By**: T1 (keyword_libraries table)

  **References**:

  **Pattern References**:
  - `src/amazon_sp_api/reports.py` — Existing report types and request/download pattern — add Brand Analytics following same pattern
  - `src/amazon_sp_api/client.py` — SP-API client setup and auth

  **External References**:
  - SP-API Brand Analytics docs: https://developer-docs.amazon.com/sp-api/docs/brand-analytics-api

  **WHY Each Reference Matters**:
  - `reports.py` — Must follow exact same report request/polling/download pattern for consistency
  - Brand Analytics API docs — Report type name, parameters, response format

  **Acceptance Criteria**:
  - [ ] `GET_BRAND_ANALYTICS_SEARCH_TERMS` in REPORT_TYPES
  - [ ] `src/amazon_sp_api/brand_analytics.py` exists with request + parse methods
  - [ ] Search terms data parseable into keyword format
  - [ ] Graceful fallback if Brand Registry not available
  - [ ] Integration with keyword library builder

  **QA Scenarios**:

  ```
  Scenario: Brand Analytics report type registered
    Tool: Bash (docker exec)
    Steps:
      1. sudo docker exec amazon-ai-app python3 -c "
         from src.amazon_sp_api.reports import REPORT_TYPES
         print('Brand Analytics' in str(REPORT_TYPES))
         print(REPORT_TYPES.get('brand_analytics_search_terms', 'NOT FOUND'))
         "
    Expected Result: True, report type config printed
    Failure Indicators: NOT FOUND
    Evidence: .sisyphus/evidence/task-33-brand-analytics.txt
  ```

  **Commit**: YES (group with Wave 4)
  - Files: `src/amazon_sp_api/reports.py`, `src/amazon_sp_api/brand_analytics.py`
  - Pre-commit: `pytest`

- [ ] 34. Multi-Model Agent Configuration

  **What to do**:
  - Create `src/agents/model_config.py` — centralized model assignment:
    - Dict mapping agent_type → preferred model:
      - `core_management` → GPT-4o (strong reasoning)
      - `brand_planning` → Claude-3.5-sonnet (analytical writing)
      - `selection` → GPT-4o (data analysis)
      - `keyword_library` → GPT-4o-mini (high volume, lower cost)
      - `auditor` → Claude-3.5-sonnet (rule interpretation)
      - `ad_monitor` → GPT-4o (optimization math)
      - Default → GPT-4o-mini (cost efficient)
    - Fallback: if preferred model fails, fall back to default
    - Configurable via environment variable or system_config table
  - Update `ChatBaseAgent.get_model()` to read from this config
  - Add admin UI option (System Management) to change model assignments

  **Must NOT do**:
  - Do NOT hardcode model names in agent files — use centralized config
  - Do NOT remove existing model support — additive only

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Configuration mapping, straightforward
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T24-T33)
  - **Parallel Group**: Wave 4
  - **Blocked By**: T5 (ChatBaseAgent)

  **References**:
  - `src/llm/client.py` — Existing model routing logic
  - `src/config.py` — Settings pattern for configuration

  **Acceptance Criteria**:
  - [ ] `src/agents/model_config.py` exists
  - [ ] Each agent uses its assigned model
  - [ ] Fallback works if preferred model fails
  - [ ] Config changeable via system_config

  **QA Scenarios**:
  ```
  Scenario: Agents use configured models
    Tool: Bash (docker exec)
    Steps:
      1. sudo docker exec amazon-ai-app python3 -c "
         from src.agents.model_config import get_model_for_agent
         print(get_model_for_agent('brand_planning'))
         print(get_model_for_agent('keyword_library'))
         "
    Expected Result: claude-3.5-sonnet for brand_planning, gpt-4o-mini for keyword_library
    Evidence: .sisyphus/evidence/task-34-model-config.txt
  ```

  **Commit**: YES (group with Wave 4)
  - Files: `src/agents/model_config.py`

### Wave 5 — Ad Optimization Engine (After Wave 4 for Keyword Library)

- [ ] 35. Ad Optimization Core Algorithm

  **What to do**:
  - Create `src/agents/ad_monitor_agent/algorithm/` directory:
    - `core.py` — Main optimization logic implementing NextGen algorithm from `亚马逊广告优化算法.txt`:
      - **Cold Start Module**: Zero-impression probing (10% incremental bids), 3x avg CPC cap, Bayesian smoothing for insufficient data
      - **Mature Phase Module**: D-4 to D-30 attribution window analysis, dynamic elasticity coefficients, N-gram keyword analysis, funnel migration tracking (impression→click→cart→purchase)
      - **Multi-dimensional Optimization**: 80/20 explore/exploit ratio, Lagrangian budget allocation across campaigns, position tilt scoring, dayparting analysis
      - **Safety Rails**: 24h cooldown between adjustments, 5%/$0.02 minimum adjustment, 20% circuit breaker (max single adjustment), oscillation detection (3+ reversals in 7 days), minimum impression protection
      - **Business Awareness**: ASP change detection, inventory protection (pause ads if stock <14 days), organic rank synergy (reduce paid if organic improving)
    - `models.py` — Data classes for: Campaign, AdGroup, Keyword, BidRecommendation, OptimizationResult
    - `metrics.py` — ACOS, ROAS, TACoS, CPC, CTR, CVR calculation utilities
    - `safety.py` — Safety rails implementation (cooldown, circuit breaker, oscillation detection)
  - All calculations use historical data — NO live API calls in algorithm
  - Algorithm outputs `BidRecommendation` objects that go through HITL approval before execution

  **Must NOT do**:
  - Do NOT call Amazon Ads API from algorithm module — algorithm is pure computation
  - Do NOT skip safety rails — all 5 safety mechanisms mandatory
  - Do NOT exceed 20% bid change in single adjustment (circuit breaker)
  - Do NOT make adjustments within 24h of previous adjustment (cooldown)

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
    - Reason: Complex mathematical optimization, Bayesian methods, Lagrangian allocation, safety system design
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (foundational for T36, T37, T38)
  - **Parallel Group**: Wave 5 (first in wave)
  - **Blocks**: T36
  - **Blocked By**: T27 (keyword library for keyword-level optimization), T33 (Brand Analytics for data)

  **References**:

  **Pattern References**:
  - `亚马逊广告优化算法.txt:1-97` — Complete algorithm specification — THIS IS THE PRIMARY REFERENCE, implement faithfully

  **API/Type References**:
  - `src/amazon_ads_api/` — Ads API client (for data structures, NOT for calling from algorithm)
  - `src/db/models.py:AdSimulation, AdOptimizationLog` — Storage models from T1

  **External References**:
  - Friend's reference: https://www.ppcopt.com/how-it-works — Additional algorithm inspiration

  **WHY Each Reference Matters**:
  - `亚马逊广告优化算法.txt` — THE specification. Every module described must be implemented. No shortcuts.
  - Ads API — Data structure reference only. Algorithm reads historical data, never makes API calls.

  **Acceptance Criteria**:
  - [ ] `src/agents/ad_monitor_agent/algorithm/` exists with core.py, models.py, metrics.py, safety.py
  - [ ] Cold start module: Bayesian smoothing, incremental bidding, CPC cap
  - [ ] Mature phase: attribution windows, elasticity, N-gram, funnel tracking
  - [ ] Multi-dimensional: explore/exploit, Lagrangian allocation, dayparting
  - [ ] Safety rails: all 5 mechanisms implemented and tested
  - [ ] Business awareness: ASP detection, inventory protection, organic synergy
  - [ ] Algorithm produces BidRecommendation objects (no API calls)
  - [ ] pytest tests for each module with test data

  **QA Scenarios**:

  ```
  Scenario: Safety rails prevent dangerous bid changes
    Tool: Bash (docker exec python3)
    Preconditions: Algorithm module deployed
    Steps:
      1. sudo docker exec amazon-ai-app python3 -c "
         from src.agents.ad_monitor_agent.algorithm.safety import SafetyRails
         from src.agents.ad_monitor_agent.algorithm.models import BidRecommendation
         rails = SafetyRails()
         # Test circuit breaker: 25% increase should be capped to 20%
         rec = BidRecommendation(keyword='test', current_bid=1.00, recommended_bid=1.25)
         safe_rec = rails.apply(rec)
         print(f'Original: {rec.recommended_bid}, Safe: {safe_rec.recommended_bid}')
         assert safe_rec.recommended_bid <= 1.20, 'Circuit breaker failed!'
         print('Circuit breaker: PASS')
         "
    Expected Result: Bid capped at 1.20 (20% max), prints "Circuit breaker: PASS"
    Failure Indicators: Bid exceeds 1.20, assertion error
    Evidence: .sisyphus/evidence/task-35-safety-rails.txt

  Scenario: Algorithm produces recommendations without API calls
    Tool: Bash (docker exec python3)
    Preconditions: Algorithm module deployed, test data available
    Steps:
      1. Run algorithm with sample historical data
      2. Verify output is list of BidRecommendation objects
      3. Verify no network calls were made (mock check)
    Expected Result: Recommendations generated from data alone
    Failure Indicators: Network calls detected, empty recommendations
    Evidence: .sisyphus/evidence/task-35-algo-no-api.txt
  ```

  **Commit**: YES (group with T36-T38 as Wave 5)
  - Message: `feat(ads): optimization core algorithm + simulation engine + dashboard`
  - Files: `src/agents/ad_monitor_agent/algorithm/`
  - Pre-commit: `pytest tests/test_ad_algorithm.py`

- [ ] 36. Ad Simulation Engine

  **What to do**:
  - Create `src/agents/ad_monitor_agent/simulation/` directory:
    - `engine.py` — Simulation engine that tests algorithm against historical data:
      - Load historical campaign data (impressions, clicks, conversions, spend, bids)
      - Run algorithm on historical data
      - Compare algorithm recommendations vs actual decisions
      - Calculate simulated ACOS, ROAS, TACoS if recommendations had been applied
      - Generate simulation report: improvement metrics, risk assessment, confidence level
    - `data_loader.py` — Load and prepare historical data for simulation
    - `reporter.py` — Generate simulation results report (markdown + charts data)
  - Simulation modes:
    - **Backtest**: Run algorithm on past N days of data, compare with actual results
    - **What-if**: User changes parameters, see projected outcomes
    - **Stress test**: Extreme scenarios (budget cut 50%, competitor price war, seasonal spike)
  - Store simulation results in `ad_simulations` table (from T1)
  - HITL: simulation results reviewed by boss before algorithm goes live

  **Must NOT do**:
  - Do NOT call Amazon Ads API — simulation uses ONLY historical data
  - Do NOT present simulation results as guarantees — clearly label as projections
  - Do NOT auto-deploy algorithm based on simulation results — boss must approve

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
    - Reason: Statistical simulation, backtesting methodology, confidence intervals, report generation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T35 algorithm)
  - **Parallel Group**: Wave 5 (after T35)
  - **Blocks**: T37, T38
  - **Blocked By**: T35 (core algorithm)

  **References**:

  **Pattern References**:
  - `src/agents/ad_monitor_agent/algorithm/` — Algorithm from T35 (simulation runs this algorithm)
  - `src/amazon_ads_api/` — Data structures for historical campaign data
  - `src/db/models.py:AdSimulation` — Storage model from T1

  **WHY Each Reference Matters**:
  - Algorithm module — Simulation is a TEST HARNESS for the algorithm. It must import and run the algorithm correctly.

  **Acceptance Criteria**:
  - [ ] `src/agents/ad_monitor_agent/simulation/` exists with engine, data_loader, reporter
  - [ ] Backtest mode works with historical data
  - [ ] What-if mode allows parameter changes
  - [ ] Results stored in ad_simulations table
  - [ ] No Amazon Ads API calls during simulation
  - [ ] Clear labeling as projections, not guarantees

  **QA Scenarios**:

  ```
  Scenario: Backtest simulation runs without API calls
    Tool: Bash (docker exec python3)
    Preconditions: Historical ad data in DB, algorithm module deployed
    Steps:
      1. Run simulation backtest on last 30 days of data
      2. Verify results include: simulated ACOS, comparison with actual, improvement %
      3. Verify no network calls to Amazon Ads API
    Expected Result: Simulation report generated with comparison metrics
    Failure Indicators: API calls detected, empty results, crash
    Evidence: .sisyphus/evidence/task-36-simulation-backtest.txt
  ```

  **Commit**: YES (group with T35, T37-T38 as Wave 5)
  - Message: `feat(ads): optimization core algorithm + simulation engine + dashboard`
  - Files: `src/agents/ad_monitor_agent/simulation/`
  - Pre-commit: `pytest tests/test_ad_simulation.py`

- [ ] 37. Ad Dashboard + Management Frontend Pages

  **What to do**:
  - Create `src/frontend/src/pages/AdDashboard.tsx`:
    - Route: `/ads`
    - KPI cards: Total Ad Spend, ACOS, ROAS, TACoS, Total Sales
    - Campaign performance chart (Recharts, 30-day trend)
    - Top campaigns table (sortable by spend, ACOS, conversions)
    - Budget utilization gauge
    - Safety rails activity log (recent blocks, warnings)
    - Simulation results summary (if any)
  - Create `src/frontend/src/pages/AdManagement.tsx`:
    - Route: `/ads/manage`
    - Campaign list with current bids, status, metrics
    - Algorithm recommendation panel: shows pending bid adjustments
    - Approve/reject individual recommendations
    - Simulation launcher: run backtest/what-if from UI
    - Historical optimization log (what was changed and why)
  - Wire to backend endpoints for ad data and simulation

  **Must NOT do**:
  - Do NOT show live bid adjustment buttons without HITL confirmation
  - Do NOT auto-apply any recommendations from dashboard

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Data-heavy dashboard, Recharts, interactive tables, complex layouts
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T38, after T36)
  - **Parallel Group**: Wave 5
  - **Blocks**: None
  - **Blocked By**: T16 (Dashboard pattern), T36 (simulation engine for data)

  **References**:

  **Pattern References**:
  - `temp_frontend_ref/src/components/AdDashboard.tsx:1-313` — Gemini ad dashboard (charts, tables, KPIs) — primary visual reference
  - `temp_frontend_ref/src/components/AdManagement.tsx` — Ad management UI reference
  - `src/frontend/src/pages/Dashboard.tsx` — T16 pattern for dashboard pages

  **WHY Each Reference Matters**:
  - Gemini AdDashboard — Direct visual reference for ad metrics layout, chart config, table structure

  **Acceptance Criteria**:
  - [ ] Ad Dashboard at `/ads` with KPI cards and charts
  - [ ] Ad Management at `/ads/manage` with campaign list and recommendations
  - [ ] Simulation launcher works from UI
  - [ ] HITL: recommendations require approve before execution
  - [ ] `npm run build` passes

  **QA Scenarios**:

  ```
  Scenario: Ad Dashboard renders with metrics
    Tool: Playwright
    Preconditions: Ad data in DB, logged in as boss
    Steps:
      1. Navigate to /ads
      2. Verify KPI cards visible (ACOS, ROAS, Spend)
      3. Verify chart renders
      4. Verify campaign table has rows
    Expected Result: Dashboard sections all render with data or empty state
    Failure Indicators: Blank page, JS errors, missing sections
    Evidence: .sisyphus/evidence/task-37-ad-dashboard.png

  Scenario: Bid recommendation approval
    Tool: Playwright
    Preconditions: Pending bid recommendations exist
    Steps:
      1. Navigate to /ads/manage
      2. Find pending recommendation
      3. Click approve
      4. Verify recommendation marked as approved
    Expected Result: Recommendation approved, status updated
    Evidence: .sisyphus/evidence/task-37-bid-approve.png
  ```

  **Commit**: YES (group with T35-T36, T38 as Wave 5)
  - Message: `feat(ads): optimization core algorithm + simulation engine + dashboard`
  - Files: `src/frontend/src/pages/AdDashboard.tsx`, `src/frontend/src/pages/AdManagement.tsx`
  - Pre-commit: `npm run build`

- [ ] 38. Ad Optimization Agent → Chat Mode

  **What to do**:
  - Create `src/agents/ad_monitor_agent/chat_agent.py` extending `ChatBaseAgent`:
    - `get_system_prompt()` — Ad optimization context, safety rails awareness
    - `get_model()` — GPT-4o (optimization math)
    - `get_tools()` — tools for: run simulation, query campaign data, view optimization history, generate recommendations
  - Chat flow:
    - User asks about campaign performance → agent provides analysis
    - User requests optimization → agent runs algorithm → presents recommendations
    - Recommendations go through HITL approval (via ApprovalService)
    - After approval, agent queues bid adjustments via Ads API (NOT direct execution)
  - Integration with simulation engine: user can ask "what if I increase budget by 20%?" → runs simulation

  **Must NOT do**:
  - Do NOT execute Ads API writes directly from chat — always through approval queue
  - Do NOT skip safety rails in any recommendation

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex agent integrating algorithm, simulation, Ads API, HITL workflow
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T37)
  - **Parallel Group**: Wave 5
  - **Blocks**: None
  - **Blocked By**: T36 (simulation engine), T14 (chat component)

  **References**:
  - `src/agents/core_agent/chat_agent.py` — T17 chat pattern
  - `src/agents/ad_monitor_agent/algorithm/` — T35 algorithm
  - `src/agents/ad_monitor_agent/simulation/` — T36 simulation
  - `src/amazon_ads_api/` — Ads API for data retrieval (NOT writes from chat)

  **Acceptance Criteria**:
  - [ ] Chat agent provides campaign analysis
  - [ ] Can run simulation from chat ("what if" queries)
  - [ ] Recommendations go through HITL approval
  - [ ] No direct Ads API writes from chat

  **QA Scenarios**:
  ```
  Scenario: Ad optimization chat
    Tool: Playwright
    Preconditions: Full stack, ad data in DB
    Steps:
      1. Navigate to /agents/ad_monitor
      2. Chat: "How are my SP campaigns performing this week?"
      3. Follow up: "Run a simulation with 20% more budget"
    Expected Result: Performance analysis, then simulation results
    Evidence: .sisyphus/evidence/task-38-ad-chat.png
  ```

  **Commit**: YES (group with T35-T37 as Wave 5)
  - Message: `feat(ads): optimization core algorithm + simulation engine + dashboard`
  - Files: `src/agents/ad_monitor_agent/chat_agent.py`
  - Pre-commit: `pytest`

### Wave 6 — Import + Polish + Integration (After Wave 5)

- [ ] 39. 1,118 Doc Import Pipeline (Clean + Embed + Store)

  **What to do**:
  - Create `src/knowledge_base/import_pipeline.py`:
    - `DocCleaner` class:
      - Read .docx files using python-docx
      - Clean steps:
        1. Remove personal reflections/life musings (LLM-assisted detection)
        2. Remove QR code references and promotional content
        3. Remove author signatures and WeChat/公众号 references
        4. Extract only e-commerce/Amazon relevant content
        5. Preserve document structure (headings, lists, tables)
      - Output: cleaned text per document
    - `BulkImporter` class:
      - Process .docx files from a directory
      - Clean each file via DocCleaner
      - Generate embeddings via existing RAG engine
      - Store in knowledge base with source metadata
      - Skip files that are entirely non-relevant (life content, pure images)
      - Progress tracking: log processed/skipped/failed counts
  - Processing strategy:
    - Run on local Windows machine (where files are at `F:\跨境电商长期主义\`)
    - Output cleaned text files to `cleaned_docs/` directory
    - Transfer cleaned text to server via scp
    - Import into KB on server
  - HITL: sample review — boss reviews 20 random cleaned docs before full import
  - Handle the 7,616 .jpg and 12 .mp4: skip for now (text-only import)

  **Must NOT do**:
  - Do NOT import images or videos — text only
  - Do NOT skip cleaning step — every doc must be cleaned
  - Do NOT import without boss sampling review
  - Do NOT process on server — files are on Windows local machine

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Batch processing, LLM-assisted cleaning, document parsing, quality pipeline
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T40-T44)
  - **Parallel Group**: Wave 6
  - **Blocks**: T40 (KB self-iteration needs imported data)
  - **Blocked By**: T21 (audit should complete first)

  **References**:

  **Pattern References**:
  - `src/knowledge_base/` — Existing RAG engine for embedding and storage
  - PUDIWIND_V2_complete_report.docx — Successfully read via python-docx (proves docx reading works)

  **WHY Each Reference Matters**:
  - RAG engine — Final storage destination. Cleaned text goes through existing embedding pipeline.

  **Acceptance Criteria**:
  - [ ] `src/knowledge_base/import_pipeline.py` exists with DocCleaner and BulkImporter
  - [ ] DocCleaner removes personal content, QR codes, promotions
  - [ ] BulkImporter processes entire directory with progress tracking
  - [ ] Boss reviews sample of 20 cleaned docs before full import
  - [ ] All 1,118 docs processed (some may be skipped if non-relevant)
  - [ ] Images and videos skipped

  **QA Scenarios**:

  ```
  Scenario: Doc cleaning removes personal content
    Tool: Bash (local python)
    Preconditions: Sample .docx files available
    Steps:
      1. Run DocCleaner on 5 sample docs known to have personal content
      2. Check cleaned output for QR codes, 公众号, personal reflections
    Expected Result: Cleaned text has no personal/promotional content
    Failure Indicators: QR codes or 公众号 references in output
    Evidence: .sisyphus/evidence/task-39-doc-cleaning.txt

  Scenario: Bulk import with progress tracking
    Tool: Bash
    Preconditions: Cleaned docs available
    Steps:
      1. Run BulkImporter on a batch of 50 docs
      2. Check progress output (processed/skipped/failed counts)
      3. Query KB for imported docs count
    Expected Result: 50 docs processed, count matches in KB
    Evidence: .sisyphus/evidence/task-39-bulk-import.txt
  ```

  **Commit**: YES (group with T40-T44 as Wave 6)
  - Message: `feat(polish): doc import + KB self-iteration + Google Trends + cost monitor + deployment`
  - Files: `src/knowledge_base/import_pipeline.py`
  - Pre-commit: `pytest`

- [ ] 40. AI KB Self-Iteration Pipeline (with Boss Review)

  **What to do**:
  - Create `src/knowledge_base/self_iteration.py`:
    - `KBIterator` class:
      - After each agent run, agent can propose KB entries:
        - Insights discovered during analysis
        - Market trends observed
        - Successful strategies identified
        - Error patterns to avoid
      - Proposed entries go to `kb_review_queue` (NOT directly to KB)
      - Each entry includes: source agent, content, summary, reasoning for why this should be in KB
  - Integration with `ChatBaseAgent`:
    - After each chat session, agent self-evaluates: "Did I learn something worth remembering?"
    - If yes, creates KB proposal via `KBIterator`
  - Boss reviews via KB Review UI (T20):
    - See AI-generated summary
    - See full proposed content
    - Approve → writes to KB
    - Reject → discarded with comment
  - This closes the learning loop: agents learn from operations, boss curates the knowledge

  **Must NOT do**:
  - Do NOT write to KB without boss approval — MANDATORY review step
  - Do NOT build this before KB Review UI (T20) is complete
  - Do NOT flood review queue — limit to 1 proposal per agent run maximum

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Learning loop design, integration with multiple systems (agents, KB, review UI)
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T39, T41-T44)
  - **Parallel Group**: Wave 6
  - **Blocks**: None
  - **Blocked By**: T20 (KB review UI must be complete), T39 (import should complete first)

  **References**:
  - `src/knowledge_base/` — RAG engine for storage
  - `src/db/models.py:KBReviewQueue` — Review queue model
  - `src/agents/chat_base_agent.py` — ChatBaseAgent to integrate self-evaluation hook

  **Acceptance Criteria**:
  - [ ] `src/knowledge_base/self_iteration.py` exists
  - [ ] Agents can propose KB entries after chat sessions
  - [ ] Proposals appear in KB review queue
  - [ ] Boss can approve/reject via web UI
  - [ ] Approved entries written to KB
  - [ ] Rate limited to 1 proposal per agent run

  **QA Scenarios**:
  ```
  Scenario: Agent proposes KB entry
    Tool: Bash (curl)
    Steps:
      1. Chat with an agent about market trends
      2. Check kb_review_queue for new pending entry
      3. Verify entry has source_agent, content, summary
    Expected Result: Pending KB entry created from agent insight
    Evidence: .sisyphus/evidence/task-40-kb-iteration.txt
  ```

  **Commit**: YES (group with Wave 6)
  - Files: `src/knowledge_base/self_iteration.py`
  - Pre-commit: `pytest`

- [ ] 41. Google Trends API Integration (Optional Module)

  **What to do**:
  - Create `src/google_trends/` directory:
    - `client.py` — Google Trends API client:
      - Use official Google Trends API (if available) or SerpApi as fallback
      - Methods:
        - `get_interest_over_time(keywords, geo, timeframe) → TrendData`
        - `get_related_queries(keyword, geo) → list[RelatedQuery]`
        - `get_regional_interest(keyword) → dict[region, interest]`
      - Rate limiting: respect API quotas
      - Caching: cache results for 24h (trends don't change minute-by-minute)
    - `models.py` — TrendData, RelatedQuery data classes
  - Integration points:
    - Brand Planning agent: market trend analysis
    - Selection agent: category trend validation
    - Keyword Library agent: trend scoring for keywords
  - Design as OPTIONAL — all agents must work without Google Trends (graceful degradation)
  - Add `GOOGLE_TRENDS_ENABLED=true/false` to Settings

  **Must NOT do**:
  - Do NOT make Google Trends a hard dependency — everything works without it
  - Do NOT use web scraping — API only
  - Do NOT call Google Trends on every agent run — cache + scheduled refresh only

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: External API integration, caching, graceful degradation design
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T39-T40, T42-T44)
  - **Parallel Group**: Wave 6
  - **Blocks**: None
  - **Blocked By**: T1 (config table)

  **References**:
  - `src/config.py` — Settings pattern for API key and enable/disable flag
  - `src/seller_sprite/client.py` — External API client pattern (rate limiting, error handling)

  **Acceptance Criteria**:
  - [ ] `src/google_trends/` exists with client and models
  - [ ] API calls work when enabled
  - [ ] Graceful degradation when disabled (agents work without it)
  - [ ] Results cached for 24h
  - [ ] Configurable via Settings

  **QA Scenarios**:
  ```
  Scenario: Google Trends disabled gracefully
    Tool: Bash (docker exec)
    Steps:
      1. Set GOOGLE_TRENDS_ENABLED=false
      2. Call brand planning agent
      3. Verify agent works without trends data
    Expected Result: Agent completes without error, notes trends unavailable
    Evidence: .sisyphus/evidence/task-41-trends-disabled.txt
  ```

  **Commit**: YES (group with Wave 6)
  - Files: `src/google_trends/`
  - Pre-commit: `pytest`

- [ ] 42. API Cost Monitoring Dashboard

  **What to do**:
  - Create backend endpoint `GET /api/monitoring/costs`:
    - Per-agent LLM cost breakdown (daily, weekly, monthly)
    - Per-model cost breakdown
    - Total API costs (LLM + Seller Sprite + SP-API + Ads API + Google Trends)
    - Cost trend chart data
    - Alert thresholds: approaching daily limit, unusual spike
  - Create `src/frontend/src/pages/CostMonitor.tsx` (or section in System Management):
    - Route: `/system/costs` (boss-only)
    - Cost breakdown charts (by agent, by model, by API)
    - Daily/weekly/monthly views
    - Alert configuration
    - Budget limit display ($50/day current limit)
  - Read cost data from existing `llm_cache` table + new tracking

  **Must NOT do**:
  - Do NOT expose cost data to operators — boss-only
  - Do NOT create separate cost tracking — leverage existing `_track_usage` in LLM client

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Dashboard with charts, data aggregation endpoints
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T39-T41, T43-T44)
  - **Parallel Group**: Wave 6
  - **Blocked By**: T13 (layout)

  **References**:
  - `src/llm/client.py:_track_usage` — Existing cost tracking
  - `src/db/models.py:LLMCache` — Cached LLM calls with cost data

  **Acceptance Criteria**:
  - [ ] Cost monitoring endpoint returns per-agent, per-model breakdown
  - [ ] Frontend page shows charts and tables
  - [ ] Boss-only access
  - [ ] Daily limit displayed

  **QA Scenarios**:
  ```
  Scenario: Cost dashboard shows data
    Tool: Playwright
    Preconditions: Some LLM calls have been made
    Steps:
      1. Login as boss, navigate to /system/costs
      2. Verify cost breakdown visible
      3. Login as operator, try to access /system/costs
    Expected Result: Boss sees data, operator gets redirected/blocked
    Evidence: .sisyphus/evidence/task-42-cost-monitor.png
  ```

  **Commit**: YES (group with Wave 6)
  - Files: `src/api/monitoring.py`, `src/frontend/src/pages/CostMonitor.tsx`

- [ ] 43. Message Center + System Management Pages

  **What to do**:
  - Create `src/frontend/src/pages/MessageCenter.tsx`:
    - Route: `/messages`
    - Notification history (all Feishu-equivalent notifications shown in web)
    - Filter by: type (alert, report, approval), date, read/unread
    - Mark as read, bulk actions
  - Create `src/frontend/src/pages/SystemManagement.tsx`:
    - Route: `/system` (boss-only)
    - Sections:
      - User management: list users, change roles (boss/operator)
      - Agent configuration: model assignments (from T34), enable/disable agents
      - Scheduler management: view/edit cron schedules
      - System config: key-value settings from system_config table
      - API keys status: which APIs are configured (not showing actual keys)
  - Backend endpoints as needed for system management CRUD

  **Must NOT do**:
  - Do NOT expose API key values — show only configured/not-configured status
  - Do NOT allow operator access to system management

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Admin UI pages with forms, tables, CRUD operations
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T39-T42, T44)
  - **Parallel Group**: Wave 6
  - **Blocked By**: T13 (layout)

  **References**:
  - `temp_frontend_ref/src/components/MessageCenter.tsx` — Gemini reference
  - `temp_frontend_ref/src/components/SystemManagement.tsx` — Gemini reference
  - `src/db/models.py:SystemConfig` — Existing config table

  **Acceptance Criteria**:
  - [ ] Message Center renders with notification list
  - [ ] System Management renders with all sections (boss-only)
  - [ ] User management: can change roles
  - [ ] Agent config: can change model assignments
  - [ ] Operator blocked from system management

  **QA Scenarios**:
  ```
  Scenario: System management sections
    Tool: Playwright
    Preconditions: Logged in as boss
    Steps:
      1. Navigate to /system
      2. Verify all sections visible: Users, Agents, Scheduler, Config, API Status
      3. Try changing model assignment for one agent
    Expected Result: All sections render, config change saves
    Evidence: .sisyphus/evidence/task-43-system-mgmt.png
  ```

  **Commit**: YES (group with Wave 6)
  - Files: `src/frontend/src/pages/MessageCenter.tsx`, `src/frontend/src/pages/SystemManagement.tsx`

- [ ] 44. Docker Build + Nginx + Deployment Config Update

  **What to do**:
  - Update `deploy/docker/Dockerfile`:
    - Multi-stage build: Node.js stage for frontend build + Python stage for backend
    - Frontend: `npm run build` in Node stage, copy `dist/` to Nginx serve directory
    - Backend: existing Python setup with new dependencies (langgraph-checkpoint-postgres, etc.)
  - Update `deploy/docker/docker-compose.yml`:
    - Ensure proper volume mounts for new directories
    - Environment variables for new features (GOOGLE_TRENDS_ENABLED, etc.)
    - Health check configuration
  - Update `deploy/nginx/nginx.conf`:
    - Serve frontend `dist/` at `/`
    - Proxy `/api/` to backend (existing)
    - SSE config for `/api/chat/` (from T6, verify in production)
    - SSL configuration (existing)
    - SPA fallback: all non-API routes serve index.html (React Router)
  - Update Alembic to run on container startup
  - Test full deployment cycle: build → deploy → migrate → verify

  **Must NOT do**:
  - Do NOT break existing deployment — incremental changes only
  - Do NOT remove existing environment variables
  - Do NOT skip SSL configuration

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Docker, Nginx, deployment pipeline, multi-stage build
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (integrates everything)
  - **Parallel Group**: Wave 6 (last task, after all others)
  - **Blocks**: F1-F4 (final verification)
  - **Blocked By**: All T1-T43

  **References**:
  - `deploy/docker/Dockerfile` — Existing Dockerfile
  - `deploy/docker/docker-compose.yml` — Existing compose
  - `deploy/nginx/nginx.conf` — Existing Nginx config

  **Acceptance Criteria**:
  - [ ] `docker compose build` succeeds
  - [ ] `docker compose up` starts all services
  - [ ] Frontend served at `/`
  - [ ] API accessible at `/api/`
  - [ ] SSE works through Nginx (no buffering)
  - [ ] Alembic migrations run on startup
  - [ ] SSL works
  - [ ] Health check passes

  **QA Scenarios**:

  ```
  Scenario: Full deployment cycle
    Tool: Bash (SSH to server)
    Preconditions: Code uploaded to server
    Steps:
      1. sudo docker compose -f /opt/amazon-ai/deploy/docker/docker-compose.yml down
      2. sudo docker compose -f /opt/amazon-ai/deploy/docker/docker-compose.yml build
      3. sudo docker compose -f /opt/amazon-ai/deploy/docker/docker-compose.yml up -d
      4. Wait 30s for startup
      5. curl http://localhost:8000/health
      6. curl -k https://52.221.207.30/
      7. curl -k https://52.221.207.30/api/auth/login (verify API proxy)
    Expected Result: All services running, health OK, frontend served, API accessible
    Failure Indicators: Build failure, container crash, 502 errors
    Evidence: .sisyphus/evidence/task-44-deployment.txt

  Scenario: SSE works through Nginx
    Tool: Bash
    Preconditions: Deployed
    Steps:
      1. Login, get token
      2. curl -N -k -H "Authorization: Bearer $TOKEN" https://52.221.207.30/api/chat/core_management/stream -d '{"message":"test"}' --max-time 15
    Expected Result: SSE events stream through Nginx without buffering
    Failure Indicators: All data arrives at once (buffered), timeout, 502
    Evidence: .sisyphus/evidence/task-44-sse-nginx.txt
  ```

  **Commit**: YES (final commit for Wave 6)
  - Message: `feat(polish): doc import + KB self-iteration + Google Trends + cost monitor + deployment`
  - Files: `deploy/`
  - Pre-commit: `docker compose build`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `tsc --noEmit` (frontend) + linter + `pytest --mock-external-apis`. Review all changed files for: `as any`/`@ts-ignore`, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names (data/result/item/temp). Verify Alembic migrations are reversible.
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` skill for UI)
  Start from clean state (docker compose down/up). Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (chat → approve → DB write → notification). Test RBAC (operator cannot see auditor, boss can). Test SSE streaming end-to-end. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance (especially: BaseAgent untouched, no Ads API writes in simulation, no direct DB writes without HITL). Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

| Wave | Commit Message | Key Files | Pre-commit Check |
|------|---------------|-----------|-----------------|
| 1a | `feat(db): add Alembic + RBAC enforcement + chat schema` | alembic/*, src/api/agents.py, src/api/dependencies.py, src/db/models.py | `alembic upgrade head` + `pytest` |
| 1b | `feat(streaming): add ChatBaseAgent + SSE + LLM streaming` | src/agents/chat_base_agent.py, src/llm/client.py, src/api/sse.py, deploy/nginx/ | `pytest` + `curl SSE endpoint` |
| 1c | `feat(chat): add chat service + HITL approval workflow` | src/services/chat.py, src/api/chat.py, src/services/approval.py | `pytest` + `curl chat endpoints` |
| 2 | `feat(frontend): React 19 + Vite scaffolding with auth + layout` | src/frontend/* | `npm run build` + Playwright smoke |
| 3 | `feat(agents): first 3 agents chat mode + KB review + HITL UI` | src/agents/*/chat_*.py, src/frontend/src/pages/* | `pytest` + Playwright |
| 4 | `feat(agents): remaining agents + keyword builder + auditor` | src/agents/keyword_library/*, src/agents/auditor/* | `pytest` + `curl` |
| 5 | `feat(ads): optimization core + simulation engine + dashboard` | src/agents/ad_monitor_agent/*, src/frontend/src/pages/Ad* | `pytest` + Playwright |
| 6 | `feat(polish): doc import + Google Trends + cost monitor + deploy` | src/knowledge_base/*, src/google_trends/*, deploy/* | Full test suite + docker build |

---

## Success Criteria

### Verification Commands
```bash
# Build
sudo docker compose -f /opt/amazon-ai/deploy/docker/docker-compose.yml build  # Expected: SUCCESS

# Migrations
sudo docker exec amazon-ai-app alembic upgrade head  # Expected: OK, no errors

# Tests
sudo docker exec amazon-ai-app pytest --mock-external-apis  # Expected: all pass

# Health
curl http://localhost:8000/health  # Expected: {"status": "ok"}

# Auth + RBAC
curl -X POST http://localhost:8000/api/auth/login -d '{"username":"boss","password":"test123"}'  # Expected: JWT token
curl -H "Authorization: Bearer $BOSS_TOKEN" -X POST http://localhost:8000/api/agents/auditor/run -H "Content-Type: application/json" -d '{"params":{}}'  # Expected: 200
curl -H "Authorization: Bearer $OP_TOKEN" -X POST http://localhost:8000/api/agents/auditor/run -H "Content-Type: application/json" -d '{"params":{}}'  # Expected: 403

# SSE Streaming
curl -N -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/chat/core_management/stream  # Expected: SSE events

# Frontend
curl -k https://52.221.207.30/  # Expected: React app HTML
```

### Final Checklist
- [ ] All "Must Have" items present and verified
- [ ] All "Must NOT Have" items absent (grep verification)
- [ ] All 44 tasks completed with evidence
- [ ] Docker build clean, Alembic migrations clean
- [ ] All 13 agents accessible via chat UI
- [ ] RBAC enforced (Auditor boss-only verified)
- [ ] Human-in-the-loop flow works end-to-end
- [ ] Ad simulation runs without live API calls
- [ ] KB review queue functional for Boss
- [ ] Existing Phase 3b functionality preserved (all 11 original agents still work via REST)
