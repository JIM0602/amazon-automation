# Learnings — amazon-ai-system

## [2026-03-31] 项目初始化

### 环境约定
- 本地开发环境：Windows 11 / PowerShell
- 目标部署环境：Ubuntu 22.04 LTS（云服务器）
- Python版本：3.11+
- 数据库：PostgreSQL 16 + pgvector
- 框架：LangGraph + FastAPI + APScheduler

### 关键架构决策
- LLM：OpenAI GPT-4o/GPT-4o-mini + Anthropic Claude，通过LiteLLM统一调用
- Embedding：OpenAI text-embedding-3-small
- 飞书SDK：lark-oapi（官方Python SDK）
- 调度器：APScheduler（支持Cron+持久化）
- ORM：SQLAlchemy + Alembic（迁移管理）
- 日志：loguru

### Task 1 特殊情况
- T1（云服务器搭建）是外部操作，需要JIM亲自购买服务器
- 我们先产出：docs/server-setup.md（详细步骤指南）和 scripts/setup-server.sh（自动化脚本）
- T1不阻塞本地代码开发（T2-T6可以在本地完成）

### Task 1 交付补充
- 已补齐云服务器搭建指南的中文大白话说明，重点强调了安全组、SSH 密钥、UFW、HTTPS 和数据库不暴露公网。
- 初始化脚本以 Ubuntu 22.04 为主，兼容 Debian 系列，默认创建非 root 用户 appuser，并把项目目录固定到 /opt/amazon-ai/。
- 证据文件先记录“待 JIM 配置真实服务器后验证”的命令和预期结果，避免把未完成的线上操作写成已完成。

### 数据库Schema关键字段
- audit_logs表字段：id, action, actor, pre_state, post_state, created_at（注意：不是agent_type）
- PostgreSQL端口5432：仅通过Docker内部网络，不暴露到宿主机

### 文件路径注册表（canonical paths）
- src/knowledge_base/rag_engine.py
- src/knowledge_base/document_processor.py
- src/feishu/bot_handler.py
- src/feishu/command_router.py
- src/feishu/approval.py
- src/feishu/bitable_sync.py
- src/agents/core_agent/daily_report.py
- src/agents/core_agent/approval_manager.py
- src/agents/selection_agent/（目录）
- src/seller_sprite/client.py
- src/amazon_api/mock.py
- src/llm/client.py
- src/llm/cost_monitor.py
- src/utils/audit.py
- src/utils/killswitch.py
- src/api/system.py
- src/scheduler/__init__.py
- src/scheduler/jobs.py
- src/scheduler/config.py
- src/config.py
- src/db/models.py
- src/db/connection.py
- src/db/__init__.py

### Task 3 交付记录
- 已创建 Python 项目骨架目录：src/、tests/、data/ 及各子包占位文件。
- 已统一补齐配置入口 src/config.py，使用 pydantic-settings 读取 .env。
- 已补充 pytest 配置、Makefile 快捷命令、固定版本 requirements.txt 和 pyproject.toml。
- 已新增 .env.example、.gitignore、golden_qa 占位数据与任务证据文件。
