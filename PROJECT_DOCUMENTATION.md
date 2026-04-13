# 普帝风 AI 系统 (PUDIWIND AI System) 技术文档

本文档旨在为普帝风 AI 系统（亚马逊卖家自动化 AI 代理平台）提供全面的技术参考与使用指南。本系统目前已完成第一阶段（Phase 1）开发，采用模拟数据层验证核心流程，并为第二阶段的真实 API 集成奠定了坚实基础。

## 一、技术栈

本系统采用前后端分离架构，核心逻辑由 AI Agent 驱动，结合高性能数据库与容器化部署方案。

### 前端技术栈
前端采用现代化的 React 生态系统，注重用户体验与视觉表现，整体风格为暗色调玻璃拟态（Glass-morphism）。

- **框架**: React 19.0.0
- **路由**: React Router DOM 7.0.0
- **语言**: TypeScript 5.8 (严格类型检查)
- **构建工具**: Vite 6.2 (集成 @tailwindcss/vite 插件)
- **样式**: Tailwind CSS 4.1 (原子化 CSS)
- **图表库**: Recharts 3.8.0 (用于展示销售、广告趋势)
- **图标**: Lucide React 0.546 (矢量图标集)
- **动画**: Motion 12.23 (原名 framer-motion，处理平滑过渡与交互)
- **网络请求**: Axios 1.7 (集成拦截器处理 JWT)
- **内容渲染**: React Markdown 10.1 (渲染 AI 生成的 Markdown 响应)
- **样式工具**: clsx + tailwind-merge (动态类名管理)

### 后端技术栈
后端基于 Python 生态构建，利用异步框架处理高并发 AI 请求与外部 API 调用。

- **核心语言**: Python 3.12
- **Web 框架**: FastAPI 0.115 + Uvicorn 0.30.6 (高性能异步接口)
- **ORM 与迁移**: SQLAlchemy 2.0.35 + Alembic 1.13.3
- **AI 代理框架**: LangChain 0.3.7 + LangGraph 0.2.40 (工作流编排)
- **大模型支持**: OpenAI SDK 1.54+, Anthropic SDK 0.37.1, LiteLLM 1.52 (多模型适配)
- **认证与加密**: python-jose 3.3.0 (JWT), passlib + bcrypt (密码安全哈希)
- **任务调度**: APScheduler 3.10.4 (处理日报生成与自动选品)
- **配置与校验**: Pydantic 2.9.2 + pydantic-settings
- **日志系统**: Loguru 0.7.2 (结构化异步日志)
- **异步请求**: HTTPX 0.27.2
- **外部集成**: lark-oapi 1.4.6 (飞书/Lark 集成)
- **文档处理**: unstructured 0.15.14 + python-docx
- **评估框架**: ragas 0.2.5 (RAG 质量评估)
- **代码规范**: Ruff 0.7.0

### 数据库设计
系统使用 PostgreSQL 16 搭配 pgvector 插件，支持传统结构化数据存储与高维向量相似度检索。

- **数据库引擎**: PostgreSQL 16 (基于 pgvector:pg16 容器镜像)
- **向量扩展**: pgvector (支持 1536 维向量，适配 OpenAI text-embedding-3-small)
- **数据表结构 (21 张表)**:
  1. `users`: 用户账户与角色信息
  2. `documents`: 原始文档元数据
  3. `document_chunks`: 文档分块及对应的向量嵌入
  4. `products`: 亚马逊产品信息
  5. `product_selection`: 选品分析结果
  6. `agent_runs`: Agent 运行实例记录
  7. `agent_tasks`: 待处理或已完成的 Agent 任务
  8. `approval_requests`: 系统决策审批流
  9. `daily_reports`: 每日运营摘要数据
  10. `system_config`: 全局配置项
  11. `audit_logs`: 安全与操作审计日志
  12. `llm_cache`: 大模型响应缓存，降低成本与延迟
  13. `decisions`: 待执行的业务决策
  14. `conversations`: 聊天会话主体
  15. `chat_messages`: 具体的聊天消息记录
  16. `keyword_libraries`: 关键词词库
  17. `ad_simulations`: 广告模拟投放预测
  18. `ad_optimization_logs`: 广告优化建议记录
  19. `kb_review_queue`: 知识库待审核条目
  20. `auditor_logs`: 审计 Agent 评分记录
  21. `agent_configs`: 针对不同 Agent 的系统提示词配置

### 部署与基础设施
- **容器化**: Docker 多阶段构建（frontend-builder 基于 node:20-slim，backend-builder 与 runtime 基于 python:3.12-slim）。
- **编排**: Docker Compose 部署 app (FastAPI)、nginx (反向代理) 和 postgres。
- **反向代理**: Nginx 1.25-alpine (托管静态文件，转发 `/api/` 请求，支持 SSE 流式传输)。
- **服务器**: AWS EC2 位于新加坡地区 (IP: 52.221.207.30)。
- **域名**: siqiangshangwu.com。

