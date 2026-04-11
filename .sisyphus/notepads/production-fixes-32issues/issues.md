# Issues — production-fixes-32issues

## [2026-04-10] Session ses_2b24b10b0ffezwvEa0VL8uq8Tu — Plan Start

### Known Gotchas
- **datetime bug**: All agents use naive datetime — triggers "can't compare offset-naive and offset-aware" error in ChatBaseAgent's KB self-iteration hook
- **Anthropic hardcode**: `src/llm/client.py` lines 524-548 directly instantiate `anthropic.AsyncAnthropic` — fails when no Anthropic key
- **keyword_library agent**: completely silent — no response at all; root cause unknown; must diagnose
- **Conversation history**: frontend never calls history API on page load; chat messages may or may not be saved to DB (both layers need checking)
- **Nginx SSL**: template at `deploy/nginx/nginx-ssl.conf` has certbot config but is commented out; HTTP-only currently
- **LLM client is module-level functions**: when importing, use `from src.llm.client import chat, chat_stream` etc. — NOT `from src.llm.client import LLMClient`
- **No Playwright**: Cannot use browser-based testing — must use curl + Python scripts for verification
# [2026-04-11] F4 scope audit issues
- 全局文本搜索工具在当前环境会被 `node_modules` 污染，审计禁用模式时需要额外排除依赖目录，否则结果不可直接作为结论证据。
- `src/frontend/src/pages/MessageCenter.tsx` 作为独立页面文件仍然存在，属于计划明确禁止的遗留实现。
- `src/frontend/src/pages/ApiKeysPage.tsx` 的实际路径在 `src/frontend/src/pages/`，而不是计划中提到的 `src/frontend/src/pages/system/`，审计时必须按真实路径验证。
- 当前环境缺少 `typescript-language-server`，所以 `lsp_diagnostics` 无法执行；前端只能先靠构建验证。
