# 亚马逊AI智能化运营系统（PUDIWIND）

## TL;DR

> **快速摘要**：为亚马逊宠物用品卖家PUDIWIND搭建AI智能化运营系统，采用Python + LangGraph + PostgreSQL/pgvector架构，通过飞书机器人交互，分阶段交付11个AI Agent。
> 
> **交付物**：
> - Phase 1（第1个月）：知识库RAG系统 + 核心管理Agent（飞书机器人）+ 选品分析Agent + 基础设施
> - Phase 2（第2-3个月）：竞品调研Agent + 用户画像Agent + Listing文案Agent + 广告监控Agent + 亚马逊SP-API正式接入
> - Phase 3（第4-6个月）：产品上架Agent + 库存发货Agent + Listing图片Agent + Web控制台 + 品牌规划Agent
> 
> **预估工时**：Phase 1 约 4 周
> **并行执行**：YES - 6 个执行波次
> **关键路径**：基础设施搭建 → 知识库搭建 → 核心管理Agent → 选品Agent

---

## Context

### 原始需求
JIM是一位亚马逊宠物用品卖家（品牌PUDIWIND，美国站），代码基础为0但学习力强，希望搭建一套AI智能化运营系统。当前有550篇运营方法论文档和2000+篇朋友的思考文档作为知识库。系统需要11个AI Agent覆盖选品、竞品分析、Listing制作、广告优化、库存管理等全流程，通过飞书进行交互。

### 访谈摘要
**关键决策**：
- 1个月内上线核心功能闭环（知识库问答 + 每日汇报 + 选品分析）
- 全自动执行 + 人工审批模式
- 主流商业AI模型（GPT/Claude）
- 飞书作为主要交互入口
- 所有团队成员权限相同
- AI全程辅助开发

**工具现状**：
- 飞书：在用但无多维表格
- 卖家精灵MCP：有账号未使用
- 亚马逊SP-API：沙箱未就绪
- 知识库文档：550篇无分类 + 2000+篇朋友文档
- 产品数据：还未开始记录

### Metis审查
**识别的关键风险**（已纳入计划）：
- SP-API审批需2-4周 → Phase 1使用Mock数据，不依赖SP-API
- 代码零基础维护困难 → 所有配置环境变量化，错误产生中文飞书告警
- LLM API费用失控 → 设置每日硬上限+飞书告警
- 亚马逊PII数据合规 → 实现PII过滤中间件
- 1个月时间极紧 → Phase 1严格限定3个交付物
- 知识库质量是基础 → 文档处理作为第一优先级

---

## Work Objectives

### 核心目标
搭建一个可7x24小时运行的AI智能化运营系统，通过飞书机器人与团队交互，提升PUDIWIND的运营效率和决策准确度。

### 具体交付物（Phase 1）
1. **知识库RAG系统**：550篇+2000篇文档向量化入库，支持AI智能检索
2. **核心管理Agent**：飞书机器人，支持日报推送、知识问答、任务触发
3. **选品分析Agent**：定期+手动触发市场分析，输出选品建议到飞书多维表格
4. **基础设施**：云服务器 + 数据库 + 定时任务 + 日志审计

### 完成标准
- [ ] 知识库RAG系统：RAGAS评测 faithfulness ≥ 0.85
- [ ] 飞书机器人：在飞书群发送消息，5秒内获得知识库回答
- [ ] 每日自动汇报：每天09:00自动发送数据日报到飞书
- [ ] 选品Agent：运行一次完整分析，输出≥3个候选产品到飞书多维表格
- [ ] 所有Agent支持dry-run模式
- [ ] 紧急停机：一键暂停所有Agent

### Must Have（必须包含）
- 知识库文档向量化和智能检索
- 飞书机器人问答和日报推送
- 选品分析（基于卖家精灵MCP）
- 人工审批流程（飞书审批卡片）
- 所有操作的日志记录（可审计、可追溯）
- dry-run模式（模拟运行不执行）
- 紧急停机按钮
- LLM费用监控和上限

### Must NOT Have（护栏 - 禁止包含）
- ❌ Phase 1不做Web控制台（用飞书多维表格替代）
- ❌ Phase 1不做亚马逊SP-API写入操作（上架、改价、调广告等）
- ❌ Phase 1不做AI图片生成
- ❌ 不将亚马逊客户PII数据发送给第三方LLM
- ❌ 不允许Agent自行修改Prompt（"自主学习"仅指数据积累）
- ❌ 不在代码中硬编码任何API密钥
- ❌ 不制作PDF报告（Phase 1用飞书文档替代）

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — 所有验证由Agent自动执行。无例外。

### 测试决策
- **测试基础设施**：需新建（项目从零开始）
- **自动测试**：YES (Tests-after) — 每个功能模块配套测试
- **测试框架**：pytest
- **如果TDD**：不采用严格TDD，采用功能开发后补测试

### QA策略
每个任务MUST包含Agent可执行的QA场景。
证据保存到 `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`。

- **后端API**：使用 Bash (curl/httpie) — 发送请求，断言状态码和响应字段
- **飞书机器人**：使用 Bash (Python脚本) — 发送测试消息，验证回调
- **知识库**：使用 Bash (Python脚本) — 查询知识库，比对预期回答
- **数据库**：使用 Bash (psql/Python) — 查询数据库，验证数据完整性

### QA执行环境（重要）

> **本地开发环境为 Windows (PowerShell)，但部署目标为 Ubuntu Linux 服务器。**
> 所有QA场景中的Shell命令（`ls`, `grep`, `find`, `wc`, `bash`, `nmap` 等）
> 均假定在 **部署目标Linux服务器上** 或 **Docker容器内** 执行。

**执行规则**：
1. **基础设施任务**（Task 1, 18）：通过SSH在远程Linux服务器上执行QA命令
2. **容器化服务**（Task 2, 4-17, 20）：通过 `docker exec -it <container> bash -c "..."` 在容器内执行
3. **代码质量检查**（F1-F4）：在已部署的Linux服务器上或通过 `docker exec` 执行 `grep`, `find` 等命令
4. **pytest测试**：在app容器内执行 `docker exec -it app pytest tests/`
5. **curl端点测试**：可在任何环境执行（Windows PowerShell的curl别名 `Invoke-WebRequest` 或容器内curl均可）

**禁止**：不要假定QA命令在Windows本地环境运行。所有 POSIX 命令必须通过SSH或docker exec在Linux环境中执行。

---

## Execution Strategy

### 并行执行波次

> 最大化吞吐量，独立任务分组并行执行。
> 每波完成后才开始下一波。

```
Wave 1 (立即开始 — 基础设施 + 文档处理):
├── Task 1: 云服务器和基础环境搭建 [quick]
├── Task 2: 数据库设计和搭建（PostgreSQL + pgvector）[unspecified-high]
├── Task 3: Python项目骨架和配置体系 [quick]
├── Task 4: 知识库文档预处理（清洗、分类、分块）[unspecified-high]
├── Task 5: 飞书机器人创建和基础接入 [unspecified-high]
└── Task 6: 亚马逊SP-API开发者账号申请（外部依赖）[quick]

Wave 2 (Wave 1完成后 — 核心能力构建):
├── Task 7: 知识库RAG系统搭建（向量化 + 检索）(depends: 2, 3, 4) [deep]
├── Task 9: 卖家精灵MCP接入和数据采集模块 (depends: 2, 3) [unspecified-high]
├── Task 10: LLM调用封装和费用监控 (depends: 3) [unspecified-high]
└── Task 11: 定时任务调度引擎 (depends: 3) [unspecified-high]

Wave 3 (Wave 2完成后 — Agent基础模块):
├── Task 8: 飞书机器人问答功能（对接RAG）(depends: 5, 7) [unspecified-high]
├── Task 14: 选品分析Agent (depends: 7, 9, 10, 11) [deep]
├── Task 15: 飞书多维表格同步模块 (depends: 5) [unspecified-high]
├── Task 16: 日志审计和紧急停机系统 (depends: 3, 11) [unspecified-high]
└── Task 20: Mock数据准备和系统预填充 (depends: 4, 7, 9) [unspecified-high]

Wave 4 (Wave 3完成后 — Agent集成):
├── Task 12: 核心管理Agent — 每日数据汇报 (depends: 8, 10, 11) [deep]
└── Task 13: 核心管理Agent — 人工审批流程 (depends: 8) [unspecified-high]

Wave 5 (Wave 4完成后 — 联调+文档):
├── Task 17: 全链路联调和端到端测试 (depends: 12, 13, 14, 15, 16) [deep]
└── Task 19: 团队使用手册和培训 (depends: 8, 12, 14, 15) [writing]

Wave 6 (Wave 5完成后 — 部署上线):
└── Task 18: 云端部署和24小时运行 (depends: 17) [unspecified-high]

Wave FINAL (所有任务完成后 — 4个并行审查，然后用户确认):
├── Task F1: 计划合规审计 (oracle)
├── Task F2: 代码质量审查 (unspecified-high)
├── Task F3: 实际QA验证 (unspecified-high)
└── Task F4: 范围保真度检查 (deep)
-> 呈现结果 -> 获得用户明确同意

关键路径: Task 1 → Task 2 → Task 7 → Task 8 → Task 12 → Task 17 → Task 18 → F1-F4 → 用户确认
并行加速: ~65% 快于顺序执行
最大并发: 6 (Wave 1)
```

### 依赖矩阵

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | 2, 3, 5, 6 | 1 |
| 2 | — | 7, 9 | 1 |
| 3 | — | 7, 9, 10, 11 | 1 |
| 4 | — | 7 | 1 |
| 5 | — | 8, 13, 15 | 1 |
| 6 | — | (外部依赖，不阻塞Phase 1) | 1 |
| 7 | 2, 3, 4 | 8, 14, 20 | 2 |
| 9 | 2, 3 | 14, 20 | 2 |
| 10 | 3 | 12, 14 | 2 |
| 11 | 3 | 12, 14, 16 | 2 |
| 8 | 5, 7 | 12, 13, 19 | 3 |
| 14 | 7, 9, 10, 11 | 17, 19 | 3 |
| 15 | 5 | 17, 19 | 3 |
| 16 | 3, 11 | 17 | 3 |
| 20 | 4, 7, 9 | — | 3 |
| 12 | 8, 10, 11 | 17, 19 | 4 |
| 13 | 8 | 17 | 4 |
| 17 | 12, 13, 14, 15, 16 | 18 | 5 |
| 19 | 8, 12, 14, 15 | — | 5 |
| 18 | 17 | F1-F4 | 6 |

### Agent调度摘要

- **Wave 1**: **6** — T1→`quick`, T2→`unspecified-high`, T3→`quick`, T4→`unspecified-high`, T5→`unspecified-high`, T6→`quick`
- **Wave 2**: **4** — T7→`deep`, T9→`unspecified-high`, T10→`unspecified-high`, T11→`unspecified-high`
- **Wave 3**: **5** — T8→`unspecified-high`, T14→`deep`, T15→`unspecified-high`, T16→`unspecified-high`, T20→`unspecified-high`
- **Wave 4**: **2** — T12→`deep`, T13→`unspecified-high`
- **Wave 5**: **2** — T17→`deep`, T19→`writing`
- **Wave 6**: **1** — T18→`unspecified-high`
- **FINAL**: **4** — F1→`oracle`, F2→`unspecified-high`, F3→`unspecified-high`, F4→`deep`

---

## TODOs

- [x] 1. 云服务器和基础环境搭建

  **What to do**:
  - 选择并开通云服务器（推荐：AWS Lightsail 或阿里云ECS，新加坡节点——兼顾国内团队访问速度和美国亚马逊API延迟）
  - 最低配置：2核4G内存，50G SSD，Ubuntu 22.04 LTS
  - 安装基础环境：Python 3.11+，PostgreSQL 16，Nginx，Docker（可选）
  - 配置安全组：仅开放80/443（Web）、22（SSH，限IP）
  - 配置域名和SSL证书（飞书回调必须HTTPS）
  - 设置SSH密钥登录，禁用密码登录

  **Must NOT do**:
  - 不开放数据库端口到公网
  - 不使用root账户运行应用

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 标准化的服务器配置任务，步骤明确
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: 非浏览器任务

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4, 5, 6)
  - **Blocks**: Tasks 2（数据库需要服务器）, 5（飞书需要HTTPS端点）
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `构思.md:14` - 用户要求"部署到云端服务器运行以确保24小时在线"

  **External References**:
  - AWS Lightsail: https://lightsail.aws.amazon.com/ — 简单易用的VPS服务
  - 阿里云ECS: https://www.aliyun.com/product/ecs — 国内访问更快
  - Let's Encrypt: https://letsencrypt.org/ — 免费SSL证书

  **WHY Each Reference Matters**:
  - AWS Lightsail适合新手，界面简单，价格透明（$20/月起）
  - 新加坡节点是国内访问海外服务的最佳折中点
  - SSL证书是飞书机器人回调的硬性要求

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: SSH连接验证
    Tool: Bash (ssh)
    Preconditions: 服务器已创建，SSH密钥已配置
    Steps:
      1. ssh -i ~/.ssh/key user@server-ip "python3 --version"
      2. 验证输出包含 "Python 3.11" 或更高版本
      3. ssh -i ~/.ssh/key user@server-ip "psql --version"
      4. 验证输出包含 "psql (PostgreSQL) 16"
    Expected Result: Python 3.11+ 和 PostgreSQL 16 已安装
    Failure Indicators: 连接超时、版本不匹配
    Evidence: .sisyphus/evidence/task-1-ssh-verify.txt

  Scenario: HTTPS端点可达性
    Tool: Bash (curl)
    Preconditions: Nginx和SSL已配置
    Steps:
      1. curl -I https://your-domain.com/ （Nginx默认页面或自定义静态页面）
      2. 验证返回 HTTP 200 或 301/302（Nginx正常响应）
      3. 验证证书有效（无SSL错误）：curl -vI https://your-domain.com/ 2>&1 | grep "SSL certificate verify ok"
    Expected Result: HTTPS可达，SSL证书有效，Nginx正常响应
    Failure Indicators: 连接拒绝、SSL证书错误、Nginx未启动
    Evidence: .sisyphus/evidence/task-1-https-verify.txt

  Scenario: 安全配置验证
    Tool: Bash (nmap/curl)
    Preconditions: 安全组已配置
    Steps:
      1. 从外部尝试连接数据库端口5432，验证连接被拒绝（nmap -p 5432 server-ip | grep filtered/closed）
      2. 验证SSH仅接受密钥登录：ssh -o PasswordAuthentication=yes user@server-ip 验证被拒绝
      3. 验证UFW状态：ssh user@server-ip "sudo ufw status" → 仅22,80,443开放
    Expected Result: 数据库端口不可达（安全组未开放），密码登录被禁用，UFW仅开放必要端口
    Failure Indicators: 5432端口开放、密码登录成功、UFW规则过宽
    Evidence: .sisyphus/evidence/task-1-security-verify.txt
  ```

  **Commit**: YES
  - Message: `chore(infra): provision cloud server and configure base environment`
  - Files: `docs/server-setup.md`, `scripts/setup-server.sh`
  - Pre-commit: N/A (基础设施任务)

- [x] 2. 数据库设计和搭建（PostgreSQL + pgvector）

  **What to do**:
  - 安装PostgreSQL 16和pgvector扩展
  - 设计数据库Schema，核心表包括：
    - `documents` — 知识库文档（id, title, content, source, category, embedding, created_at）
    - `document_chunks` — 文档分块（id, document_id, chunk_text, chunk_embedding, chunk_index）
    - `products` — 产品信息（id, sku, name, asin, keywords, status, created_at）
    - `product_selection` — 选品记录（id, candidate_asin, reason, score, agent_run_id, created_at）
    - `agent_runs` — Agent运行日志（id, agent_type, status, input_summary, output_summary, cost_usd, started_at, finished_at）
    - `agent_tasks` — Agent任务队列（id, agent_type, trigger_type, payload, status, scheduled_at）
    - `approval_requests` — 审批记录（id, agent_run_id, action_type, payload, status, approved_by, created_at）
    - `daily_reports` — 日报记录（id, report_date, content_json, sent_at）
    - `system_config` — 系统配置（key, value, updated_at）
    - `audit_logs` — 审计日志（id, action, actor, pre_state, post_state, created_at）
  - 创建数据库迁移脚本（使用Alembic）
  - 配置pgvector扩展，创建向量索引（IVFFlat或HNSW）
  - 创建数据库连接池配置

  **Must NOT do**:
  - 不在迁移脚本中硬编码数据库密码
  - 不跳过向量索引创建

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 数据库设计需要理解业务领域，Schema影响全局
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4, 5, 6)
  - **Blocks**: Tasks 7, 9, 20
  - **Blocked By**: None（可先在本地开发，后部署到服务器）

  **References**:

  **Pattern References**:
  - `构思.md:14` - "构建底层数据库，用于存放知识库数据、销售数据、广告数据、Agent产出文档"
  - `构思.md:49-50` - "所有自动化动作都必须输出日志，保证可审计，可追溯，可回滚"

  **External References**:
  - pgvector官方文档: https://github.com/pgvector/pgvector — 向量搜索扩展
  - Alembic迁移工具: https://alembic.sqlalchemy.org/ — 数据库版本管理
  - SQLAlchemy ORM: https://www.sqlalchemy.org/ — Python ORM框架

  **WHY Each Reference Matters**:
  - pgvector让PostgreSQL同时处理结构化数据和向量搜索，不需要额外维护一个向量数据库
  - Alembic确保数据库变更可追踪可回滚
  - audit_logs表实现用户要求的"可审计、可追溯、可回滚"

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 数据库连接和扩展验证
    Tool: Bash (psql)
    Preconditions: PostgreSQL已安装
    Steps:
      1. psql -U app_user -d amazon_ai -c "SELECT extversion FROM pg_extension WHERE extname='vector';"
      2. 验证pgvector扩展已安装
      3. psql -U app_user -d amazon_ai -c "\dt" 查看所有表
      4. 验证所有10个核心表已创建
    Expected Result: pgvector已安装，10个表已创建
    Failure Indicators: 扩展未找到、表缺失
    Evidence: .sisyphus/evidence/task-2-db-schema.txt

  Scenario: 向量搜索功能验证
    Tool: Bash (Python脚本)
    Preconditions: document_chunks表已创建
    Steps:
      1. 插入3条测试向量记录
      2. 执行向量相似度搜索 SELECT * FROM document_chunks ORDER BY chunk_embedding <=> '[test_vector]' LIMIT 3
      3. 验证返回结果按相似度排序
    Expected Result: 向量搜索返回正确排序的结果
    Failure Indicators: 查询报错、排序不正确
    Evidence: .sisyphus/evidence/task-2-vector-search.txt

  Scenario: 迁移脚本可回滚
    Tool: Bash (alembic)
    Preconditions: 迁移脚本已创建
    Steps:
      1. alembic upgrade head （执行所有迁移）
      2. alembic downgrade -1 （回退一个版本）
      3. alembic upgrade head （重新升级）
      4. 验证数据库状态正常
    Expected Result: 迁移可升级、可回退、可重新升级
    Evidence: .sisyphus/evidence/task-2-migration-rollback.txt
  ```

  **Commit**: YES
  - Message: `feat(db): initialize PostgreSQL with pgvector and schema migrations`
  - Files: `src/db/models.py`, `src/db/__init__.py`, `src/db/connection.py`, `alembic/`, `alembic.ini`
  - Pre-commit: `pytest tests/test_db.py --mock-external-apis`