### 外部集成
- **亚马逊**: SP-API (订单、目录、库存、报表) 与 Advertising API (广告活动、关键词、预算管理)。
- **飞书 (Lark)**: 机器人命令交互、消息卡片回调、审批通知、日报推送。
- **市场分析**: 卖家精灵 (SellerSprite) MCP 节点集成。
- **模型提供商**: OpenAI (GPT-4o, GPT-4o-mini, text-embedding-3-small), Anthropic (Claude 3.5 Sonnet)。

## 二、系统架构与运行逻辑

### 整体架构
系统遵循经典的 C/S 模式，核心大脑位于 FastAPI 驱动的 Agent 层：
`浏览器 (Browser) ↔ Nginx (反向代理) ↔ FastAPI (业务逻辑) ↔ PostgreSQL / LLM APIs / 外部 APIs`

### 请求流程
1. 用户访问 `siqiangshangwu.com`，Nginx 监听 80/443 端口。
2. Nginx 直接返回位于 `/usr/share/nginx/html` 的 SPA 静态资源。
3. 前端发起所有以 `/api/*` 开头的请求均被 Nginx 转发至本地 8000 端口的 FastAPI 应用。
4. 后端 JWT 中间件拦截请求，验证 `Authorization` 头部，解析用户信息并注入 `request.state.user`。
5. 路由处理器根据业务需求访问模拟数据层或数据库，并返回标准 JSON 响应。

### 认证系统
- **机制**: 基于 JWT 的双令牌验证。`access_token` 有效期 30 分钟，`refresh_token` 有效期 7 天。
- **角色分配**:
  - `boss`: 拥有系统所有权限，包括用户管理、API 密钥配置与高阶审计 Agent 调用。
  - `operator`: 操作员角色，可执行日常运营、查看数据与调用通用 Agent。
- **安全性**: 所有敏感路径均需 `Bearer` 令牌。公开路径仅限 `/health`、登录/刷新接口、API 文档以及飞书回调。

### AI Agent 对话流
- **传输协议**: 采用 Server-Sent Events (SSE) 协议，路径为 `POST /api/chat/{agent_type}/stream`，实现打字机式的流式回复。
- **执行逻辑**: `ChatBaseAgent` 加载预设系统提示词 → 从数据库读取历史对话背景 → 调用 LLM 接口 → 逐步 yield 文本块 → 完成后将全量回复异步存入数据库。
- **知识自迭代**: 每次回复结束后触发 Hook，Agent 会分析当前对话是否产生新知识，并自动提报给知识库审核队列。

### 数据流
当前处于 Phase 1，所有业务数据（订单、广告、库存）由后端 `data/mock/` 目录下的 Python 函数动态生成。前端 API 调用这些模拟接口，确保 UI 逻辑与真实集成时保持一致。

### 定时任务
利用 APScheduler 管理关键自动化流程：
- `daily_report`: 每天 09:00 生成前一日运营摘要并推送到飞书群组。
- `selection_analysis`: 每周一 10:00 启动大数据分析流程，更新潜在高利润选品名单。
- `llm_cost_report`: 每天 23:00 汇总当日所有 Agent 的 API 调用消耗，并发送费用预警。

### 决策状态机与规则引擎
- **决策生命周期**: 决策（如调价、超支预警）遵循 `草稿(DRAFT) → 待审批(PENDING_APPROVAL) → 已批准(APPROVED) → 执行中(EXECUTING) → 成功/失败` 的闭环流程。任何状态变更均记录于 `audit_logs` 表。
- **规则引擎**: 线程安全的 Policy Engine 在决策批准前进行二次校验（例如：单次调价幅度不得超过 20%，总预算不得超过日均限额）。

### 知识库 (RAG)
系统集成 RAG 架构实现精准的知识问答：
1. **解析**: 对上传的 Word/PDF 文档进行分块处理。
2. **嵌入**: 使用 `text-embedding-3-small` 生成 1536 维向量。
3. **存储**: 存入带有 `vector` 类型的 PostgreSQL 字段。
4. **检索**: 对话时利用余弦相似度进行语义检索，结合元数据过滤（如仅检索 2024 年后的文档）。
5. **生成**: LLM 根据检索到的知识片段生成增强后的精准回答。

## 三、Agent 目录

普帝风系统内置 13 个专业 Agent，涵盖了亚马逊运营的全生命周期。

