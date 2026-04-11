# Decisions — production-fixes-32issues

## [2026-04-11] F4 audit scope rules
- 仅按 `src/`、`data/`、`deploy/`、`.sisyphus/` 的真实实现文件判定，不把 `node_modules` / 构建产物纳入合规判断。
- 路由接线优先于页面文件存在；若页面存在但未注册到 `App.tsx`，视为“未交付可用功能”。
- 本次 F4 结论按“计划 spec + 实际接线 + 禁止项”三者同时满足才算合规。
- 本次路由修复采用最小改动：只更新 `App.tsx` 的 imports/route element，并删除独立 `MessageCenter.tsx`，不触碰页面实现文件。

## [2026-04-10] Session ses_2b24b10b0ffezwvEa0VL8uq8Tu — Plan Start

### Architecture Decisions (User-Confirmed)
- **Data Layer**: Mock data first, SP-API pipeline in later phase
- **LLM**: OpenRouter + direct-connect dual mode; OpenRouter key not yet configured → feature flag
- **Users Table**: DB-backed (migrate from env vars USERS dict)
- **Theme**: dark by default, manual toggle (NOT system-follow), localStorage persistence
- **Timezone**: US site = America/Los_Angeles (PST/PDT); no multi-site for now
- **Notifications**: polling every 30s (NOT WebSocket)
- **Message Center**: NO standalone page — bell placeholder only
- **Returns**: FBA only (no FBM, no Voice of Customer)
- **SSL**: Deploy LAST — after all features complete
- **User Deletion**: set is_active=False (soft delete); JWT remains valid until expiry (acceptable simplification)
- **Agent Names**: stored in DB, editable via management UI
- **Approval History**: replaces old Agent Activity block on Dashboard

### Frontend Decisions
- **Shared DataTable**: built in Wave 1 (Task 9), used by 6+ pages
- **Chart library**: use already-installed package if exists; otherwise recharts
- **Route guards**: PrivateRoute (auth) + BossRoute (boss-only)
- **Ad Management page**: ~60% of frontend effort; split into 5 parallel tasks (27-31)