- [x] 3. Python项目骨架和配置体系

  **What to do**:
  - 创建Python项目结构：
    ```
    amazon-automation/
    ├── src/
    │   ├── __init__.py
    │   ├── config.py          # 环境变量配置管理
    │   ├── db/                 # 数据库模块
    │   ├── agents/             # 所有Agent模块
    │   │   ├── core_agent/     # 核心管理Agent
    │   │   ├── selection_agent/ # 选品Agent
    │   │   └── base_agent.py   # Agent基类
    │   ├── feishu/             # 飞书集成模块
    │   ├── knowledge_base/     # 知识库RAG模块
    │   ├── seller_sprite/      # 卖家精灵MCP模块
    │   ├── amazon_api/         # 亚马逊API模块（Phase 2）
    │   ├── scheduler/          # 定时任务
    │   ├── llm/                # LLM调用封装
    │   └── utils/              # 工具函数
    ├── tests/
    │   ├── conftest.py         # pytest配置和fixtures
    │   ├── golden_qa.json      # 知识库黄金QA数据集
    │   └── test_*.py
    ├── scripts/                # 运维脚本
    ├── data/
    │   ├── raw_docs/           # 原始知识库文档
    │   ├── processed_docs/     # 处理后的文档
    │   └── mock/               # Mock数据
    ├── .env.example            # 环境变量模板
    ├── pyproject.toml          # 项目配置
    ├── requirements.txt        # 依赖列表
    └── Makefile               # 常用命令快捷方式
    ```
  - 使用pydantic-settings管理配置（从.env读取）
  - 创建.env.example模板，包含所有需要的环境变量
  - 配置pytest和日志框架（loguru）
  - 创建Makefile，包含常用命令：`make test`, `make run`, `make lint`, `make deploy`
  - 安装核心依赖：langchain, langraph, openai, anthropic, httpx, pydantic, sqlalchemy, alembic, loguru, apscheduler

  **Must NOT do**:
  - 不创建.env文件（只创建.env.example）
  - 不在requirements.txt中使用不固定版本

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 项目脚手架搭建，模板化工作
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4, 5, 6)
  - **Blocks**: Tasks 7, 9, 10, 11
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `requirements.txt` - 当前仅有requests, python-dotenv, playwright，需要大幅扩充
  - `构思.md:14` - 主Agent管理多Agent模式 → LangGraph是最佳选择

  **External References**:
  - LangGraph: https://python.langchain.com/docs/langgraph — 多Agent编排框架
  - pydantic-settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/ — 环境变量管理
  - loguru: https://github.com/Delgan/loguru — 简洁的日志库

  **WHY Each Reference Matters**:
  - LangGraph支持有状态、可恢复、可循环的多Agent工作流，适合11个Agent的协调
  - pydantic-settings确保所有配置从环境变量读取，不会硬编码
  - loguru比标准logging更简洁，适合零代码基础用户阅读日志

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 项目结构验证
    Tool: Bash
    Preconditions: 项目已创建
    Steps:
      1. ls -R src/ 验证目录结构完整
      2. python -c "from src.config import Settings; s = Settings(); print(s)" 验证配置加载
      3. pytest tests/ --co 验证测试发现
    Expected Result: 目录结构完整，配置可加载，pytest可发现测试
    Failure Indicators: ImportError、目录缺失
    Evidence: .sisyphus/evidence/task-3-project-structure.txt

  Scenario: Makefile命令可用
    Tool: Bash
    Preconditions: Makefile已创建
    Steps:
      1. make test 运行测试
      2. make lint 运行代码检查
    Expected Result: 命令正常执行，无报错
    Evidence: .sisyphus/evidence/task-3-makefile.txt
  ```

  **Commit**: YES
  - Message: `chore(project): setup Python project skeleton with config management`
  - Files: `src/`, `tests/`, `pyproject.toml`, `requirements.txt`, `Makefile`, `.env.example`
  - Pre-commit: `pytest tests/ -v`

- [x] 4. 知识库文档预处理（清洗、分类、分块）

  **What to do**:
  - 编写文档批量加载脚本，支持Word(.docx)、PDF、Markdown三种格式
  - 使用LlamaParse或unstructured库解析文档内容
  - 核心处理逻辑封装到 `src/knowledge_base/document_processor.py` 模块中（包含：加载、解析、分类、去重、分块方法），`scripts/preprocess_docs.py` 作为调用入口
  - 实现文档自动分类逻辑（基于内容关键词分为：选品方法论、广告策略、Listing优化、品牌建设、供应链管理、通用运营等类别）
  - 实现文档去重逻辑（550篇+2000篇可能有大量重复）
  - 实现文档分块策略：
    - 按语义段落分块，每块500-1000 tokens
    - 保留上下文重叠（overlap 100 tokens）
    - 每块保留元数据（文档来源、分类、标题）
  - 输出处理统计报告：总文档数、成功/失败数、分类分布、去重数
  - 创建20组黄金QA数据集（golden_qa.json），从知识库中精选问答对，用于后续RAG质量评测

  **Must NOT do**:
  - 不修改原始文档文件
  - 不丢弃无法解析的文档（记录到失败列表）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 文档处理涉及多格式解析、NLP分类、去重等复杂逻辑
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 5, 6)
  - **Blocks**: Task 7
  - **Blocked By**: None（处理文档不需要数据库，先处理后入库）

  **References**:

  **Pattern References**:
  - `构思.md:10-11` - "550篇碎片化的运营思路文档"+"2000多篇思考文档"
  - `构思.md:11` - "这是我们公司的核心运营思路及价值观，所有AIagent都不能偏离这个原则"

  **External References**:
  - LlamaParse: https://docs.llamaindex.ai/en/stable/llama_cloud/llama_parse/ — 高质量文档解析
  - unstructured: https://github.com/Unstructured-IO/unstructured — 通用文档解析库
  - LangChain TextSplitters: https://python.langchain.com/docs/modules/data_connection/document_transformers/ — 文档分块策略

  **WHY Each Reference Matters**:
  - 550篇无分类文档需要自动分类，这决定了Agent检索时的准确度
  - 去重避免RAG返回冗余信息
  - 黄金QA数据集是知识库质量的唯一客观衡量标准

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 批量文档处理
    Tool: Bash (Python脚本)
    Preconditions: 原始文档已放入data/raw_docs/
    Steps:
      1. python scripts/preprocess_docs.py --input data/raw_docs/ --output data/processed_docs/
      2. 验证处理报告：总数≥550，失败率<5%
      3. 验证分类分布：每个类别至少有10篇文档
      4. 验证分块结果：每个分块在500-1000 tokens之间
    Expected Result: ≥95%文档成功处理，分类合理，分块大小合规
    Failure Indicators: 失败率>5%，某分类为0，分块超出范围
    Evidence: .sisyphus/evidence/task-4-preprocess-report.json

  Scenario: 去重验证
    Tool: Bash (Python脚本)
    Preconditions: 文档已处理
    Steps:
      1. python scripts/preprocess_docs.py --check-duplicates
      2. 验证去重报告：显示去重数量和相似对
    Expected Result: 重复文档被标记，去重后文档数<原始总数
    Evidence: .sisyphus/evidence/task-4-dedup-report.json

  Scenario: 黄金QA数据集
    Tool: Bash
    Preconditions: golden_qa.json已创建
    Steps:
      1. python -c "import json; d=json.load(open('tests/golden_qa.json')); print(len(d))"
      2. 验证≥20组QA对
      3. 验证每个QA对有question和expected_answer字段
    Expected Result: ≥20组QA对，格式完整
    Evidence: .sisyphus/evidence/task-4-golden-qa.txt
  ```

  **Commit**: YES
  - Message: `feat(kb): preprocess and clean knowledge base documents`
  - Files: `src/knowledge_base/document_processor.py`, `scripts/preprocess_docs.py`, `data/processed_docs/`, `tests/golden_qa.json`
  - Pre-commit: `pytest tests/test_preprocess.py`

- [x] 5. 飞书机器人创建和基础接入

  **What to do**:
  - 在飞书开放平台（open.feishu.cn）创建自建应用
  - 配置机器人能力，获取App ID和App Secret
  - 申请必要权限：消息发送（im:message:send）、群组管理、多维表格读写、云文档读写
  - 实现飞书SDK封装模块：
    - 获取和刷新tenant_access_token
    - 发送文本消息到群组
    - 发送富文本/卡片消息
    - 接收消息事件（Webhook回调）
  - 配置事件订阅URL（需要Task 1的HTTPS端点）
  - 创建测试飞书群，邀请机器人入群
  - 实现消息事件监听：机器人被@时触发处理逻辑

  **Must NOT do**:
  - 不硬编码App ID和App Secret
  - 不使用自定义Webhook（需要自建应用才能实现交互卡片）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 飞书API接入涉及OAuth认证、Webhook、消息格式等多环节
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 4, 6)
  - **Blocks**: Tasks 8, 13, 15
  - **Blocked By**: None（本地开发先行，部署时再配置回调URL）

  **References**:

  **Pattern References**:
  - `构思.md:16-17` - "主agent在飞书中进行每日汇报，管理各个AIagent的任务进程"
  - `构思.md:17` - "团队成员如需问答可以在飞书中咨询"

  **External References**:
  - 飞书开放平台: https://open.feishu.cn/document/ — 官方文档
  - lark-oapi (Python SDK): https://github.com/larksuite/oapi-sdk-python — 飞书官方Python SDK
  - 飞书消息卡片搭建工具: https://open.feishu.cn/tool/cardbuilder — 可视化搭建卡片

  **WHY Each Reference Matters**:
  - 飞书自建应用（非Webhook）才能支持交互卡片（审批按钮等）
  - lark-oapi是官方维护的SDK，处理了token刷新等细节
  - 消息卡片是审批流程的基础

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 飞书机器人发送消息
    Tool: Bash (Python脚本)
    Preconditions: 飞书应用已创建，机器人已加入测试群
    Steps:
      1. python tests/test_feishu.py --send-text "Hello from AI System"
      2. 验证测试群收到消息
      3. python tests/test_feishu.py --send-card --title "测试卡片" --content "系统测试"
      4. 验证测试群收到卡片消息
    Expected Result: 文本消息和卡片消息均成功发送
    Failure Indicators: API返回错误、消息未送达
    Evidence: .sisyphus/evidence/task-5-feishu-send.txt

  Scenario: 飞书消息接收（Webhook）
    Tool: Bash (curl)
    Preconditions: Webhook端点已配置
    Steps:
      1. 模拟飞书Webhook回调: curl -X POST http://localhost:8000/feishu/webhook -d '{"event_type":"im.message.receive_v1","event":{"message":{"content":"测试"}}}'
      2. 验证服务器正确解析消息
      3. 验证返回200状态码
    Expected Result: Webhook正确处理，返回200
    Failure Indicators: 500错误、解析失败
    Evidence: .sisyphus/evidence/task-5-feishu-webhook.txt

  Scenario: Token自动刷新
    Tool: Bash (Python脚本)
    Preconditions: 飞书应用凭证已配置
    Steps:
      1. python tests/test_feishu.py --test-token-refresh
      2. 验证获取到valid tenant_access_token
      3. 验证token过期前自动刷新
    Expected Result: Token获取成功，自动刷新逻辑正常
    Evidence: .sisyphus/evidence/task-5-feishu-token.txt
  ```

  **Commit**: YES
  - Message: `feat(feishu): create Feishu bot app and basic webhook handler`
  - Files: `src/feishu/`, `tests/test_feishu.py`
  - Pre-commit: `pytest tests/test_feishu.py --mock-external-apis`

- [x] 6. 亚马逊SP-API开发者账号申请（外部依赖）

  **What to do**:
  - 编写详细的SP-API申请指南文档，包含：
    - 申请步骤截图和说明
    - 所需信息清单（品牌信息、公司信息等）
    - 常见拒绝原因和避免方法
  - 指导JIM在Amazon Developer Central提交开发者申请
  - 配置开发者沙箱环境（用于本地测试）
  - 创建SP-API Mock数据模块：
    - 模拟商品信息API响应
    - 模拟订单数据API响应
    - 模拟广告数据API响应
    - 模拟库存数据API响应
  - 这个任务的产出不阻塞Phase 1（Phase 1全部使用Mock数据）

  **Must NOT do**:
  - 不在Phase 1进行任何SP-API写入操作
  - 不将SP-API审批作为Phase 1的阻塞项

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 主要是文档编写和Mock数据创建
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 4, 5)
  - **Blocks**: None（Phase 1不依赖SP-API）
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `构思.md:8` - "亚马逊API接口（当前是沙箱状态，构建完成后可接入可用状态）"

  **External References**:
  - Amazon SP-API文档: https://developer-docs.amazon.com/sp-api/ — 官方开发者文档
  - SP-API申请指南: https://developer-docs.amazon.com/sp-api/docs/registering-as-a-developer — 注册流程

  **WHY Each Reference Matters**:
  - SP-API审批需2-4周，越早提交越好
  - Mock数据确保Phase 1开发不被阻塞

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Mock数据完整性
    Tool: Bash (Python脚本)
    Preconditions: Mock数据模块已创建
    Steps:
      1. python -c "from src.amazon_api.mock import get_mock_products; print(len(get_mock_products()))"
      2. 验证返回≥3个模拟产品
      3. python -c "from src.amazon_api.mock import get_mock_orders; print(len(get_mock_orders()))"
      4. 验证返回≥30天的模拟订单数据
    Expected Result: Mock数据涵盖产品、订单、广告、库存4个维度
    Failure Indicators: ImportError、数据为空
    Evidence: .sisyphus/evidence/task-6-mock-data.txt

  Scenario: 申请指南文档完整
    Tool: Bash
    Preconditions: 文档已创建
    Steps:
      1. 验证 docs/sp-api-guide.md 存在
      2. 验证文档包含"申请步骤"、"所需材料"、"常见问题"章节
    Expected Result: 指南文档完整，可指导用户完成申请
    Evidence: .sisyphus/evidence/task-6-guide-check.txt
  ```

  **Commit**: YES
  - Message: `docs(api): document Amazon SP-API application steps and create mock data`
  - Files: `docs/sp-api-guide.md`, `src/amazon_api/mock.py`, `data/mock/`
  - Pre-commit: `pytest tests/test_mock_data.py`