| 标识符 | 中文名称 | 功能描述 | 核心模型 | 类别 | 权限 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `core_management` | 运营主管Agent | 统筹任务、生成日报周报、制定年度运营计划 | GPT-4o | 运营 | 全员 |
| `brand_planning` | 品牌路径规划Agent | 基于市场现状规划品牌成长路径与护城河 | Claude 3.5 Sonnet | 分析 | Boss |
| `selection` | 选品Agent | 基于大数据算法推荐高潜力、低竞争产品 | GPT-4o | 分析 | 全员 |
| `competitor` | 竞品调研Agent | 深度分析类目趋势、监控竞品 BSR 与评论动态 | GPT-4o | 分析 | 全员 |
| `whitepaper` | 产品白皮书Agent | 深入挖掘产品技术卖点、编写详细说明文档 | Claude 3.5 Sonnet | 内容 | 全员 |
| `listing` | Listing规划Agent | 关键词埋词优化、SEO 文案生成、五点描述撰写 | Claude 3.5 Sonnet | 内容 | 全员 |
| `image_generation` | Listing图片Agent | 生成产品主图、生活场景图及 A+ 页面素材 | GPT-4o | 内容 | 全员 |
| `product_listing` | 产品上架Agent | 自动化处理 Listing 上架流程与批量属性配置 | GPT-4o | 运营 | 全员 |
| `inventory` | 库存监控Agent | 监控 FBA 库存状态、基于销量预测智能补货 | GPT-4o-mini | 运营 | 全员 |
| `ad_monitor` | 广告监控Agent | 实时监控 ACoS 与转化率，自动优化关键词出价 | GPT-4o | 监控 | 全员 |
| `persona` | 用户画像Agent | 通过 VOC 分析提取用户痛点、偏好与购买意图 | GPT-4o | 分析 | 全员 |
| `keyword_library` | 关键词库Agent | 整合多渠道关键词数据，进行分类与权重评估 | GPT-4o-mini | 分析 | 全员 |
| `auditor` | 审计Agent | 对其他 Agent 的输出质量进行独立评分与合规审核 | Claude 3.5 Sonnet | 监控 | Boss |

## 四、系统使用手册

### 1. 登录系统
- 访问官方地址：`https://siqiangshangwu.com/`。
- 输入您的账号密码。
- **注意**: Boss 角色可见「系统管理」菜单，Operator 角色仅可见日常运营菜单。

### 2. 数据大盘 (Dashboard)
- **核心指标**: 首页顶部展示销售额、订单数、销量、广告费等 10 项核心卡片。
- **趋势分析**: 通过图表查看销售额与订单量的波动情况，支持不同时间维度的切换。
- **SKU 排行**: 快速掌握哪些产品是当前的利润中心。

### 3. AI Manager (运营主管Agent)
- 系统的默认入口。在这里您可以像使用 ChatGPT 一样与运营主管交流。
- 支持流式输出，AI 会根据实时抓取的店铺数据回答您的经营状况问题。

### 4. 更多功能 (Agent列表)
- 在左侧导航栏展开「更多功能」。
- 您可以选择特定的 Agent 执行专业任务，如「选品助手」或「Listing 优化器」。
- 每个 Agent 都有专属的上下文，专注于其擅长的领域。

### 5. 广告监控与管理
- **广告大盘**: 查看整体 ACoS、CTR、CPC 等广告核心漏斗指标。
- **多维度管理**: 通过 Tab 切换查看 Portfolio、Campaign 以及具体的 Search Term 情况。
- **AI 优化建议**: 广告管理页面集成了专门的 Agent，可以针对具体的广告活动给出调价建议。

### 6. 订单与退货管理
- **订单查询**: 实时查看所有亚马逊订单状态，支持分页浏览。
- **售后监控**: 重点关注退货订单，辅助分析产品潜在质量问题。

### 7. 审批中心
- 系统 Agent 产生的关键决策（如修改产品价格、增加广告预算）不会直接生效。
- 管理员需在「审批中心」进行人工审核，确保所有自动执行的动作符合运营策略。

### 8. 系统管理 (Boss 专属)
- **用户管理**: 添加新员工账号，分配相应权限。
- **Agent 配置**: 自定义 Agent 的中文显示名称或微调其 Prompt。
- **API 密钥**: 配置 OpenAI 与 Anthropic 的 Key，系统会自动通过 LiteLLM 进行分发。
- **费用监控**: 实时监控大模型调用的 Token 消耗，防止费用异常增长。

### 9. 界面操作技巧
- **侧边栏**: 底部有收起/展开按钮，收起后可获得更大的工作空间。
- **暗色模式**: 系统原生支持暗色主题，缓解长时间运营产生的视觉疲劳。
- **多轮对话**: 所有的 Agent 均支持多轮对话记忆，无需在单次提问中输入所有背景。