- [x] 7. 知识库RAG系统搭建（向量化 + 检索）

  **What to do**:
  - 选择Embedding模型：OpenAI text-embedding-3-small（英文优秀+中文可用，$0.02/1M tokens，性价比最高）
  - 实现文档向量化Pipeline：
    - 读取处理后的文档分块
    - 调用Embedding API生成向量
    - 批量写入PostgreSQL/pgvector
    - 记录向量化进度和失败项
  - 实现RAG检索模块：
    - 接收用户查询 → 生成查询向量 → pgvector相似度搜索 → 返回Top-K相关文档块
    - 支持元数据过滤（按分类、按来源过滤）
    - 支持混合搜索（向量搜索 + 关键词搜索）
  - 实现RAG问答Chain：
    - 检索相关文档块 → 构建Prompt（含系统指令+检索结果+用户问题）→ 调用LLM → 返回答案
    - Prompt中明确要求：如果知识库无相关信息，回答"我没有找到相关信息"而非编造
    - 在回答中标注引用来源（文档名+段落）
  - 实现RAGAS评测脚本：
    - 使用golden_qa.json评测RAG质量
    - 计算faithfulness、context_precision、answer_relevancy指标
    - 质量门控：faithfulness ≥ 0.85 才允许上线

  **Must NOT do**:
  - 不使用本地Embedding模型（增加服务器开销，Phase 1用云API）
  - 不跳过RAGAS评测（这是质量门控）
  - 知识库回答不得编造信息

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: RAG系统是整个平台的基础，需要深入理解检索、Embedding、Prompt工程
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES（与Task 9, 10, 11并行）
  - **Parallel Group**: Wave 2 (with Tasks 9, 10, 11)
  - **Blocks**: Tasks 8, 14, 20
  - **Blocked By**: Tasks 2（数据库）, 3（项目骨架）, 4（处理后的文档）

  **References**:

  **Pattern References**:
  - `构思.md:11` - "所有AIagent都不能偏离这个原则" → RAG必须忠实于知识库
  - `构思.md:14` - "用于存放知识库数据" → pgvector存储

  **External References**:
  - LangChain RAG: https://python.langchain.com/docs/tutorials/rag/ — RAG教程
  - RAGAS: https://docs.ragas.io/ — RAG评测框架
  - OpenAI Embeddings: https://platform.openai.com/docs/guides/embeddings — Embedding API

  **WHY Each Reference Matters**:
  - LangChain提供成熟的RAG pipeline组件
  - RAGAS是唯一客观评价RAG质量的方法
  - 混合搜索（向量+关键词）提升中文检索准确度

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 知识库问答——正确回答
    Tool: Bash (Python脚本)
    Preconditions: 知识库已向量化入库
    Steps:
      1. python -c "from src.knowledge_base.rag_engine import query; print(query('亚马逊广告ACOS多少算好？'))"
      2. 验证回答包含知识库中的相关内容
      3. 验证回答包含引用来源
    Expected Result: 回答准确，引用来源标注
    Failure Indicators: 回答为空、回答编造信息、无引用来源
    Evidence: .sisyphus/evidence/task-7-rag-query-positive.txt

  Scenario: 知识库问答——拒绝编造
    Tool: Bash (Python脚本)
    Preconditions: 知识库已向量化入库
    Steps:
      1. python -c "from src.knowledge_base.rag_engine import query; print(query('欧洲站退货政策是什么？'))"
      2. 验证回答包含"没有找到相关信息"或类似拒绝回答
    Expected Result: 对于知识库未覆盖的问题，拒绝编造
    Failure Indicators: 编造了欧洲站退货政策
    Evidence: .sisyphus/evidence/task-7-rag-query-negative.txt

  Scenario: RAGAS评测达标
    Tool: Bash (Python脚本)
    Preconditions: golden_qa.json存在，知识库已入库
    Steps:
      1. python tests/eval_rag.py --golden-dataset tests/golden_qa.json
      2. 验证 faithfulness >= 0.85
      3. 验证 context_precision >= 0.80
    Expected Result: 所有RAGAS指标达标
    Failure Indicators: 任一指标低于阈值
    Evidence: .sisyphus/evidence/task-7-ragas-eval.json
  ```

  **Commit**: YES
  - Message: `feat(kb): implement RAG system with pgvector embeddings and RAGAS evaluation`
  - Files: `src/knowledge_base/`, `tests/eval_rag.py`, `tests/test_rag.py`
  - Pre-commit: `pytest tests/test_rag.py --mock-external-apis`

- [x] 8. 飞书机器人问答功能（对接RAG）

  **What to do**:
  - 在飞书Webhook消息处理中接入RAG系统：
    - 用户@机器人发送问题 → 调用RAG查询 → 返回回答
  - 实现消息格式化：
    - 回答用富文本格式，包含标题、正文、引用来源
    - 长回答自动分段
    - 错误情况返回友好提示
  - 实现会话上下文管理：
    - 同一用户连续提问时，保持上下文（最近5轮对话）
    - 超过5轮自动清除上下文
  - 实现指令路由：
    - "@机器人 问：xxx" → 知识库问答
    - "@机器人 选品分析" → 触发选品Agent
    - "@机器人 今日报告" → 手动触发日报
    - "@机器人 暂停所有" → 紧急停机
    - "@机器人 帮助" → 显示可用指令列表
  - 实现响应时间优化：
    - 先发送"正在思考中..."的临时消息
    - 完成后替换为正式回答（避免用户等待焦虑）

  **Must NOT do**:
  - 不在消息中暴露内部错误堆栈
  - 不允许非授权群组的消息触发Agent

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 需要理解飞书消息API + RAG集成 + 指令路由设计
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES（与Task 14, 15, 16, 20并行）
  - **Parallel Group**: Wave 3 (with Tasks 14, 15, 16, 20)
  - **Blocks**: Tasks 12, 13, 19
  - **Blocked By**: Tasks 5（飞书基础, Wave 1）, 7（RAG系统, Wave 2）

  **References**:

  **Pattern References**:
  - `构思.md:17` - "问答任何关于运营知识、关于店铺数据、关于广告数据等等都可以在飞书中咨询"
  - `构思.md:17` - "可以特定性的创建一些特殊任务"

  **External References**:
  - 飞书消息API: https://open.feishu.cn/document/server-docs/im-v1/message/create — 发送消息
  - 飞书富文本格式: https://open.feishu.cn/document/common-capabilities/message-card/message-cards-content — 卡片消息

  **WHY Each Reference Matters**:
  - 飞书卡片消息比纯文本更美观，用户体验更好
  - 指令路由让一个机器人入口连接所有Agent功能

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 知识库问答端到端
    Tool: Bash (Python脚本)
    Preconditions: 飞书机器人+RAG系统均已就绪
    Steps:
      1. 模拟飞书消息: python tests/test_feishu_qa.py --query "什么是关键词上首页策略？"
      2. 验证回答在5秒内返回
      3. 验证回答包含知识库相关内容
      4. 验证回答格式为富文本（含引用来源）
    Expected Result: 5秒内返回准确回答，格式正确
    Failure Indicators: 超时、空回答、纯文本格式
    Evidence: .sisyphus/evidence/task-8-feishu-qa.txt

  Scenario: 指令路由
    Tool: Bash (Python脚本)
    Preconditions: 消息处理器已配置
    Steps:
      1. 发送"帮助"指令，验证返回指令列表
      2. 发送"选品分析"指令，验证触发选品Agent（dry-run模式）
      3. 发送无法识别的指令，验证返回友好提示
    Expected Result: 所有指令正确路由
    Evidence: .sisyphus/evidence/task-8-command-routing.txt
  ```

  **Commit**: YES
  - Message: `feat(feishu): implement Q&A bot connected to RAG system with command routing`
  - Files: `src/feishu/bot_handler.py`, `src/feishu/command_router.py`, `tests/test_feishu_qa.py`
  - Pre-commit: `pytest tests/test_feishu_qa.py --mock-external-apis`

- [x] 9. 卖家精灵MCP接入和数据采集模块

  **前置条件（⚠️ 需JIM配合）**:
  > **执行本任务前，JIM必须提供**：
  > 1. 卖家精灵账号的MCP接口文档/Schema（或提供账号让执行者登录查看文档）
  > 2. 卖家精灵API密钥/Token（写入.env的SELLER_SPRITE_API_KEY）
  >
  > **如果JIM无法及时提供**：本任务分两阶段执行：
  > - **阶段A（立即可做）**：实现接口抽象层+Mock实现+缓存+错误处理——不依赖真实API
  > - **阶段B（获得文档后）**：对接真实卖家精灵MCP API——替换Mock为真实调用
  > 
  > 阶段A的Mock数据格式参考卖家精灵网页版的数据字段（关键词搜索量、竞争度、ASIN数据等通用字段）。

  **What to do**:
  - **阶段A — 接口抽象+Mock（不依赖真实API）**:
    - 定义数据采集接口（Abstract Base Class）：
      - `search_keyword(keyword: str) -> KeywordData` — 关键词搜索量、竞争度、趋势
      - `get_asin_data(asin: str) -> ASINData` — 评分、review数、价格、BSR排名、月销量估算
      - `get_category_data(category: str) -> CategoryData` — 市场容量、头部卖家、价格分布
      - `reverse_lookup(asin: str) -> list[KeywordData]` — 关键词反查
    - 实现MockSellerSpriteClient — 返回合理的宠物用品类目模拟数据
    - 实现数据缓存层：
      - 相同查询24小时内返回缓存数据（避免重复调用浪费配额）
      - 缓存存储在PostgreSQL中
    - 实现速率限制和错误处理：
      - 遵守API速率限制（接口预留，Mock无限制）
      - 失败自动重试（最多3次，指数退避）
      - API异常发送飞书告警
    - 将采集数据存入数据库对应表
  - **阶段B — 真实API对接（获得文档后）**:
    - 研究卖家精灵MCP接口文档，映射到抽象接口
    - 实现RealSellerSpriteClient — 调用真实MCP API
    - 通过环境变量 `SELLER_SPRITE_USE_MOCK=true/false` 切换Mock/真实
    - 验证真实API返回数据与Mock数据格式一致

  **Must NOT do**:
  - 不超过API速率限制
  - 不缓存超过24小时的数据用于决策
  - 不将阶段B的真实API对接作为Phase 1的阻塞项（阶段A的Mock足以支撑选品Agent运行）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: API集成+数据采集+缓存策略
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES（与Task 7, 10, 11并行）
  - **Parallel Group**: Wave 2 (with Tasks 7, 10, 11)
  - **Blocks**: Tasks 14, 20
  - **Blocked By**: Tasks 2（数据库）, 3（项目骨架）

  **References**:

  **Pattern References**:
  - `构思.md:7-8` - "卖家精灵MCP" — 核心市场数据来源
  - `构思.md:20,23` - 品牌规划和选品Agent都依赖卖家精灵数据

  **External References**:
  - 卖家精灵官网: https://www.sellersprite.com/ — 网页版功能和数据字段参考（用于设计Mock数据格式）
  - 卖家精灵MCP文档: **待JIM提供账号后获取**（阶段B前置条件）
  - MCP (Model Context Protocol): https://modelcontextprotocol.io/ — MCP协议说明（理解MCP工具调用方式）

  **WHY Each Reference Matters**:
  - 卖家精灵是选品Agent的核心数据源，但API文档需账号才能访问
  - 阶段A的Mock数据字段设计参考网页版的展示字段（搜索量、竞争度、BSR等）
  - MCP协议允许AI直接调用工具，阶段B需要理解调用方式

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Mock模式关键词数据查询（阶段A）
    Tool: Bash (Python脚本)
    Preconditions: SELLER_SPRITE_USE_MOCK=true
    Steps:
      1. python -c "from src.seller_sprite.client import get_client; c=get_client(); print(c.search_keyword('dog leash'))"
      2. 验证返回包含字段：search_volume, competition, trend
      3. 验证返回数据类型正确（search_volume为int, competition为float 0-1）
      4. 再次查询相同关键词，验证命中缓存（日志显示"cache hit"）
    Expected Result: Mock数据完整返回，缓存正常工作
    Failure Indicators: 字段缺失、类型错误、缓存未生效
    Evidence: .sisyphus/evidence/task-9-mock-keyword.txt

  Scenario: 接口抽象层验证（阶段A）
    Tool: Bash (Python脚本)
    Preconditions: 模块已创建
    Steps:
      1. 验证SellerSpriteBase抽象类存在4个方法签名
      2. 验证MockSellerSpriteClient实现了全部4个方法
      3. 验证get_client()在SELLER_SPRITE_USE_MOCK=true时返回Mock实例
    Expected Result: 接口抽象正确，Mock实现完整
    Evidence: .sisyphus/evidence/task-9-interface.txt

  Scenario: API错误处理和告警
    Tool: Bash (Python脚本)
    Preconditions: 模拟API不可用
    Steps:
      1. 设置SELLER_SPRITE_MOCK_ERROR=true
      2. 调用数据采集，验证重试3次后报告失败
      3. 验证飞书收到告警消息
    Expected Result: 优雅失败+飞书告警
    Evidence: .sisyphus/evidence/task-9-error-handling.txt
  ```

  **Commit**: YES
  - Message: `feat(data): integrate Seller Sprite MCP data collection with caching`
  - Files: `src/seller_sprite/`, `tests/test_seller_sprite.py`
  - Pre-commit: `pytest tests/test_seller_sprite.py --mock-external-apis`

- [x] 10. LLM调用封装和费用监控

  **What to do**:
  - 实现统一LLM调用封装模块：
    - 支持OpenAI GPT-4o/GPT-4o-mini和Anthropic Claude
    - 统一接口：`llm.chat(model, messages, temperature, max_tokens)`
    - 自动选择模型：简单任务用GPT-4o-mini（便宜），复杂任务用GPT-4o/Claude
  - 实现费用监控：
    - 每次调用记录：模型、输入tokens、输出tokens、费用（按官方定价计算）
    - 写入数据库agent_runs表
    - 每日汇总费用
  - 实现费用上限控制：
    - 环境变量：MAX_DAILY_LLM_COST_USD（默认50）
    - 达到80%时发送飞书预警
    - 达到100%时停止所有LLM调用，发送飞书告警
  - 实现PII过滤中间件：
    - 在发送给LLM之前，检测并脱敏可能的亚马逊客户PII数据
    - 正则匹配：邮箱、电话、姓名、地址等
    - 脱敏方式：替换为[REDACTED]

  **Must NOT do**:
  - 不将包含客户PII的数据发送给第三方LLM
  - 不允许单日费用无限增长

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 需要理解多LLM API + 费用计算 + PII检测
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES（与Task 7, 9, 11并行）
  - **Parallel Group**: Wave 2 (with Tasks 7, 9, 11)
  - **Blocks**: Tasks 12, 14
  - **Blocked By**: Task 3（项目骨架）

  **References**:

  **Pattern References**:
  - `构思.md:49-50` - "所有自动化动作都必须输出日志" → 每次LLM调用记录日志

  **External References**:
  - OpenAI Pricing: https://openai.com/pricing — 费用参考
  - Anthropic Pricing: https://www.anthropic.com/pricing — 费用参考
  - LiteLLM: https://github.com/BerriAI/litellm — 统一LLM调用库

  **WHY Each Reference Matters**:
  - LiteLLM提供统一接口调用100+模型，省去逐个适配
  - 费用监控是Metis识别的关键风险项——11个Agent并发可能月费数千美元

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: LLM调用和费用记录
    Tool: Bash (Python脚本)
    Preconditions: LLM API密钥已配置
    Steps:
      1. python -c "from src.llm.client import chat; r=chat('gpt-4o-mini', [{'role':'user','content':'hello'}]); print(r)"
      2. 验证数据库agent_runs表新增一条记录
      3. 验证记录包含input_tokens, output_tokens, cost_usd字段
    Expected Result: 调用成功，费用记录完整
    Evidence: .sisyphus/evidence/task-10-llm-cost.txt

  Scenario: 费用上限触发
    Tool: Bash (Python脚本)
    Preconditions: MAX_DAILY_LLM_COST_USD=0.01（极低以触发）
    Steps:
      1. 调用LLM直到费用超过上限
      2. 验证80%预警飞书消息已发送
      3. 验证100%时LLM调用被拒绝，返回费用超限错误
    Expected Result: 费用预警和拦截正常工作
    Evidence: .sisyphus/evidence/task-10-cost-limit.txt

  Scenario: PII过滤
    Tool: Bash (Python脚本)
    Preconditions: PII过滤模块已就绪
    Steps:
      1. 发送包含邮箱"john@example.com"和电话"555-1234"的内容
      2. 验证发送给LLM的内容中这些信息被替换为[REDACTED]
    Expected Result: PII被成功脱敏
    Evidence: .sisyphus/evidence/task-10-pii-filter.txt
  ```

  **Commit**: YES
  - Message: `feat(llm): implement LLM call wrapper with cost monitoring and PII filter`
  - Files: `src/llm/`, `tests/test_llm.py`
  - Pre-commit: `pytest tests/test_llm.py --mock-external-apis`

- [x] 11. 定时任务调度引擎

  **What to do**:
  - 使用APScheduler实现定时任务调度：
    - 支持Cron表达式（灵活配置执行时间）
    - 支持一次性任务和周期性任务
    - 任务持久化（重启后恢复）
  - 预配置任务计划：
    - 每日09:00：核心管理Agent发送日报
    - 每周一10:00：选品Agent运行分析
    - 每日23:00：LLM费用日报
  - 实现任务管理API：
    - GET /api/scheduler/jobs — 查看所有定时任务
    - POST /api/scheduler/jobs/{id}/pause — 暂停单个任务
    - POST /api/scheduler/jobs/{id}/resume — 恢复单个任务
    - POST /api/scheduler/trigger/{id} — 手动触发一次
  - 实现任务执行监控：
    - 每次执行记录开始时间、结束时间、状态、耗时
    - 失败任务自动重试（最多2次）
    - 失败后飞书告警

  **Must NOT do**:
  - 不使用简单sleep循环代替调度器
  - 不跳过任务执行日志记录

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 定时任务+持久化+API接口+监控
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES（与Task 7, 9, 10并行）
  - **Parallel Group**: Wave 2 (with Tasks 7, 9, 10)
  - **Blocks**: Tasks 12, 14, 16
  - **Blocked By**: Task 3（项目骨架）

  **References**:

  **Pattern References**:
  - `构思.md:20` - "定期（如一月一次）抓取市场数据" → 周期性任务
  - `构思.md:23` - "定期（如一周一次或两周一次）" → 可配置的Cron计划

  **External References**:
  - APScheduler: https://apscheduler.readthedocs.io/ — Python定时任务框架
  - FastAPI: https://fastapi.tiangolo.com/ — Web框架（提供API接口）

  **WHY Each Reference Matters**:
  - APScheduler支持Cron+一次性任务+持久化，是Python生态最成熟的调度库
  - FastAPI作为API层，为调度器提供HTTP管理接口

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 定时任务执行
    Tool: Bash (Python脚本)
    Preconditions: 调度器已启动
    Steps:
      1. 注册一个10秒后执行的测试任务
      2. 等待15秒
      3. 查询agent_runs表，验证任务已执行
    Expected Result: 任务在预定时间执行，日志已记录
    Failure Indicators: 任务未执行、日志缺失
    Evidence: .sisyphus/evidence/task-11-scheduler-exec.txt

  Scenario: 任务管理API
    Tool: Bash (curl)
    Preconditions: FastAPI服务已启动
    Steps:
      1. curl http://localhost:8000/api/scheduler/jobs — 获取任务列表，验证包含daily_report
      2. curl -X POST http://localhost:8000/api/scheduler/jobs/daily_report/pause — 暂停日报
      3. curl http://localhost:8000/api/scheduler/jobs — 再次获取列表，验证daily_report的status字段为"paused"
      4. curl -X POST http://localhost:8000/api/scheduler/jobs/daily_report/resume — 恢复
      5. curl http://localhost:8000/api/scheduler/jobs — 验证daily_report的status字段恢复为"active"
    Expected Result: 任务CRUD操作正常
    Evidence: .sisyphus/evidence/task-11-scheduler-api.txt

  Scenario: 任务失败处理
    Tool: Bash (Python脚本)
    Preconditions: 模拟任务失败
    Steps:
      1. 注册一个必定失败的测试任务
      2. 验证自动重试2次
      3. 验证最终失败后飞书收到告警
    Expected Result: 重试机制和告警均正常
    Evidence: .sisyphus/evidence/task-11-scheduler-retry.txt
  ```

  **Commit**: YES
  - Message: `feat(scheduler): implement task scheduling engine with APScheduler`
  - Files: `src/scheduler/__init__.py`, `src/scheduler/jobs.py`, `src/scheduler/config.py`, `tests/test_scheduler.py`
  - Pre-commit: `pytest tests/test_scheduler.py --mock-external-apis`

- [x] 12. 核心管理Agent — 每日数据汇报

  **What to do**:
  - 实现每日数据汇报Agent，每日09:00自动发送到飞书群：
    - 板块1——销售数据汇总：
      - 昨日总销售额、订单数、退货数（Phase 1用Mock数据）
      - 各SKU销量排行
      - 与前一天/上周同期对比（涨跌百分比+箭头emoji）
    - 板块2——Agent任务进度：
      - 各Agent最近运行状态（成功/失败/未运行）
      - 上次运行时间
      - 待审批任务数量
    - 板块3——市场动态简报：
      - 基于卖家精灵数据的类目趋势变化
      - 竞品动态（评分变化、新增review等）
      - 异常告警（库存低、广告异常等）
  - 实现数据汇总逻辑：
    - 从数据库读取各维度数据
    - 计算环比/同比指标
    - 生成结构化JSON报告
  - 实现飞书卡片消息格式化：
    - 使用飞书消息卡片模板
    - 关键数据高亮（绿色涨、红色跌）
    - 底部添加快捷操作按钮（"查看详情"、"触发选品分析"等）
  - 支持手动触发（飞书指令"@机器人 今日报告"）

  **Must NOT do**:
  - 不在报告中包含未经验证的数据
  - 不在Phase 1使用真实亚马逊数据（全部Mock）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 涉及多数据源汇总、复杂卡片消息格式、定时触发集成
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES（与Task 13并行）
  - **Parallel Group**: Wave 4 (with Task 13)
  - **Blocks**: Tasks 17, 19
  - **Blocked By**: Tasks 8（飞书问答, Wave 3）, 10（LLM封装, Wave 2）, 11（调度器, Wave 2）

  **References**:

  **Pattern References**:
  - `构思.md:16-17` - "主agent主要负责与我和团队成员在飞书中进行每日汇报"
  - 用户确认汇报内容：销售数据汇总 + Agent任务进度 + 市场动态简报

  **External References**:
  - 飞书消息卡片模板: https://open.feishu.cn/tool/cardbuilder — 可视化搭建
  - 飞书卡片JSON规范: https://open.feishu.cn/document/common-capabilities/message-card/message-cards-content

  **WHY Each Reference Matters**:
  - 飞书卡片消息支持颜色、按钮、分列布局，适合数据展示
  - Phase 1用Mock数据验证格式和流程，Phase 2切换真实数据

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 每日报告自动发送
    Tool: Bash (Python脚本)
    Preconditions: 调度器+飞书机器人+Mock数据已就绪
    Steps:
      1. python tests/test_daily_report.py --trigger-now
      2. 验证飞书群收到卡片消息
      3. 验证卡片包含3个板块（销售/Agent状态/市场动态）
      4. 验证数据字段不为空
    Expected Result: 报告发送成功，3个板块数据完整
    Failure Indicators: 消息未发送、板块缺失、数据为空
    Evidence: .sisyphus/evidence/task-12-daily-report.txt

  Scenario: 手动触发日报
    Tool: Bash (Python脚本)
    Preconditions: 飞书机器人已就绪
    Steps:
      1. 模拟飞书消息 "@机器人 今日报告"
      2. 验证30秒内收到日报卡片
    Expected Result: 手动触发正常工作
    Evidence: .sisyphus/evidence/task-12-manual-trigger.txt
  ```

  **Commit**: YES
  - Message: `feat(agents): implement core management agent daily report with Feishu cards`
  - Files: `src/agents/core_agent/daily_report.py`, `tests/test_daily_report.py`
  - Pre-commit: `pytest tests/test_daily_report.py --mock-external-apis`

- [x] 13. 核心管理Agent — 人工审批流程

  **What to do**:
  - 实现飞书交互卡片审批流程：
    - Agent产出建议后，发送审批卡片到飞书
    - 卡片包含：操作描述、影响范围、建议理由、风险提示
    - 卡片底部有"同意"和"拒绝"按钮
    - 用户点击按钮后，通过Webhook回调处理
  - 实现审批状态机：
    - PENDING → APPROVED / REJECTED
    - APPROVED → EXECUTING → COMPLETED / FAILED
    - 支持超时自动拒绝（24小时无操作）
  - 实现审批记录：
    - 所有审批操作写入approval_requests表
    - 记录审批人、审批时间、审批意见
  - 实现飞书审批通知：
    - 发起审批时通知相关人
    - 审批通过/拒绝后通知发起Agent
    - 超时即将到期时提醒

  **Must NOT do**:
  - 不允许无审批直接执行写入操作
  - 不允许审批通过后不记录日志

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 飞书交互卡片回调 + 状态机 + 数据库记录
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES（与Task 12并行）
  - **Parallel Group**: Wave 4 (with Task 12)
  - **Blocks**: Task 17
  - **Blocked By**: Task 8（飞书问答基础, Wave 3）

  **References**:

  **Pattern References**:
  - `构思.md:47` - "输出广告优化执行策略（交由人工确认），确认后通过亚马逊SP-API接口进行自动化调整"
  - 用户确认：全自动执行+人工审批

  **External References**:
  - 飞书卡片交互回调: https://open.feishu.cn/document/common-capabilities/message-card/message-cards-content/interaction-module — 按钮回调
  - 飞书卡片action: https://open.feishu.cn/document/server-docs/im-v1/message-card-callback — 回调配置

  **WHY Each Reference Matters**:
  - 交互卡片是实现飞书内"一键审批"的唯一方式
  - 状态机确保审批流程不会卡死或跳过

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 审批流程完整链路
    Tool: Bash (Python脚本 + curl)
    Preconditions: 飞书机器人+审批模块已就绪
    Steps:
      1. 创建一个测试审批请求
      2. 验证飞书群收到带"同意/拒绝"按钮的卡片
      3. 模拟点击"同意"按钮的Webhook回调
      4. 验证approval_requests表状态变为APPROVED
      5. 验证审批人和时间已记录
    Expected Result: 审批全链路通畅
    Failure Indicators: 卡片无按钮、回调处理失败、状态未更新
    Evidence: .sisyphus/evidence/task-13-approval-flow.txt

  Scenario: 审批超时自动拒绝
    Tool: Bash (Python脚本)
    Preconditions: 超时设置为10秒（测试用）
    Steps:
      1. 创建审批请求
      2. 等待15秒不操作
      3. 验证状态自动变为REJECTED
      4. 验证飞书收到超时通知
    Expected Result: 超时自动拒绝+通知
    Evidence: .sisyphus/evidence/task-13-approval-timeout.txt
  ```

  **Commit**: YES
  - Message: `feat(feishu): implement approval workflow with interactive cards and state machine`
  - Files: `src/feishu/approval.py`, `src/agents/core_agent/approval_manager.py`, `tests/test_approval.py`
  - Pre-commit: `pytest tests/test_approval.py --mock-external-apis`

- [x] 14. 选品分析Agent

  **What to do**:
  - 实现选品分析Agent核心逻辑（基于LangGraph）：
    - **数据采集节点**：调用卖家精灵MCP获取市场数据
      - 宠物用品类目热门关键词和趋势
      - 头部ASIN的销量、评分、价格、review数
      - 类目价格分布和竞争格局
    - **知识库检索节点**：从RAG系统获取运营方法论中的选品标准
    - **分析推理节点**：结合数据和方法论，使用LLM分析：
      - 市场空间和趋势判断
      - 竞品弱点分析（差评汇总、功能缺失）
      - 差异化机会识别
    - **报告生成节点**：输出结构化选品报告
      - 推荐候选产品/ASIN（≥3个）
      - 每个推荐附带：选品理由、市场数据支撑、风险提示、预估投入
      - 综合评分排序
  - 支持两种触发方式：
    - 定时触发（每周一10:00，通过调度器）
    - 手动触发（飞书指令或API调用）
  - 支持指定分析范围：
    - 默认：宠物用品全类目
    - 可指定子类目（如"牵引绳"、"狗项圈"）
    - 可指定竞品ASIN进行定向分析
  - 报告输出到：数据库 + 飞书多维表格 + 飞书群通知

  **Must NOT do**:
  - 不推荐亚马逊限制类目的产品
  - 不在推荐理由中编造数据（所有数据必须来自卖家精灵）
  - 不跳过知识库中的选品原则

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 核心业务Agent，涉及LangGraph多节点编排、数据采集、LLM分析、报告生成
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES（与Task 8, 15, 16, 20并行）
  - **Parallel Group**: Wave 3 (with Tasks 8, 15, 16, 20)
  - **Blocks**: Tasks 17, 19
  - **Blocked By**: Tasks 7（RAG, Wave 2）, 9（卖家精灵, Wave 2）, 10（LLM, Wave 2）, 11（调度器, Wave 2）

  **References**:

  **Pattern References**:
  - `构思.md:22-23` - 选品Agent的完整描述
  - `构思.md:19-20` - 品牌路径规划Agent给出的开发建议（Phase 2，Phase 1暂不依赖）
  - `构思.md:11` - "核心运营思路及价值观，所有AIagent都不能偏离这个原则"

  **External References**:
  - LangGraph Agent: https://python.langchain.com/docs/langgraph — Agent编排
  - 亚马逊产品限制类目列表: https://sellercentral.amazon.com/gp/help/G200164330 — 合规检查

  **WHY Each Reference Matters**:
  - LangGraph的Graph结构适合"采集→检索→分析→生成"的多步骤流程
  - 知识库中的选品原则是Agent的行为约束

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 选品分析完整运行
    Tool: Bash (Python脚本)
    Preconditions: RAG系统+卖家精灵模块+LLM封装已就绪
    Steps:
      1. python -c "from src.agents.selection_agent import run; result=run(category='pet_supplies', dry_run=True); print(result)"
      2. 验证返回≥3个候选产品
      3. 验证每个候选包含：ASIN/产品名、选品理由、市场数据、风险提示
      4. 验证运行时间<5分钟
      5. 验证agent_runs表新增运行记录
    Expected Result: 完整选品报告，数据来源可溯
    Failure Indicators: 候选数<3、理由无数据支撑、超时
    Evidence: .sisyphus/evidence/task-14-selection-run.json

  Scenario: 知识库原则遵循
    Tool: Bash (Python脚本)
    Preconditions: 知识库含选品方法论
    Steps:
      1. 查看选品Agent的系统Prompt
      2. 验证Prompt中引用了知识库检索结果
      3. 验证推荐理由中引用了运营方法论
    Expected Result: 选品决策遵循知识库原则
    Evidence: .sisyphus/evidence/task-14-kb-compliance.txt

  Scenario: 手动触发via飞书
    Tool: Bash (Python脚本)
    Preconditions: 飞书指令路由已配置
    Steps:
      1. 模拟飞书消息 "@机器人 选品分析 子类目=牵引绳"
      2. 验证Agent开始运行（飞书回复"选品分析已启动..."）
      3. 等待运行完成，验证飞书收到分析结果摘要
    Expected Result: 飞书触发→运行→结果回报全链路通畅
    Evidence: .sisyphus/evidence/task-14-feishu-trigger.txt
  ```

  **Commit**: YES
  - Message: `feat(agents): implement product selection analysis agent with LangGraph`
  - Files: `src/agents/selection_agent/`, `tests/test_selection_agent.py`
  - Pre-commit: `pytest tests/test_selection_agent.py --mock-external-apis`

- [x] 15. 飞书多维表格同步模块

  **What to do**:
  - 在飞书中创建多维表格（Bitable），设计表结构：
    - **选品记录表**：候选ASIN、产品名称、选品理由、市场数据、风险提示、评分、状态、分析日期
    - **Agent运行日志表**：Agent类型、运行状态、开始时间、结束时间、耗时、费用
    - **审批记录表**：审批类型、描述、状态、审批人、审批时间
    - **产品信息表**：SKU、产品名称、ASIN、状态、关键词（Phase 2扩充）
  - 实现数据库到飞书多维表格的单向同步：
    - 支持增量同步（只同步新增/修改的记录）
    - 每次同步记录同步日志
    - 同步失败自动重试
  - 实现同步触发方式：
    - Agent完成任务后自动触发同步
    - 定时全量同步（每日一次）
    - 手动触发
  - 遵守飞书API速率限制：
    - 批量写入（一次最多500条）
    - 请求间隔控制

  **Must NOT do**:
  - 不做飞书到数据库的反向同步（飞书是展示层，数据库是真实源）
  - 不在飞书中存储敏感数据（如API密钥）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 飞书Bitable API + 增量同步逻辑 + 速率限制处理
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES（与Task 8, 14, 16, 20并行）
  - **Parallel Group**: Wave 3 (with Tasks 8, 14, 16, 20)
  - **Blocks**: Tasks 17, 19
  - **Blocked By**: Task 5（飞书基础, Wave 1）

  **References**:

  **Pattern References**:
  - `构思.md:14` - "一部分数据需同步到飞书的多维表格，以便随时查看随时调用"
  - `构思.md:23` - "录入到数据库且同步到飞书多维表格"

  **External References**:
  - 飞书多维表格API: https://open.feishu.cn/document/server-docs/docs/bitable-v1/bitable-overview — Bitable文档
  - 飞书Bitable记录操作: https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/batch_create — 批量写入

  **WHY Each Reference Matters**:
  - 多维表格替代Phase 1的Web控制台，是团队查看数据的主要方式
  - 增量同步避免每次全量覆盖浪费API配额

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 数据同步到飞书
    Tool: Bash (Python脚本)
    Preconditions: 飞书多维表格已创建
    Steps:
      1. 往数据库插入3条选品记录
      2. python -c "from src.feishu.bitable_sync import sync_selection; sync_selection()"
      3. 查询飞书多维表格，验证3条记录已出现
    Expected Result: 数据库→飞书同步成功
    Failure Indicators: 记录缺失、字段不匹配
    Evidence: .sisyphus/evidence/task-15-bitable-sync.txt

  Scenario: 增量同步验证
    Tool: Bash (Python脚本)
    Preconditions: 已有3条已同步记录
    Steps:
      1. 新增2条数据库记录
      2. 运行同步
      3. 验证飞书多维表格总数=5，且只有2条是新同步的
    Expected Result: 增量同步正确，不重复
    Evidence: .sisyphus/evidence/task-15-incremental-sync.txt
  ```

  **Commit**: YES
  - Message: `feat(feishu): implement Feishu Bitable sync module for data display`
  - Files: `src/feishu/bitable_sync.py`, `tests/test_bitable_sync.py`
  - Pre-commit: `pytest tests/test_bitable_sync.py --mock-external-apis`

- [x] 16. 日志审计和紧急停机系统

  **What to do**:
  - 实现日志审计系统：
    - 所有Agent操作记录到audit_logs表
    - 每条记录包含：操作类型、操作者（Agent/人）、操作前状态、操作后状态、时间戳
    - 写入操作必须记录pre_state快照（支持回滚）
    - 日志不可修改（只能追加）
  - 实现紧急停机（Kill Switch）：
    - API端点：POST /api/system/pause-all
    - 飞书指令："@机器人 暂停所有"
    - 执行逻辑：
      1. 暂停所有定时任务
      2. 取消所有队列中的待执行任务
      3. 等待正在执行的任务完成（最长等待60秒后强制中断）
      4. 发送飞书通知"系统已暂停"
    - 恢复端点：POST /api/system/resume-all
    - 飞书指令："@机器人 恢复所有"
  - 实现系统健康检查：
    - GET /api/health — 返回各组件状态（DB/飞书/LLM/调度器）
    - 组件异常时自动发送飞书告警
  - 实现dry-run模式全局开关：
    - 环境变量 DRY_RUN=true 时，所有Agent只输出分析结果，不执行任何写入操作

  **Must NOT do**:
  - 不允许删除审计日志
  - 紧急停机不能有延迟超过10秒

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 审计日志+Kill Switch+健康检查+dry-run模式
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES（与Task 8, 14, 15, 20并行）
  - **Parallel Group**: Wave 3 (with Tasks 8, 14, 15, 20)
  - **Blocks**: Task 17
  - **Blocked By**: Tasks 3（项目骨架, Wave 1）, 11（调度器, Wave 2）

  **References**:

  **Pattern References**:
  - `构思.md:49-50` - "所有自动化动作都必须输出日志，保证可审计，可追溯，可回滚"

  **External References**:
  - SQLAlchemy事件监听: https://docs.sqlalchemy.org/en/20/core/event.html — 自动记录变更
  - FastAPI中间件: https://fastapi.tiangolo.com/tutorial/middleware/ — 请求日志

  **WHY Each Reference Matters**:
  - 审计日志是用户的核心需求——可审计、可追溯、可回滚
  - Kill Switch是Metis识别的关键安全护栏

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 审计日志完整性
    Tool: Bash (Python脚本)
    Preconditions: 审计系统已启动
    Steps:
      1. 执行一次选品Agent运行
      2. 查询audit_logs表
      3. 验证记录包含：action, actor, pre_state, post_state, created_at（与Task 2 Schema一致）
    Expected Result: 所有操作均有审计记录
    Evidence: .sisyphus/evidence/task-16-audit-log.txt

  Scenario: 紧急停机
    Tool: Bash (curl)
    Preconditions: 调度器有活跃任务
    Steps:
      1. curl -X POST http://localhost:8000/api/system/pause-all
      2. 验证返回 {"status": "paused", "tasks_paused": N}
      3. 验证所有定时任务已暂停
      4. 验证飞书收到"系统已暂停"通知
      5. curl -X POST http://localhost:8000/api/system/resume-all
      6. 验证定时任务恢复
    Expected Result: 停机和恢复均在10秒内完成
    Evidence: .sisyphus/evidence/task-16-kill-switch.txt

  Scenario: 健康检查
    Tool: Bash (curl)
    Preconditions: 系统已运行
    Steps:
      1. curl http://localhost:8000/api/health
      2. 验证返回各组件状态：{"db": "ok", "feishu": "ok", "llm": "ok", "scheduler": "ok"}
    Expected Result: 所有组件状态正常
    Evidence: .sisyphus/evidence/task-16-health-check.txt
  ```

  **Commit**: YES
  - Message: `feat(system): implement audit logging, kill switch, and health check`
  - Files: `src/utils/audit.py`, `src/utils/killswitch.py`, `src/api/system.py`, `tests/test_system.py`
  - Pre-commit: `pytest tests/test_system.py --mock-external-apis`

- [x] 17. 端到端集成测试 — 系统级验证

  **What to do**:
  - 创建集成测试套件 `tests/integration/` 目录结构
  - 编写端到端测试脚本 `tests/integration/test_e2e_flow.py`：
    - 测试流程1：文档上传 → 向量化 → 知识库问答 → 飞书回复（完整RAG链路）
    - 测试流程2：定时触发选品Agent → 调用卖家精灵Mock → 生成分析报告 → 写入Bitable → 飞书通知
    - 测试流程3：飞书发送指令 → 核心管理Agent分发 → 选品Agent执行 → 结果回传飞书
    - 测试流程4：每日自动汇报流程 → 汇总各模块状态 → 格式化报告 → 飞书群推送
  - 编写 `tests/integration/test_error_recovery.py`：
    - LLM API超时场景 → 验证重试机制 → 验证飞书错误告警
    - 数据库连接断开 → 验证重连机制 → 验证降级运行
    - 卖家精灵API异常 → 验证Mock数据降级 → 验证告警
    - 超出LLM每日预算 → 验证硬停机制 → 验证飞书通知
  - 编写 `tests/integration/conftest.py`：
    - 集成测试专用fixtures（Mock外部API、测试数据库、飞书Mock）
    - `@pytest.mark.integration` 标记
    - 测试前后自动清理数据库
  - 编写 `tests/integration/test_concurrent.py`：
    - 多个Agent同时运行场景
    - 并发飞书请求处理
    - 资源竞争测试（数据库连接池、LLM并发限制）
  - 确保所有集成测试可通过 `pytest tests/integration/ --mock-external-apis -v` 一键运行

  **Must NOT do**:
  - 不调用真实的外部API（飞书、卖家精灵、OpenAI）——全部Mock
  - 不修改已有的单元测试文件
  - 不引入额外的测试框架（只用pytest）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 端到端集成测试需要理解整个系统的交互流程，需要深度理解多模块协作
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES（与Task 19并行）
  - **Parallel Group**: Wave 5 (with Task 19)
  - **Blocks**: Task 18（部署）
  - **Blocked By**: Tasks 12（核心管理Agent, Wave 4）, 13（审批流程, Wave 4）, 14（选品Agent, Wave 3）, 15（飞书Bitable, Wave 3）, 16（审计系统, Wave 3）

  **References**:

  **Pattern References**:
  - `tests/` - 所有已有单元测试文件的结构和Mock模式
  - `src/agents/core_agent/daily_report.py` - 核心管理Agent的日报逻辑（测试流程3的关键——Agent分发和汇报）
  - `src/agents/selection_agent/` - 选品Agent的完整执行流程（测试流程2的关键——选品分析链路）
  - `src/knowledge_base/rag_engine.py` - RAG查询链路（测试流程1的关键——知识库问答）
  - `src/feishu/bot_handler.py` - 飞书消息处理和指令路由逻辑（所有流程的入口/出口）
  - `src/scheduler/jobs.py` - 定时任务配置（测试流程2和4的触发器）

  **External References**:
  - pytest fixtures作用域: https://docs.pytest.org/en/stable/how-to/fixtures.html — conftest.py的scope=session管理
  - pytest-asyncio: https://pytest-asyncio.readthedocs.io/ — 异步测试支持

  **WHY Each Reference Matters**:
  - 集成测试必须串联所有模块，每个Reference对应一个子系统的入口点
  - 测试需要复用各模块单元测试中已建立的Mock模式，保持一致性

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: RAG完整链路测试
    Tool: Bash (pytest)
    Preconditions: 数据库已初始化，知识库已有测试文档
    Steps:
      1. pytest tests/integration/test_e2e_flow.py::test_rag_full_pipeline -v --mock-external-apis
      2. 验证测试输出包含："PASSED"
      3. 验证日志包含完整链路：document_loaded → vectorized → query_received → context_retrieved → llm_generated → response_sent
    Expected Result: 测试通过，完整链路日志可追踪
    Failure Indicators: 任何FAILED或ERROR，链路日志断裂
    Evidence: .sisyphus/evidence/task-17-rag-e2e.txt

  Scenario: 选品Agent端到端流程
    Tool: Bash (pytest)
    Preconditions: Mock数据已配置
    Steps:
      1. pytest tests/integration/test_e2e_flow.py::test_selection_full_pipeline -v --mock-external-apis
      2. 验证生成了选品分析报告（包含>=3个候选产品）
      3. 验证Bitable Mock收到了写入请求
      4. 验证飞书Mock收到了通知消息
    Expected Result: 完整流程执行，所有模块正确串联
    Evidence: .sisyphus/evidence/task-17-selection-e2e.txt

  Scenario: 错误恢复测试
    Tool: Bash (pytest)
    Preconditions: 系统正常运行
    Steps:
      1. pytest tests/integration/test_error_recovery.py -v --mock-external-apis
      2. 验证LLM超时场景：重试3次后降级，飞书告警已发送
      3. 验证预算超限场景：LLM调用被阻止，飞书通知已发送
    Expected Result: 所有错误恢复测试通过
    Failure Indicators: 错误未被捕获、告警未发送、系统崩溃
    Evidence: .sisyphus/evidence/task-17-error-recovery.txt

  Scenario: 并发压力测试
    Tool: Bash (pytest)
    Preconditions: 系统正常运行
    Steps:
      1. pytest tests/integration/test_concurrent.py -v --mock-external-apis
      2. 验证5个并发飞书请求均正确处理
      3. 验证数据库连接池未耗尽
    Expected Result: 并发场景无死锁、无数据竞争
    Evidence: .sisyphus/evidence/task-17-concurrent.txt
  ```

  **Commit**: YES
  - Message: `test(integration): add end-to-end integration tests for all core workflows`
  - Files: `tests/integration/conftest.py`, `tests/integration/test_e2e_flow.py`, `tests/integration/test_error_recovery.py`, `tests/integration/test_concurrent.py`
  - Pre-commit: `pytest tests/integration/ --mock-external-apis -v`

- [x] 18. 云服务器部署与24/7运行配置

  **What to do**:
  - 创建 `deploy/` 目录结构：
    ```
    deploy/
    ├── docker/
    │   ├── Dockerfile          # Python 3.11 slim, 安装依赖, 配置健康检查
    │   ├── docker-compose.yml  # app + postgres + redis(可选) 一键启动
    │   └── .dockerignore
    ├── scripts/
    │   ├── setup-server.sh     # 一键服务器初始化（安装Docker/Docker Compose）
    │   ├── deploy.sh           # 一键部署/更新脚本
    │   ├── backup-db.sh        # 数据库备份脚本（每日cron）
    │   └── monitor.sh          # 简易监控脚本（检查进程+磁盘+内存）
    ├── nginx/
    │   └── nginx.conf          # 反向代理配置（HTTPS + WebSocket for Feishu）
    └── systemd/
        └── amazon-ai.service   # systemd服务文件（自动重启）
    ```
  - **Dockerfile**:
    - 基础镜像: `python:3.11-slim`
    - 多阶段构建：builder阶段安装依赖，runtime阶段仅复制必要文件
    - 健康检查: `HEALTHCHECK CMD curl -f http://localhost:8000/api/health`
    - 非root用户运行
  - **docker-compose.yml**:
    - `app` 服务: 挂载 `.env`，端口映射 8000
    - `postgres` 服务: pgvector镜像, 持久化volume, 不映射宿主机端口（仅通过Docker内部网络在容器间以5432通信，不暴露到宿主机）
    - `network`: 内部网络隔离（postgres仅对app容器可见）
    - 资源限制: app最大2GB内存, postgres最大1GB内存
  - **setup-server.sh**:
    - 检测操作系统（Ubuntu/CentOS）
    - 安装Docker和Docker Compose
    - 创建项目目录 `/opt/amazon-ai/`
    - 配置UFW防火墙（仅开放22, 80, 443）
    - 创建非root部署用户
  - **deploy.sh**:
    - git pull最新代码
    - docker-compose build --no-cache
    - docker-compose up -d
    - 等待健康检查通过
    - 发送飞书部署成功/失败通知
  - **backup-db.sh**:
    - pg_dump导出数据库
    - 压缩并保留最近7天备份
    - 超过7天自动删除
  - 创建 `.env.example` 更新版（包含所有必要环境变量和中文注释说明）
  - 创建 `docs/deployment-guide.md` — 纯中文、大白话、截图级别的部署指南：
    - 如何购买云服务器（推荐配置：AWS EC2 t3.medium 或阿里云ECS 2核4G）
    - 如何SSH连接服务器
    - 如何运行 setup-server.sh
    - 如何配置 .env
    - 如何运行 deploy.sh
    - 如何设置域名和HTTPS（可选）
    - 如何查看日志和监控
    - 常见问题排查

  **Must NOT do**:
  - 不使用Kubernetes（过于复杂，单机Docker Compose足够）
  - 不配置CI/CD流水线（Phase 1不需要）
  - 部署脚本不能硬编码任何密钥或IP地址
  - 不使用付费监控服务（用简单脚本+飞书告警）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 涉及Docker、Nginx、systemd、Shell脚本等多种运维技术，但不需要特别深度的推理
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO（Wave 6唯一任务）
  - **Parallel Group**: Wave 6（依赖集成测试通过）
  - **Blocks**: F1-F4（最终验证）
  - **Blocked By**: Task 17（集成测试通过, Wave 5）

  **References**:

  **Pattern References**:
  - `requirements.txt` - 当前依赖列表（Dockerfile中pip install）
  - `src/config.py` - 所有环境变量定义（.env.example模板来源）
  - `src/api/` - FastAPI入口点（Dockerfile CMD）
  - `src/utils/killswitch.py` - 健康检查端点（Docker HEALTHCHECK）

  **External References**:
  - Docker multi-stage builds: https://docs.docker.com/build/building/multi-stage/
  - pgvector Docker: https://hub.docker.com/r/pgvector/pgvector — 包含pgvector扩展的PostgreSQL镜像
  - Docker Compose health checks: https://docs.docker.com/compose/compose-file/05-services/#healthcheck
  - Nginx reverse proxy: https://nginx.org/en/docs/http/ngx_http_proxy_module.html

  **WHY Each Reference Matters**:
  - 用户代码零基础，部署必须一键化且文档详尽
  - Docker Compose让用户不需要手动管理多个服务
  - pgvector Docker镜像避免手动编译安装

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Docker本地构建与启动
    Tool: Bash (docker)
    Preconditions: Docker已安装
    Steps:
      1. docker-compose -f deploy/docker/docker-compose.yml build
      2. 验证构建成功，无ERROR
      3. docker-compose -f deploy/docker/docker-compose.yml up -d
      4. 等待30秒
      5. curl http://localhost:8000/api/health
      6. 验证返回 {"status": "healthy", ...}
    Expected Result: 所有容器运行正常，健康检查通过
    Failure Indicators: 构建失败、容器退出、健康检查超时
    Evidence: .sisyphus/evidence/task-18-docker-build.txt

  Scenario: 数据库持久化验证
    Tool: Bash (docker)
    Preconditions: docker-compose已启动
    Steps:
      1. 向数据库写入测试数据
      2. docker-compose down
      3. docker-compose up -d
      4. 查询测试数据是否存在
    Expected Result: 重启后数据完整保留
    Evidence: .sisyphus/evidence/task-18-db-persistence.txt

  Scenario: 备份脚本验证
    Tool: Bash (shell)
    Preconditions: PostgreSQL容器运行中
    Steps:
      1. bash deploy/scripts/backup-db.sh
      2. 验证备份文件已创建（检查文件大小>0）
      3. 验证备份文件名包含日期时间戳
    Expected Result: 备份文件成功创建
    Evidence: .sisyphus/evidence/task-18-backup.txt

  Scenario: .env.example完整性
    Tool: Bash (grep)
    Preconditions: .env.example已生成
    Steps:
      1. 读取src/config.py中所有os.environ/os.getenv调用
      2. 读取.env.example中所有变量定义
      3. 对比验证——config.py中的每个环境变量在.env.example中都有对应条目
    Expected Result: 100%环境变量覆盖，每个变量都有中文注释
    Failure Indicators: config.py中有变量在.env.example中缺失
    Evidence: .sisyphus/evidence/task-18-env-completeness.txt
  ```

  **Commit**: YES
  - Message: `chore(deploy): add Docker, deployment scripts, and deployment guide`
  - Files: `deploy/**`, `.env.example`, `docs/deployment-guide.md`
  - Pre-commit: `docker-compose -f deploy/docker/docker-compose.yml config`

- [x] 19. 团队使用手册与培训材料

  **What to do**:
  - 创建 `docs/user-guide/` 目录结构：
    ```
    docs/user-guide/
    ├── README.md                    # 使用手册首页（目录导航）
    ├── 01-快速开始.md               # 5分钟上手指南
    ├── 02-飞书机器人使用.md         # 飞书Bot所有命令说明
    ├── 03-知识库管理.md             # 如何上传/管理知识库文档
    ├── 04-选品Agent使用.md          # 选品功能详细说明
    ├── 05-每日报告说明.md           # 每日报告格式和自定义
    ├── 06-飞书多维表格.md           # 多维表格数据查看和筛选
    ├── 07-系统管理.md               # 紧急停机、日志查看、故障排查
    └── 08-常见问题FAQ.md            # 常见问题和解答
    ```
  - **编写原则**：
    - 全部中文，大白话，零代码术语
    - 每个操作配以飞书截图占位符 `![操作名称](screenshots/xxx.png)`
    - 每个命令先说"什么时候用"，再说"怎么用"，最后说"结果是什么"
    - FAQ来源于系统可能出现的真实问题
  - **01-快速开始.md** 核心内容：
    - 第一步：在飞书中找到"PUDIWIND运营助手"机器人
    - 第二步：发送"你好"验证连接
    - 第三步：发送"今日报告"查看系统状态
    - 第四步：发送"选品分析 宠物玩具"体验选品功能
  - **02-飞书机器人使用.md** 核心内容：
    - 列出所有支持的指令（问答、选品、报告、系统控制）
    - 每个指令格式 + 示例 + 预期返回
    - 群聊 vs 私聊的区别
    - @机器人的正确方式
  - **07-系统管理.md** 核心内容：
    - 紧急停机命令（飞书发送"紧急停止"）
    - 查看系统日志（简化命令）
    - 常见报错及解决方法
    - 如何联系技术支持（AI辅助排查流程）
  - 创建 `docs/user-guide/screenshots/` 空目录并添加 `.gitkeep`

  **Must NOT do**:
  - 不使用任何编程术语（API、数据库、容器等 → 用大白话替代）
  - 不写英文内容
  - 不假设用户有技术背景
  - 不写开发者文档（只写使用者文档）

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: 纯文档写作任务，需要面向非技术用户的清晰表达
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES（与Task 17并行）
  - **Parallel Group**: Wave 5 (with Task 17)
  - **Blocks**: None
  - **Blocked By**: Tasks 12（核心管理Agent, Wave 4）, 14（选品Agent, Wave 3）, 8（飞书Bot问答, Wave 3）, 15（Bitable, Wave 3）

  **References**:

  **Pattern References**:
  - `src/feishu/bot_handler.py` - 飞书Bot消息处理和指令路由入口（提取命令列表和格式）
  - `src/feishu/command_router.py` - 指令路由逻辑（理解用户输入→系统响应映射）
  - `src/agents/core_agent/daily_report.py` - 核心管理Agent的日报逻辑（理解日报内容和格式）
  - `src/agents/selection_agent/` - 选品Agent的输入输出格式（目录，理解选品功能范围）
  - `src/scheduler/jobs.py` - 定时任务列表（每日报告等定时功能说明）
  - `src/feishu/bitable_sync.py` - 多维表格同步模块（用户需知道哪些列是什么含义）

  **External References**:
  - 飞书机器人使用: https://www.feishu.cn/hc/zh-CN/articles/360049067831 — 用户端如何与机器人交互

  **WHY Each Reference Matters**:
  - 使用手册的每个章节都直接对应系统模块的用户接口
  - 必须从代码中提取真实的命令格式和返回格式，不能凭想象写

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 使用手册完整性验证
    Tool: Bash (Python脚本)
    Preconditions: 所有手册文件已创建
    Steps:
      1. 验证docs/user-guide/下有8个.md文件 + 1个screenshots目录
      2. 读取src/feishu/bot_handler.py中所有注册的命令（指令路由）
      3. 读取02-飞书机器人使用.md中提到的所有命令
      4. 对比验证——Bot中的每个命令在手册中都有说明
    Expected Result: 命令覆盖率100%，无遗漏
    Failure Indicators: Bot中存在手册未提及的命令
    Evidence: .sisyphus/evidence/task-19-coverage.txt

  Scenario: 零术语验证
    Tool: Bash (grep)
    Preconditions: 手册文件已创建
    Steps:
      1. grep -rn "API\|数据库\|容器\|Docker\|PostgreSQL\|向量\|embedding\|token\|endpoint" docs/user-guide/*.md
      2. 验证返回为空（无技术术语泄露）
      3. 如有匹配，检查是否在FAQ的"技术人员参考"区域
    Expected Result: 用户手册无技术术语（FAQ技术参考区除外）
    Evidence: .sisyphus/evidence/task-19-no-jargon.txt

  Scenario: 快速开始流程可执行性
    Tool: Bash (Python脚本)
    Preconditions: 系统已运行，飞书Bot在线
    Steps:
      1. 按照01-快速开始.md的步骤逐一执行（Mock飞书消息）
      2. 发送"你好" → 验证收到欢迎回复
      3. 发送"今日报告" → 验证收到报告
      4. 发送"选品分析 宠物玩具" → 验证收到分析结果
    Expected Result: 4步流程均可顺利完成
    Evidence: .sisyphus/evidence/task-19-quickstart.txt
  ```

  **Commit**: YES
  - Message: `docs(user-guide): add complete Chinese user guide for non-technical team`
  - Files: `docs/user-guide/**`
  - Pre-commit: `test -f docs/user-guide/01-快速开始.md`

- [x] 20. Mock数据准备与系统预填充

  **What to do**:
  - 创建 `data/mock/` 目录结构：
    ```
    data/mock/
    ├── knowledge_base/
    │   ├── sample_docs/           # 10篇示例运营文档（Markdown）
    │   │   ├── 亚马逊A9算法解读.md
    │   │   ├── 宠物用品选品方法论.md
    │   │   ├── Listing优化实战指南.md
    │   │   ├── 广告投放策略入门.md
    │   │   ├── 竞品分析框架.md
    │   │   ├── 库存管理最佳实践.md
    │   │   ├── 关键词研究方法.md
    │   │   ├── 产品定价策略.md
    │   │   ├── 评论管理与客户服务.md
    │   │   └── 品牌建设与推广.md
    │   └── expected_qa_pairs.json # 测试问答对（问题→预期答案关键词）
    ├── seller_sprite/
    │   ├── market_analysis.json   # 卖家精灵市场分析Mock数据
    │   ├── keyword_research.json  # 关键词研究Mock数据
    │   └── competitor_data.json   # 竞品数据Mock
    ├── amazon_sp_api/
    │   ├── product_catalog.json   # 商品目录Mock（PUDIWIND在售产品）
    │   ├── sales_reports.json     # 销售报告Mock（30天数据）
    │   ├── advertising_reports.json # 广告报告Mock
    │   └── inventory_status.json  # 库存状态Mock
    └── seed_database.py           # 一键初始化脚本（导入所有Mock数据到数据库）
    ```
  - **示例文档编写原则**:
    - 内容参考真实的亚马逊运营知识（但不复制任何版权内容）
    - 每篇500-1000字，包含实际可操作的方法论
    - 覆盖知识库RAG测试的主要场景
    - 用于验证RAG查询质量（RAGAS评估）
  - **Mock数据编写原则**:
    - 卖家精灵Mock：模拟真实API返回格式，包含宠物用品类目的合理数据
    - SP-API Mock：模拟真实Amazon响应格式，PUDIWIND品牌的虚拟产品数据
    - 销售数据：30天趋势（含节假日波动），日销量10-50单区间
    - 广告数据：ACoS 15%-35%区间，多组广告活动
  - **seed_database.py**:
    - 读取所有Mock数据文件
    - 初始化数据库表
    - 批量导入示例文档并触发向量化
    - 导入Mock商品和销售数据
    - 验证导入结果并打印统计
    - 支持 `--clean` 参数清空重建
  - 创建 `scripts/init-demo.sh` — 一键Demo初始化：
    - 运行seed_database.py
    - 触发一次知识库问答测试
    - 触发一次选品分析测试
    - 打印系统就绪状态

  **Must NOT do**:
  - Mock数据不得包含真实的个人信息或公司数据
  - 示例文档不得复制任何版权内容
  - 不生成超过合理范围的数据量（保持轻量，便于快速导入）
  - seed脚本不得修改production数据库配置

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 需要编写合理的业务Mock数据和初始化脚本，涉及多种数据格式
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES（与Task 8, 14, 15, 16并行）
  - **Parallel Group**: Wave 3 (with Tasks 8, 14, 15, 16)
  - **Blocks**: None
  - **Blocked By**: Tasks 4（文档预处理, Wave 1）, 7（知识库RAG, Wave 2）, 9（卖家精灵, Wave 2）

  **References**:

  **Pattern References**:
  - `src/db/models.py` - 数据库模型定义（Mock数据必须匹配Schema）
  - `src/knowledge_base/document_processor.py` - 文档处理格式要求（示例文档格式必须兼容）
  - `src/seller_sprite/client.py` - 卖家精灵API响应格式（Mock数据格式来源）
  - `src/amazon_api/mock.py` - SP-API Mock模块的响应格式（由Task 6创建）
  - `src/knowledge_base/rag_engine.py` - RAG查询格式（expected_qa_pairs的设计依据）

  **External References**:
  - Amazon SP-API数据格式: https://developer-docs.amazon.com/sp-api/docs/reports-api-v2021-06-30-reference — 报告数据结构参考
  - 宠物用品市场数据: 用于编写合理的市场Mock数据参考

  **WHY Each Reference Matters**:
  - 所有Mock数据必须与系统实际期望的数据格式完全一致，否则导入会失败
  - expected_qa_pairs用于RAGAS评估，必须基于示例文档的实际内容设计

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 数据库预填充完整性
    Tool: Bash (Python脚本)
    Preconditions: 数据库已初始化（空库）
    Steps:
      1. python data/mock/seed_database.py --clean
      2. 验证输出包含：documents_imported: 10, products_imported: N, sales_records: N
      3. 查询数据库验证各表行数
      4. 验证向量化已完成（documents表的embedding字段非空）
    Expected Result: 所有Mock数据成功导入，向量化完成
    Failure Indicators: 导入数量为0、向量化失败、Schema不匹配错误
    Evidence: .sisyphus/evidence/task-20-seed-database.txt

  Scenario: Mock数据格式验证
    Tool: Bash (Python脚本)
    Preconditions: Mock数据文件已创建
    Steps:
      1. 用jsonschema验证每个JSON Mock文件的格式
      2. 对比seller_sprite Mock数据的key与src/seller_sprite/client.py中解析的key
      3. 对比amazon_sp_api Mock数据的key与src/amazon_api/mock.py中解析的key
    Expected Result: 所有Mock数据格式与系统期望格式100%匹配
    Failure Indicators: 格式不匹配、缺少必需字段
    Evidence: .sisyphus/evidence/task-20-format-validation.txt

  Scenario: Demo初始化一键运行
    Tool: Bash (shell)
    Preconditions: 系统已运行（docker-compose up或本地运行）
    Steps:
      1. bash scripts/init-demo.sh
      2. 验证输出包含："知识库就绪"、"选品测试通过"、"系统就绪"
      3. 通过飞书Mock发送"什么是A9算法"
      4. 验证返回包含A9算法相关内容（来自示例文档）
    Expected Result: Demo环境一键就绪，知识库问答可用
    Evidence: .sisyphus/evidence/task-20-demo-init.txt

  Scenario: QA对测试（RAGAS预评估）
    Tool: Bash (Python脚本)
    Preconditions: 知识库已导入示例文档
    Steps:
      1. 读取data/mock/knowledge_base/expected_qa_pairs.json
      2. 对每个问题执行RAG查询
      3. 验证返回答案包含预期关键词
      4. 计算覆盖率（答案包含预期关键词的比例）
    Expected Result: 覆盖率>=80%（10个QA对中至少8个命中）
    Evidence: .sisyphus/evidence/task-20-qa-pairs.txt
  ```

  **Commit**: YES
  - Message: `feat(mock): add mock data, sample docs, and database seed script for demo`
  - Files: `data/mock/**`, `scripts/init-demo.sh`
  - Pre-commit: `python data/mock/seed_database.py --clean --dry-run`

---

## Final Verification Wave (MANDATORY — 所有实现任务完成后)

> 4个审查Agent并行运行。全部必须APPROVE。合并结果呈现给用户，获得明确"同意"后才能标记完成。
>
> **验证后不要自动继续。等待用户明确批准才能标记完成。**

- [x] F1. **计划合规审计** — `oracle`

  **What to do**:
  逐项阅读计划。对每个"Must Have"：验证实现存在（读取文件，curl端点，运行命令）。对每个"Must NOT Have"：搜索代码库中的禁止模式——如发现则拒绝并指出file:line。检查.sisyphus/evidence/中的证据文件。对比交付物与计划。

  **QA Scenarios:**

  ```
  Scenario: Must Have合规检查
    Tool: Bash (grep + curl + Python)
    Preconditions: 所有实现任务已完成
    Steps:
      1. 读取计划中"Must Have"列表（共8项）
      2. 逐项验证：
         - "知识库文档向量化和智能检索" → 验证src/knowledge_base/目录存在，运行 python -c "from src.knowledge_base.rag_engine import RAGEngine; print('OK')"
         - "飞书机器人问答和日报推送" → 验证src/feishu/目录存在，curl http://localhost:8000/api/health 返回feishu:ok
         - "选品分析（基于卖家精灵MCP）" → 验证src/agents/selection_agent/目录存在，运行 python -c "from src.agents.selection_agent import run; print('OK')"
         - "人工审批流程" → 验证src/feishu/approval.py存在
         - "所有操作的日志记录" → 验证src/utils/audit.py存在，查询audit_logs表有记录
         - "dry-run模式" → 运行 DRY_RUN=true python -c "from src.config import settings; assert settings.DRY_RUN"
         - "紧急停机按钮" → curl -X POST http://localhost:8000/api/system/pause-all 返回200
         - "LLM费用监控和上限" → 验证src/llm/cost_monitor.py存在
      3. 统计通过数/总数
    Expected Result: Must Have 8/8 全部通过
    Failure Indicators: 任何Must Have缺失
    Evidence: .sisyphus/evidence/F1-must-have-audit.txt

  Scenario: Must NOT Have违规检查
    Tool: Bash (grep)
    Preconditions: 代码库已完成
    Steps:
      1. grep -rn "硬编码.*key\|api_key\s*=\s*['\"]sk-\|password\s*=\s*['\"]" src/ --include="*.py" → 验证返回空（无硬编码密钥）
      2. grep -rn "web.*console\|flask.*admin\|django.*admin" src/ --include="*.py" → 验证无Web控制台代码
      3. grep -rn "create_listing\|update_price\|create_campaign" src/ --include="*.py" → 验证无SP-API写入操作
      4. grep -rn "generate_image\|dall-e\|stable.diffusion" src/ --include="*.py" → 验证无AI图片生成
      5. 检查.env文件不在git跟踪中（git status --porcelain | grep .env 应为空或.gitignore包含.env）
    Expected Result: Must NOT Have 7/7 全部合规（无违规代码）
    Failure Indicators: 任何grep返回非空结果
    Evidence: .sisyphus/evidence/F1-must-not-have-audit.txt

  Scenario: 证据文件完整性
    Tool: Bash (ls)
    Preconditions: 所有任务QA已执行
    Steps:
      1. ls -la .sisyphus/evidence/task-*.txt .sisyphus/evidence/task-*.json 2>/dev/null | wc -l → 验证证据文件数量≥40（20个任务×平均2个场景，包含.txt和.json两种格式）
      2. 验证已知的.json格式证据文件存在：task-4-preprocess-report.json, task-7-ragas-eval.json, task-14-selection-run.json
      3. 逐个检查所有证据文件大小>0（非空文件）：find .sisyphus/evidence/ -name "task-*" -empty → 应返回空
    Expected Result: 所有证据文件（.txt和.json）存在且非空
    Evidence: .sisyphus/evidence/F1-evidence-check.txt
  ```

  输出: `Must Have [N/8] | Must NOT Have [N/7] | Evidence [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **代码质量审查** — `unspecified-high`

  **What to do**:
  运行测试套件和代码质量检查。审查所有变更文件：查找硬编码密钥、空异常捕获、未使用的导入。检查AI过度工程。

  **QA Scenarios:**

  ```
  Scenario: 测试套件运行
    Tool: Bash (pytest)
    Preconditions: 所有代码已提交
    Steps:
      1. pytest tests/ --mock-external-apis -v 2>&1 | tee test-results.txt
      2. 从输出中提取：passed数、failed数、error数
      3. 验证failed=0且error=0
    Expected Result: 所有测试通过
    Failure Indicators: 任何FAILED或ERROR
    Evidence: .sisyphus/evidence/F2-test-results.txt

  Scenario: 代码质量扫描
    Tool: Bash (grep + Python)
    Preconditions: 代码库已完成
    Steps:
      1. grep -rn "as any\|@ts-ignore\|# type: ignore" src/ --include="*.py" → 记录类型抑制数量
      2. grep -rn "except:\s*$\|except Exception:\s*$" src/ --include="*.py" → 查找空异常捕获（后面无具体处理）
      3. grep -rn "console\.log\|print(" src/ --include="*.py" | grep -v "logger\|logging\|test_\|debug" → 查找非日志的print语句
      4. grep -rn "# TODO\|# FIXME\|# HACK" src/ --include="*.py" → 记录遗留TODO数量
      5. 统计：清洁文件数 vs 有问题文件数
    Expected Result: 空异常捕获=0，非日志print=0，TODO≤5
    Failure Indicators: 空异常捕获>0或非日志print>0
    Evidence: .sisyphus/evidence/F2-code-quality.txt

  Scenario: AI过度工程检查
    Tool: Bash (Python脚本)
    Preconditions: 代码库已完成
    Steps:
      1. 统计src/目录下每个.py文件的注释行占比
      2. 查找注释占比>40%的文件（过度注释嫌疑）
      3. 查找单文件超过300行的文件（可能过度抽象）
      4. 查找泛型命名：grep -rn "data\s*=\|result\s*=\|temp\s*=\|item\s*=" src/ 统计数量
    Expected Result: 无注释占比>40%的文件，泛型命名≤10处
    Evidence: .sisyphus/evidence/F2-ai-slop-check.txt
  ```

  输出: `Tests [N pass/0 fail] | Quality [N clean/N issues] | AI Slop [CLEAN/N issues] | VERDICT: APPROVE/REJECT`

- [x] F3. **实际QA验证** — `unspecified-high`

  **What to do**:
  从干净状态开始。执行每个任务的每个QA场景，测试跨任务集成和边缘情况。

  **QA Scenarios:**

  ```
  Scenario: 全场景回归执行
    Tool: Bash (pytest + curl + Python)
    Preconditions: 系统从docker-compose up干净启动，Mock数据已导入
    Steps:
      1. 按顺序执行所有Task的QA场景（从Task 1到Task 20）
      2. 每个场景记录：PASS/FAIL + 耗时 + 证据路径
      3. 统计通过率
    Expected Result: 场景通过率≥95%（允许≤2个非关键场景失败）
    Failure Indicators: 通过率<90%或任何关键路径场景失败
    Evidence: .sisyphus/evidence/F3-full-regression.txt

  Scenario: 跨任务集成验证
    Tool: Bash (Python脚本 + curl)
    Preconditions: 系统正常运行
    Steps:
      1. 完整流程1：飞书发消息"选品分析 宠物玩具" → 核心管理Agent接收 → 选品Agent执行 → 结果写入Bitable → 飞书回复结果摘要
         验证：飞书Mock收到完整回复，Bitable Mock收到写入请求
      2. 完整流程2：触发每日报告 → 汇总销售数据(Mock) + Agent状态 + 市场动态 → 格式化 → 飞书群推送
         验证：报告包含三个板块，时间戳正确
      3. 完整流程3：飞书发送审批请求 → 生成审批卡片 → 模拟点击"通过" → 执行后续动作
         验证：审批状态正确更新
    Expected Result: 3个跨任务集成流程全部通过
    Failure Indicators: 任何流程中断或数据丢失
    Evidence: .sisyphus/evidence/F3-integration.txt

  Scenario: 边缘情况测试
    Tool: Bash (curl + Python)
    Preconditions: 系统正常运行
    Steps:
      1. 空消息测试：飞书发送空字符串 → 验证返回友好提示而非崩溃
      2. 超长消息测试：发送10000字消息 → 验证截断处理正确
      3. 并发测试：同时发送10条飞书消息 → 验证全部得到回复，无丢失
      4. LLM超时模拟：设置LLM超时=1ms → 验证重试后返回降级回复
      5. 数据库断连模拟：停止PostgreSQL → 验证健康检查报告异常 → 重启后自动恢复
    Expected Result: 所有边缘情况优雅处理，无崩溃
    Evidence: .sisyphus/evidence/F3-edge-cases.txt
  ```

  输出: `Scenarios [N/N pass] | Integration [3/3] | Edge Cases [5 tested] | VERDICT: APPROVE/REJECT`

- [x] F4. **范围保真度检查** — `deep`

  **What to do**:
  对每个任务：读取"What to do"，读取实际diff。验证1:1对应——规格中的一切都已实现（无遗漏），规格之外的一切都未实现（无蔓延）。检查"Must NOT do"合规性。

  **QA Scenarios:**

  ```
  Scenario: 任务-实现一致性审计
    Tool: Bash (git + Python脚本)
    Preconditions: 所有任务已提交
    Steps:
      1. 对每个Task (1-20)：
         a. 从计划中提取"What to do"列表
         b. 从git log中找到对应commit
         c. 读取commit的diff，列出变更文件
         d. 对比：计划要求的每项是否都有对应实现 → 标记"实现/缺失"
         e. 对比：diff中是否有计划未提到的变更 → 标记"计划内/范围外"
      2. 统计：合规任务数/总任务数
    Expected Result: 20/20任务合规（无缺失实现，无范围外变更）
    Failure Indicators: 任何任务有缺失或范围外变更
    Evidence: .sisyphus/evidence/F4-scope-audit.txt

  Scenario: Must NOT Do合规检查
    Tool: Bash (grep)
    Preconditions: 代码库已完成
    Steps:
      1. 对每个任务的"Must NOT do"列表，逐条验证：
         - Task 1: grep确认数据库端口未暴露到公网（docker-compose.yml中postgres服务无ports字段，仅通过内部网络通信）
         - Task 7: grep确认无本地Embedding模型引用
         - Task 14: grep确认无直接修改Amazon数据的代码
         - Task 16: grep确认无删除审计日志的代码
         - Task 18: grep确认部署脚本无硬编码IP或密钥
         - Task 19: grep确认用户手册无技术术语
      2. 统计合规条目数/总条目数
    Expected Result: 所有Must NOT Do条目合规
    Evidence: .sisyphus/evidence/F4-must-not-do.txt

  Scenario: 跨任务文件污染检查
    Tool: Bash (git)
    Preconditions: 所有commit已提交
    Steps:
      1. 对每个Task的commit：
         a. 列出变更文件列表
         b. 检查是否有文件同时出现在多个Task的commit中
         c. 如有，验证是否合理（如config.py被多个任务修改是合理的）
      2. 标记：合理共享 vs 不合理污染
    Expected Result: 无不合理的跨任务文件污染
    Evidence: .sisyphus/evidence/F4-contamination.txt
  ```

  输出: `Tasks [N/20 compliant] | Must NOT Do [N/N] | Contamination [CLEAN/N issues] | VERDICT: APPROVE/REJECT`

---

## Commit Strategy

- **T1**: `chore(infra): provision cloud server and configure base environment` — server configs
- **T2**: `feat(db): initialize PostgreSQL with pgvector and schema migrations` — schema files, migration scripts
- **T3**: `chore(project): setup Python project skeleton with config management` — pyproject.toml, src/, tests/
- **T4**: `feat(kb): preprocess and clean knowledge base documents` — preprocessing scripts, cleaned docs
- **T5**: `feat(feishu): create Feishu bot app and basic webhook handler` — feishu module
- **T6**: `docs(api): document Amazon SP-API application steps` — documentation
- **T7**: `feat(kb): implement RAG system with pgvector embeddings` — rag module, embedding pipeline
- **T8**: `feat(feishu): implement Q&A bot connected to RAG system` — bot handler
- **T9**: `feat(data): integrate Seller Sprite MCP data collection` — seller_sprite module
- **T10**: `feat(llm): implement LLM call wrapper with cost monitoring` — llm module
- **T11**: `feat(scheduler): implement task scheduling engine` — scheduler module
- **T12**: `feat(agents): implement core management agent daily report` — core_agent module
- **T13**: `feat(feishu): implement approval workflow with interactive cards` — approval module
- **T14**: `feat(agents): implement product selection analysis agent` — selection_agent module
- **T15**: `feat(feishu): implement Feishu Bitable sync module` — bitable module
- **T16**: `feat(system): implement audit logging and kill switch` — audit, killswitch modules
- **T17**: `test(e2e): add end-to-end integration tests` — e2e test files
- **T18**: `chore(deploy): configure cloud deployment and systemd services` — deployment configs
- **T19**: `docs(guide): create team user guide and training materials` — docs/
- **T20**: `feat(data): prepare mock data for system testing` — mock data files

---

## Success Criteria

### 验证命令
```bash
# 知识库RAG质量
python tests/eval_rag.py --golden-dataset tests/golden_qa.json
# Expected: faithfulness >= 0.85, context_precision >= 0.80

# 飞书机器人响应
python tests/test_feishu_qa.py --send-query "什么是A9算法"
# Expected: response within 5s, contains relevant knowledge base content

# 每日报告定时触发
python tests/test_daily_report.py --mock-schedule
# Expected: report generated with sales_summary, agent_status, market_brief sections

# 选品Agent完整运行
python tests/test_selection_agent.py --mode dry-run
# Expected: >=3 candidate products with rationale, <5min runtime

# 飞书多维表格同步
python tests/test_bitable_sync.py --verify
# Expected: Bitable rows match DB records

# 紧急停机
curl -X POST http://localhost:8000/api/system/pause-all
# Expected: all scheduled tasks paused, Feishu notification sent

# 全量测试
pytest tests/ --mock-external-apis -v
# Expected: all tests pass
```

### 最终检查清单
- [ ] 所有"Must Have"均已实现
- [ ] 所有"Must NOT Have"均未出现
- [ ] 所有测试通过
- [ ] 知识库RAGAS评分达标
- [ ] 飞书机器人可正常问答
- [ ] 每日报告可自动发送
- [ ] 选品分析可输出结果
- [ ] 紧急停机功能可用
- [ ] 所有API密钥在.env中，非硬编码
- [ ] dry-run模式所有Agent可用
- [ ] 日志审计系统可用

---

# Phase 2：系统优化 + 新Agent开发（第2-3个月）

## Phase 2 TL;DR

> **目标**：基于Phase 1的基础，引入架构优化（Rate Limiter、RAG增强、LLM缓存）+ 开发新Agent（竞品调研、用户画像、Listing文案、广告监控）+ 接入亚马逊SP-API正式环境。
>
> **优化项来源**：参考多Agent全流程架构方案，取其精髓：
> - Rate Limit Controller（防止API封禁）
> - RAG元数据增强（提高检索精度）
> - LLM响应缓存（降低Token成本）
> - JSON Schema输出校验（降低解析错误）
> - 决策状态机（可追溯、可回滚）
> - Policy Engine规则引擎（业务硬约束）

---

## Phase 2 Work Objectives

### 核心目标
1. **架构优化**：引入限流、缓存、规则引擎，提升系统稳定性和成本效率
2. **新Agent开发**：竞品调研、用户画像、Listing文案、广告监控
3. **SP-API接入**：从Mock数据切换到真实亚马逊数据

### 具体交付物
1. **Rate Limit Controller**：统一API限流，支持优先级队列
2. **RAG元数据增强**：文档按策略单元切分，支持版本和生效日期
3. **LLM响应缓存**：相同输入哈希命中缓存，降低30%+ Token成本
4. **JSON Schema校验**：LLM输出强制结构化，降低解析错误
5. **决策状态机**：Draft→Approved→Executing→Succeeded/Failed→RolledBack
6. **Policy Engine**：业务规则硬约束（预算上限、变动幅度等）
7. **竞品调研Agent**：分析竞品价格、评分、Review关键词
8. **用户画像Agent**：订单/评价/搜索词分析，输出人群标签
9. **Listing文案Agent**：生成标题/五点描述/广告文案
10. **广告监控Agent**：ACoS/ROAS监控，异常告警

### Must Have（Phase 2）
- Rate Limit Controller + 动态优先级
- LLM响应缓存（Redis）
- JSON Schema输出校验
- 决策状态机 + decisions表
- 竞品调研Agent基础版
- SP-API正式环境读取（只读，不写入）

### Must NOT Have（Phase 2护栏）
- ❌ 不做SP-API写入操作（调价、上架、广告调整留到Phase 3）
- ❌ 不引入Kubernetes（保持Docker Compose）
- ❌ 不引入Celery（保持APScheduler）
- ❌ 不引入Prometheus/Grafana（保持飞书告警）
- ❌ 不引入Neo4j（保持pgvector）

---

## Phase 2 TODOs

### Wave 1：架构优化基础设施（可并行）

- [ ] 21. Rate Limit Controller 统一限流模块

  **What to do**:
  - 创建 `src/utils/rate_limiter.py`：
    - 令牌桶算法实现
    - 支持按API组、账号、优先级维度限流
    - 优先级权重：critical=1.0, normal=0.6, batch=0.3
  - 创建 `src/utils/api_priority.py`：
    - 定义API调用优先级枚举
    - 风控/紧急调价 > 广告执行 > 市场调研
  - 集成到现有API调用点：
    - `src/seller_sprite/client.py`
    - `src/llm/client.py`
    - 未来的SP-API客户端
  - 添加限流指标到审计日志

  **Must NOT do**:
  - 不引入Redis（Phase 2用内存+数据库，Phase 3再考虑Redis）
  - 不做分布式限流（单机足够）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with 22, 23, 24)
  - **Blocks**: 25, 26, 27
  - **Blocked By**: None

  **References**:
  - `src/llm/client.py` - 现有LLM调用点
  - `src/seller_sprite/client.py` - 现有卖家精灵调用点
  - `src/utils/audit.py` - 审计日志模式

  **Acceptance Criteria**:
  - [ ] 令牌桶算法正确实现，支持burst
  - [ ] 优先级队列正确排序
  - [ ] 限流触发时返回429或排队等待
  - [ ] 审计日志记录限流事件

  **QA Scenarios**:
  ```
  Scenario: 限流触发验证
    Tool: Bash (pytest)
    Steps:
      1. 连续发送100个低优先级请求
      2. 验证部分请求被限流（429或延迟）
      3. 发送1个高优先级请求
      4. 验证高优先级请求优先处理
    Expected Result: 高优先级请求在低优先级之前完成
    Evidence: .sisyphus/evidence/task-21-rate-limit.txt
  ```

  **Commit**: YES
  - Message: `feat(infra): add rate limit controller with priority queue`

- [ ] 22. LLM响应缓存模块

  **What to do**:
  - 创建 `src/llm/cache.py`：
    - 输入哈希计算（prompt + context + model）
    - 缓存存储（先用数据库，预留Redis接口）
    - TTL过期策略（默认24小时）
    - 缓存命中率统计
  - 创建数据库表 `llm_cache`：
    - cache_key (hash)
    - prompt_hash
    - response_json
    - model
    - created_at
    - expires_at
    - hit_count
  - 修改 `src/llm/client.py`：
    - 调用前检查缓存
    - 调用后写入缓存
    - 缓存命中时记录审计日志
  - 添加缓存统计到日报

  **Must NOT do**:
  - 不缓存带有实时数据的查询（如"今日销量"）
  - 不缓存超过1MB的响应

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with 21, 23, 24)
  - **Blocks**: 25, 26
  - **Blocked By**: None

  **References**:
  - `src/llm/client.py` - 现有LLM客户端
  - `src/llm/cost_monitor.py` - 费用监控模式
  - `alembic/` - 数据库迁移

  **Acceptance Criteria**:
  - [ ] 相同输入第二次调用命中缓存
  - [ ] 缓存命中率可查询
  - [ ] 过期缓存自动清理
  - [ ] 缓存节省的Token数可统计

  **QA Scenarios**:
  ```
  Scenario: 缓存命中验证
    Tool: Bash (pytest)
    Steps:
      1. 发送查询A，记录耗时T1和Token数
      2. 再次发送相同查询A，记录耗时T2和Token数
      3. 验证T2 << T1（缓存命中无LLM调用）
      4. 验证第二次Token数=0
    Expected Result: 缓存命中，Token消耗为0
    Evidence: .sisyphus/evidence/task-22-llm-cache.txt
  ```

  **Commit**: YES
  - Message: `feat(llm): add response caching with hash-based lookup`

- [ ] 23. JSON Schema输出校验模块

  **What to do**:
  - 创建 `src/llm/schema_validator.py`：
    - 定义常用输出Schema（选品结果、日报、广告策略等）
    - Pydantic模型定义
    - 校验失败时的重试逻辑（最多2次）
  - 创建 `src/llm/schemas/`目录：
    - `selection_result.py` - 选品结果Schema
    - `daily_report.py` - 日报Schema
    - `ad_strategy.py` - 广告策略Schema（预留）
  - 修改现有Agent输出：
    - `src/agents/selection_agent/` - 使用Schema校验
    - `src/agents/core_agent/daily_report.py` - 使用Schema校验
  - 校验失败时记录到审计日志

  **Must NOT do**:
  - 不强制所有LLM调用都用Schema（仅结构化输出场景）
  - Schema校验失败不应阻塞整个流程（降级为原始输出）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with 21, 22, 24)
  - **Blocks**: 25, 26, 27
  - **Blocked By**: None

  **References**:
  - `src/agents/selection_agent/prompts.py` - 现有Prompt
  - `src/agents/core_agent/daily_report.py` - 日报输出

  **Acceptance Criteria**:
  - [ ] Pydantic Schema定义完整
  - [ ] 校验成功时输出符合Schema
  - [ ] 校验失败时自动重试
  - [ ] 重试2次仍失败时降级处理

  **QA Scenarios**:
  ```
  Scenario: Schema校验与重试
    Tool: Bash (pytest)
    Steps:
      1. 模拟LLM返回不符合Schema的输出
      2. 验证触发重试
      3. 第二次返回正确格式
      4. 验证最终输出符合Schema
    Expected Result: 重试后输出符合Schema
    Evidence: .sisyphus/evidence/task-23-schema-validation.txt
  ```

  **Commit**: YES
  - Message: `feat(llm): add JSON schema validation with Pydantic`

- [ ] 24. RAG元数据增强

  **What to do**:
  - 修改 `src/knowledge_base/models.py`：
    - 添加元数据字段：doc_type, category, version, effective_date, expires_date, priority
  - 修改 `src/knowledge_base/preprocessor.py`：
    - 支持从文档提取/推断元数据
    - 支持按"策略单元"切分（不仅仅是固定长度）
  - 修改 `src/knowledge_base/rag_engine.py`：
    - search()方法支持元数据过滤
    - 先按元数据过滤，再语义检索
  - 创建Alembic迁移脚本
  - 重新处理现有知识库文档（添加元数据）

  **Must NOT do**:
  - 不删除现有文档（增量更新元数据）
  - 不改变向量维度

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with 21, 22, 23)
  - **Blocks**: 25, 26, 27, 28
  - **Blocked By**: None

  **References**:
  - `src/knowledge_base/rag_engine.py` - 现有RAG引擎
  - `src/knowledge_base/models.py` - 现有数据模型
  - `data/knowledge_base/` - 知识库文档

  **Acceptance Criteria**:
  - [ ] 元数据字段添加到数据库
  - [ ] 文档处理时提取元数据
  - [ ] 检索时支持元数据过滤
  - [ ] 过滤后检索精度提升

  **QA Scenarios**:
  ```
  Scenario: 元数据过滤检索
    Tool: Bash (pytest)
    Steps:
      1. 插入两篇文档：A(category=广告), B(category=选品)
      2. 查询"如何优化广告"，过滤category=广告
      3. 验证只返回文档A
    Expected Result: 元数据过滤生效
    Evidence: .sisyphus/evidence/task-24-rag-metadata.txt
  ```

  **Commit**: YES
  - Message: `feat(rag): add metadata filtering and strategy-based chunking`

### Wave 2：决策追踪与规则引擎（依赖Wave 1）

- [ ] 25. 决策状态机与decisions表

  **What to do**:
  - 创建数据库表 `decisions`：
    - id, decision_type, agent_name, input_summary
    - status (draft/review_required/approved/executing/succeeded/failed/rolled_back)
    - llm_response_json, validated_output_json
    - created_at, approved_at, executed_at, completed_at
    - approved_by, rollback_reason
  - 创建数据库表 `decision_outcomes`：
    - decision_id, outcome_type, metrics_json
    - created_at
  - 创建 `src/decisions/state_machine.py`：
    - 状态转换逻辑
    - 状态变更事件发布
  - 创建 `src/decisions/manager.py`：
    - 创建决策、更新状态、记录结果
  - 集成到现有Agent：
    - 选品Agent输出时创建decision记录
    - 审批流程更新decision状态

  **Must NOT do**:
  - 不自动执行（Phase 2仍需人工审批）
  - 不实现自动回滚（Phase 3）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with 26)
  - **Blocks**: 27, 28, 29, 30
  - **Blocked By**: 21, 22, 23, 24

  **References**:
  - `src/feishu/approval.py` - 现有审批流程
  - `src/utils/audit.py` - 审计日志模式
  - `alembic/` - 数据库迁移

  **Acceptance Criteria**:
  - [ ] decisions表创建成功
  - [ ] 状态机转换正确
  - [ ] Agent输出自动创建decision
  - [ ] 审批后状态更新

  **QA Scenarios**:
  ```
  Scenario: 决策生命周期追踪
    Tool: Bash (pytest)
    Steps:
      1. 触发选品Agent
      2. 验证创建decision记录(status=draft)
      3. 触发审批
      4. 验证状态变为approved
      5. 查询decision历史
    Expected Result: 完整状态流转记录
    Evidence: .sisyphus/evidence/task-25-decision-tracking.txt
  ```

  **Commit**: YES
  - Message: `feat(decisions): add decision state machine and tracking`

- [ ] 26. Policy Engine规则引擎

  **What to do**:
  - 创建 `src/policy/engine.py`：
    - 规则定义（预算上限、变动幅度、毛利下限等）
    - 规则评估
    - 违规时的处理（拒绝/告警/降级）
  - 创建 `src/policy/rules/`目录：
    - `budget_rules.py` - 预算相关规则
    - `pricing_rules.py` - 调价相关规则（预留Phase 3）
    - `ad_rules.py` - 广告相关规则（预留Phase 3）
  - 创建数据库表 `policy_rules`：
    - rule_name, rule_type, threshold_json
    - enabled, priority
    - created_at, updated_at
  - 集成到决策流程：
    - decision创建时评估规则
    - 违规时阻止状态转换

  **Must NOT do**:
  - 规则不能硬编码（必须可配置）
  - 不做复杂的规则DSL（简单JSON配置即可）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with 25)
  - **Blocks**: 27, 28, 29, 30
  - **Blocked By**: 21, 22, 23, 24

  **References**:
  - `src/llm/cost_monitor.py` - 现有费用上限模式
  - `src/decisions/` - 决策模块

  **Acceptance Criteria**:
  - [ ] 规则可通过数据库配置
  - [ ] 规则评估正确
  - [ ] 违规时阻止执行
  - [ ] 违规记录到审计日志

  **QA Scenarios**:
  ```
  Scenario: 规则引擎阻止违规决策
    Tool: Bash (pytest)
    Steps:
      1. 配置规则：日预算上限=100
      2. 创建决策：请求预算=150
      3. 验证规则引擎拒绝
      4. 查看审计日志
    Expected Result: 决策被拒绝，记录违规原因
    Evidence: .sisyphus/evidence/task-26-policy-engine.txt
  ```

  **Commit**: YES
  - Message: `feat(policy): add rule engine with configurable policies`

### Wave 3：新Agent开发（依赖Wave 2）

- [ ] 27. 竞品调研Agent

  **What to do**:
  - 创建 `src/agents/competitor_agent/`目录：
    - `__init__.py`
    - `analyzer.py` - 竞品分析核心逻辑
    - `prompts.py` - LLM提示词
    - `schemas.py` - 输出Schema
  - 功能实现：
    - 输入：目标ASIN
    - 分析：竞品价格带、评分趋势、Review关键词
    - 输出：竞品画像JSON（符合Schema）
  - 数据源：
    - 卖家精灵MCP（已有）
    - 未来接入SP-API
  - 集成：
    - 飞书命令：`/competitor asin=B0...`
    - 输出到飞书多维表格

  **Must NOT do**:
  - 不爬取亚马逊页面（只用API）
  - 不存储竞品敏感数据超过30天

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with 28, 29)
  - **Blocks**: 30, 31
  - **Blocked By**: 25, 26

  **References**:
  - `src/agents/selection_agent/` - 现有Agent模式
  - `src/seller_sprite/client.py` - 卖家精灵客户端
  - `src/llm/schemas/` - Schema定义

  **Acceptance Criteria**:
  - [ ] 输入ASIN返回竞品分析
  - [ ] 输出符合JSON Schema
  - [ ] 集成飞书命令
  - [ ] 结果写入多维表格

  **QA Scenarios**:
  ```
  Scenario: 竞品分析完整流程
    Tool: Bash (pytest + curl)
    Steps:
      1. 调用 /competitor asin=B0EXAMPLE
      2. 验证返回竞品画像
      3. 验证Schema符合
      4. 验证写入Bitable
    Expected Result: 完整竞品分析报告
    Evidence: .sisyphus/evidence/task-27-competitor-agent.txt
  ```

  **Commit**: YES
  - Message: `feat(agents): add competitor research agent`

- [ ] 28. 用户画像Agent

  **What to do**:
  - 创建 `src/agents/persona_agent/`目录：
    - `__init__.py`
    - `analyzer.py` - 画像分析核心逻辑
    - `prompts.py` - LLM提示词
    - `schemas.py` - 输出Schema
  - 功能实现：
    - 输入：ASIN或产品类目
    - 分析：Review文本、Q&A、搜索词
    - 输出：人群标签、痛点地图、购买触发词
  - 数据源：
    - 知识库（运营文档）
    - 卖家精灵MCP
  - 集成：
    - 飞书命令：`/persona category=宠物玩具`

  **Must NOT do**:
  - 不存储个人可识别信息（PII）
  - 不做实时画像（批处理即可）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with 27, 29)
  - **Blocks**: 30
  - **Blocked By**: 25, 26, 24

  **References**:
  - `src/knowledge_base/rag_engine.py` - RAG检索
  - `src/agents/selection_agent/` - Agent模式

  **Acceptance Criteria**:
  - [ ] 输出人群标签列表
  - [ ] 输出痛点地图
  - [ ] 输出购买触发词
  - [ ] 结果可追溯到原始数据

  **QA Scenarios**:
  ```
  Scenario: 用户画像生成
    Tool: Bash (pytest)
    Steps:
      1. 调用 /persona category=宠物玩具
      2. 验证返回人群标签
      3. 验证痛点地图非空
      4. 验证触发词列表
    Expected Result: 完整用户画像
    Evidence: .sisyphus/evidence/task-28-persona-agent.txt
  ```

  **Commit**: YES
  - Message: `feat(agents): add user persona analysis agent`

- [ ] 29. Listing文案Agent

  **What to do**:
  - 创建 `src/agents/listing_agent/`目录：
    - `__init__.py`
    - `generator.py` - 文案生成核心逻辑
    - `prompts.py` - LLM提示词
    - `schemas.py` - 输出Schema
    - `compliance.py` - 合规词检查
  - 功能实现：
    - 输入：产品信息 + 用户画像 + 竞品差异
    - 输出：标题、五点描述、后台关键词、广告文案
    - 合规检查：禁用词、敏感词过滤
  - 集成：
    - 飞书命令：`/listing generate asin=B0...`
    - 输出到飞书文档（可编辑）

  **Must NOT do**:
  - 不自动上传到亚马逊（Phase 3）
  - 不生成图片（Phase 3）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with 27, 28)
  - **Blocks**: 30
  - **Blocked By**: 25, 26, 27, 28

  **References**:
  - `src/agents/persona_agent/` - 用户画像输入
  - `src/agents/competitor_agent/` - 竞品差异输入
  - `src/knowledge_base/` - 运营知识库

  **Acceptance Criteria**:
  - [ ] 生成完整Listing文案
  - [ ] 合规词检查通过
  - [ ] 输出符合Schema
  - [ ] 可导出到飞书文档

  **QA Scenarios**:
  ```
  Scenario: Listing文案生成
    Tool: Bash (pytest)
    Steps:
      1. 准备产品信息+画像+竞品数据
      2. 调用 /listing generate
      3. 验证标题、五点、关键词非空
      4. 验证合规检查通过
    Expected Result: 完整Listing文案
    Evidence: .sisyphus/evidence/task-29-listing-agent.txt
  ```

  **Commit**: YES
  - Message: `feat(agents): add listing copywriting agent`

### Wave 4：广告与SP-API（依赖Wave 3）

- [ ] 30. 广告监控Agent

  **What to do**:
  - 创建 `src/agents/ad_monitor_agent/`目录：
    - `__init__.py`
    - `monitor.py` - 广告指标监控
    - `alerts.py` - 异常告警
    - `prompts.py` - LLM提示词
    - `schemas.py` - 输出Schema
  - 功能实现：
    - 监控指标：ACoS、ROAS、CTR、CVR、花费
    - 异常检测：指标偏离阈值告警
    - 建议生成：基于知识库RAG生成优化建议
  - 集成：
    - 定时任务：每小时检查一次
    - 异常时飞书告警
    - 日报中包含广告摘要

  **Must NOT do**:
  - 不自动调整广告（Phase 3）
  - 不修改预算（Phase 3）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4
  - **Blocks**: 31
  - **Blocked By**: 25, 26, 27, 24

  **References**:
  - `src/scheduler/jobs.py` - 定时任务
  - `src/knowledge_base/rag_engine.py` - 知识库检索
  - `src/feishu/bot_handler.py` - 飞书通知

  **Acceptance Criteria**:
  - [ ] 定时拉取广告指标
  - [ ] 异常时触发告警
  - [ ] 生成优化建议
  - [ ] 建议基于知识库有据可查

  **QA Scenarios**:
  ```
  Scenario: 广告异常告警
    Tool: Bash (pytest)
    Steps:
      1. 模拟ACoS=50%（超过阈值30%）
      2. 触发监控检查
      3. 验证飞书收到告警
      4. 验证告警包含优化建议
    Expected Result: 告警触发且建议合理
    Evidence: .sisyphus/evidence/task-30-ad-monitor.txt
  ```

  **Commit**: YES
  - Message: `feat(agents): add advertising monitoring agent`

- [ ] 31. 亚马逊SP-API正式接入（只读）

  **What to do**:
  - 创建 `src/amazon_sp_api/`目录：
    - `__init__.py`
    - `client.py` - SP-API客户端封装
    - `auth.py` - OAuth认证
    - `reports.py` - 报告API
    - `catalog.py` - 商品目录API
    - `orders.py` - 订单API（只读）
  - 功能实现：
    - OAuth 2.0 认证流程
    - 自动Token刷新
    - 报告请求与下载
    - 集成Rate Limit Controller
  - 替换Mock数据：
    - 选品Agent：真实销量数据
    - 日报：真实订单数据
    - 广告监控：真实广告数据

  **Must NOT do**:
  - 不调用写入API（createListing, updatePrice等）
  - 不存储完整订单详情（只存储聚合数据）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4 (after 30)
  - **Blocks**: Phase 2 Final
  - **Blocked By**: 21, 30

  **References**:
  - `src/seller_sprite/client.py` - 现有API客户端模式
  - `src/utils/rate_limiter.py` - 限流控制器
  - Amazon SP-API文档

  **Acceptance Criteria**:
  - [ ] OAuth认证成功
  - [ ] 报告API可调用
  - [ ] 订单数据可读取
  - [ ] 限流控制生效

  **QA Scenarios**:
  ```
  Scenario: SP-API数据拉取
    Tool: Bash (pytest)
    Steps:
      1. 调用SP-API获取销售报告
      2. 验证数据格式正确
      3. 验证限流控制生效
      4. 验证数据写入数据库
    Expected Result: 真实数据成功获取
    Evidence: .sisyphus/evidence/task-31-sp-api.txt
  ```

  **Commit**: YES
  - Message: `feat(amazon): add SP-API client with read-only access`

### Wave 5：集成测试与文档

- [ ] 32. Phase 2 端到端集成测试

  **What to do**:
  - 创建 `tests/integration/test_phase2_e2e.py`：
    - 测试Rate Limiter在高并发下的表现
    - 测试LLM缓存命中率
    - 测试决策状态机完整流程
    - 测试新Agent链路
  - 测试场景：
    - 竞品→画像→文案 链路
    - 广告监控→告警→建议 链路
    - SP-API数据→日报 链路

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 5
  - **Blocks**: F5-F8
  - **Blocked By**: 21-31

  **Acceptance Criteria**:
  - [ ] 所有集成测试通过
  - [ ] 覆盖率≥80%

  **Commit**: YES
  - Message: `test(integration): add Phase 2 end-to-end tests`

---

## Phase 2 Final Verification Wave

- [ ] F5. Phase 2 计划合规审计
- [ ] F6. Phase 2 代码质量审查
- [ ] F7. Phase 2 实际QA验证
- [ ] F8. Phase 2 范围保真度检查

---

## Phase 2 Success Criteria

### 验证命令
```bash
# Rate Limiter
pytest tests/test_rate_limiter.py -v
# Expected: 限流正确触发，优先级排序正确

# LLM缓存
pytest tests/test_llm_cache.py -v
# Expected: 缓存命中率≥30%

# 决策追踪
pytest tests/test_decisions.py -v
# Expected: 状态机转换正确

# 新Agent
pytest tests/test_competitor_agent.py tests/test_persona_agent.py tests/test_listing_agent.py -v
# Expected: 全部通过

# SP-API
pytest tests/test_sp_api.py --live-api -v
# Expected: 真实数据获取成功（需要正式API权限）
```

### 最终检查清单
- [ ] Rate Limit Controller正常工作
- [ ] LLM缓存命中率≥30%
- [ ] 决策状态机可追踪所有Agent输出
- [ ] 竞品调研Agent可用
- [ ] 用户画像Agent可用
- [ ] Listing文案Agent可用
- [ ] 广告监控Agent可用
- [ ] SP-API正式环境可读取数据
