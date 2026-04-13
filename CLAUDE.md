# PUDIWIND AI System - Project CLAUDE.md

> 普帝风亚马逊自动化运营系统 | Phase 1 (Mock Data) | Production: siqiangshangwu.com

## 项目身份

本系统是一套面向亚马逊卖家的 **AI 多智能体自动化运营平台**，由 PUDIWIND（普帝风）品牌创始人 Jim 主导开发。系统通过 13 个专业 AI Agent 覆盖亚马逊运营全生命周期：从品牌规划、选品、竞品调研、用户画像分析，到 Listing 文案/图片生成、产品上架、库存监控、广告优化，最终通过审计 Agent 确保所有产出符合公司品牌路径和运营知识库。

**核心理念**：AI 辅助决策 + 人工审批确认。所有 Agent 产出必须经人工审批后才能固化到数据库或执行实际操作。

## 业务背景

- **品牌**：PUDIWIND（美国注册商标），宠物用品类目（狗牵引绳、胸背、项圈）
- **销售平台**：Amazon US (marketplace ID: ATVPDKIKX0DER)
- **团队**：Jim (boss) + 2 名运营
- **当前状态**：老产品清货中，通过本 AI 系统辅助品牌升级和新品开发
- **品牌战略方法论**：三势分析法（市场趋势 + 我方优势 + 敌方劣势）→ 品牌价值定位(BVP) → 最小单元模型（产品/价格/渠道/推广）
- **核心打法来源**：550 篇自有运营笔记 + 2000+ 篇合作伙伴共享思考文档（ppcopt.com 广告优化算法）

## 技术栈

### 前端
- **React 19** + React Router DOM 7 + TypeScript 5.8 + Vite 6
- **Tailwind CSS 4.1** (CSS-first config, `@theme` blocks, NOT `tailwind.config.ts`)
- **Recharts 3.8.0** (图表) + **Lucide React** (图标) + **Motion 12.23** (动画)
- **Axios** (HTTP, baseURL = `/api`) + **React Markdown** (渲染 AI 响应)
- 视觉风格：暗色调玻璃拟态(Glass-morphism) + 商务蓝调，响应式布局

### 后端
- **Python 3.12** + **FastAPI 0.115** + Uvicorn
- **SQLAlchemy 2.0.35** + Alembic (ORM & 迁移)
- **LangChain 0.3.7** + **LangGraph 0.2.40** (Agent 工作流编排)
- **LiteLLM** (多模型适配) + OpenAI SDK + Anthropic SDK
- **APScheduler** (定时任务) + **Loguru** (日志)
- 认证：JWT 双令牌 (access 30min + refresh 7d)
- LLM 网关：**OpenRouter** (统一接入，非直接调用 Anthropic)

### 数据库
- **PostgreSQL 16** + **pgvector** (1536 维向量，适配 text-embedding-3-small)
- 21 张数据表，覆盖用户、文档、产品、Agent 任务、审批、对话、广告模拟等

### 部署
- **Docker** 多阶段构建 (node:20-slim → python:3.12-slim)
- **Docker Compose**：app (FastAPI) + nginx (1.25-alpine) + postgres (pgvector:pg16)
- **AWS EC2** 新加坡区域 (52.221.207.30)
- 域名：siqiangshangwu.com

## 项目结构

```
amazon-automation/
├── src/
│   ├── agents/                    # 13 个 AI Agent 实现
│   │   ├── base_agent.py          # 基础 Agent 类 ⚠️ 禁止修改
│   │   ├── chat_base_agent.py     # 聊天 Agent 基类 (SSE 流式)
│   │   ├── model_config.py        # 模型配置映射
│   │   ├── core_agent/            # 运营主管 Agent
│   │   ├── brand_planning_agent/  # 品牌路径规划 Agent
│   │   ├── selection_agent/       # 选品 Agent
│   │   ├── competitor_agent/      # 竞品调研 Agent
│   │   ├── whitepaper_agent/      # 产品白皮书 Agent
│   │   ├── persona_agent/         # 用户画像 Agent
│   │   ├── keyword_library/       # 关键词库 Agent
│   │   ├── listing_agent/         # Listing 规划 Agent
│   │   ├── image_gen_agent/       # Listing 图片 Agent
│   │   ├── product_listing_agent/ # 产品上架 Agent
│   │   ├── inventory_agent/       # 库存监控 Agent
│   │   ├── ad_monitor_agent/      # 广告监控 Agent
│   │   └── auditor/               # 审计 Agent (boss only)
│   ├── api/                       # FastAPI 路由层
│   │   ├── main.py                # FastAPI app 入口
│   │   ├── middleware.py          # JWT 中间件
│   │   ├── auth.py                # 登录/注册/刷新
│   │   ├── chat.py                # SSE 聊天接口
│   │   ├── dashboard.py           # 数据大盘 API
│   │   ├── ads.py                 # 广告数据 API
│   │   ├── orders.py              # 订单 API
│   │   ├── returns.py             # 退货 API
│   │   ├── users.py               # 用户管理 API
│   │   └── system.py              # 系统配置 API
│   ├── db/
│   │   └── models.py              # SQLAlchemy 模型 (21 tables)
│   ├── config.py                  # Pydantic Settings (.env)
│   ├── knowledge_base/
│   │   └── rag_engine.py          # RAG 检索增强生成
│   ├── policy/
│   │   └── engine.py              # 规则引擎（决策校验）
│   ├── decisions/
│   │   └── state_machine.py       # 决策状态机
│   ├── scheduler/                 # APScheduler 定时任务
│   ├── llm/
│   │   └── client.py              # LLM 统一调用层
│   ├── feishu/                    # 飞书集成
│   ├── amazon_sp_api/             # SP-API 集成
│   ├── amazon_ads_api/            # 广告 API 集成
│   ├── seller_sprite/             # 卖家精灵 MCP
│   ├── google_trends/             # Google Trends
│   ├── services/                  # 业务服务层
│   ├── tasks/                     # 后台任务
│   └── frontend/                  # React 前端
│       ├── package.json
│       ├── vite.config.ts
│       ├── src/
│       │   ├── App.tsx            # 路由定义
│       │   ├── api/client.ts      # Axios 实例 (baseURL=/api)
│       │   ├── contexts/          # AuthContext, ThemeContext
│       │   ├── components/        # Layout, Sidebar, ProtectedRoute
│       │   ├── pages/             # 所有页面组件
│       │   ├── data/agents.ts     # Agent 元数据定义
│       │   └── types.ts           # TypeScript 类型定义
│       └── index.html
├── data/mock/                     # Phase 1 模拟数据层
│   └── dashboard.py               # Mock 仪表盘数据
├── deploy/
│   ├── docker/
│   │   ├── Dockerfile             # 多阶段构建
│   │   └── docker-compose.yml     # 三服务编排
│   └── nginx/
│       └── nginx.conf             # 反向代理配置
├── alembic/                       # 数据库迁移
├── 构思.md                        # 系统构思（完整需求）
├── 构思补充.md                    # 详细补充需求
├── 品牌路径规划初步分析思路.md    # 品牌战略方法论
├── 亚马逊广告优化算法.txt         # ppcopt.com 广告算法
├── 产品词库搭建SOP.docx          # 词库构建 SOP
└── PROJECT_DOCUMENTATION.md       # 系统技术文档
```

## Agent 完整目录

| 标识符 | 中文名称 | 触发方式 | 权限 | 聊天界面 |
|--------|----------|----------|------|----------|
| `core_management` | 运营主管 Agent | 随时 (飞书+Web) | 全员 | 飞书 + Web |
| `brand_planning` | 品牌路径规划 Agent | 月度定期 + 手动 | Boss 专属 | Web |
| `selection` | 选品 Agent | 周度定期 + 手动 | 全员 | Web |
| `whitepaper` | 产品白皮书 Agent | 仅手动 | 全员 | Web (支持图片上传) |
| `competitor` | 竞品调研 Agent | 月度定期 + 手动 | 全员 | Web |
| `persona` | 用户画像 Agent | 月度定期 + 手动 | 全员 | Web |
| `keyword_library` | 关键词库 Agent | 手动 + 月度监控 | 全员 | Web |
| `listing` | Listing 规划 Agent | 手动 + 月度监控 | 全员 | Web |
| `image_generation` | Listing 图片 Agent | 仅手动 | 全员 | Web |
| `product_listing` | 产品上架 Agent | 仅手动 | 全员 | Web |
| `inventory` | 库存监控 Agent | 自动(日度) + 手动 | 全员 | Web |
| `ad_monitor` | 广告监控 Agent | 自动 + 手动 | 全员 | Web (广告管理页内) |
| `auditor` | 审计 Agent | 自动拦截 | Boss 专属 | Web |

### Agent 通用规则
1. **人工审批优先**：所有 Agent 产出（报告、文案、词库等）必须经人工确认后才能录入数据库
2. **知识库对齐**：所有 Agent 决策不能偏离公司基础知识库中的核心打法
3. **审计闭环**：审计 Agent 有权自动驳回违规产出
4. **版本管理**：确认后清理中间版本文件，只保留最终确认版
5. **核心管理 Agent 特殊**：唯一同时支持飞书和 Web 端聊天的 Agent

## 前端路由表

| 路径 | 组件 | 说明 |
|------|------|------|
| `/login` | Login | 登录页 |
| `/` | Dashboard | 数据大盘 (首页) |
| `/agents` | AgentCatalog | Agent 列表 (更多功能) |
| `/agents/:type` | AgentChat | Agent 聊天 |
| `/chat/:agentType` | AgentChat | Agent 聊天 (别名) |
| `/ads` | AdDashboard | 广告数据大盘 |
| `/ads/manage` | AdManagement | 广告管理 |
| `/ads/agent` | AdAgentPage | 广告优化 Agent |
| `/orders` | OrdersPage | 全部订单 |
| `/returns` | ReturnsPage | 退货订单 |
| `/approvals` | ApprovalsPage | 审批中心 |
| `/kb-review` | KBReview | 知识库审核 (boss) |
| `/system` | SystemManagement | 系统管理 (boss) |
| `/system/users` | UserManagementPage | 用户管理 (boss) |
| `/system/agents` | AgentConfigPage | Agent 配置 (boss) |
| `/system/api-keys` | ApiKeysPage | API 密钥 (boss) |
| `/system/costs` | CostMonitor | 费用监控 (boss) |

## 后端 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录 (返回 access + refresh token) |
| POST | `/api/auth/refresh` | 刷新令牌 |
| GET | `/api/dashboard/metrics` | 数据大盘指标 |
| GET | `/api/dashboard/trends` | 趋势数据 |
| GET | `/api/dashboard/sku-ranking` | SKU 排行榜 |
| POST | `/api/chat/{agent_type}/stream` | Agent SSE 聊天流 |
| GET | `/api/ads/dashboard` | 广告大盘数据 |
| GET | `/api/ads/campaigns` | 广告活动列表 |
| GET | `/api/orders` | 订单列表 |
| GET | `/api/returns` | 退货列表 |
| GET | `/api/users` | 用户列表 (boss) |
| POST | `/api/users` | 创建用户 (boss) |
| GET | `/api/system/config` | 系统配置 |
| GET | `/health` | 健康检查 (public) |

## 认证系统

- JWT payload：`{"sub": username, "role": role, "type": "access|refresh", "exp": ..., "iat": ...}`
- 测试账号：`boss` / `test123` (角色: boss)
- 角色权限：
  - `boss`：全部功能 + 系统管理 + 审计 Agent + 品牌规划 Agent
  - `operator`：日常运营功能，无系统管理权限
- 前端 Axios 拦截器自动附加 `Authorization: Bearer {token}` 头

## 编码规范与约束

### 绝对禁止 (Hard Rules)
- **禁止修改** `src/agents/base_agent.py`
- **禁止** `as any`、`@ts-ignore`、`@ts-expect-error` (TypeScript)
- **禁止** 生产代码中的 `console.log`
- **禁止** 调用 Amazon Ads API 写入端点
- **禁止** 实现真实 SP-API 数据管道 (Phase 1 仅 Mock)
- **禁止** 使用 WebSocket 做通知 (使用轮询)
- **禁止** 空 catch 块 `catch(e) {}`
- **禁止** 删除失败的测试来"通过"测试

### 前端规范
- Tailwind CSS 4 (CSS-first)：使用 `@theme` 块，不用 `tailwind.config.ts`
- React 19：不需要 `forwardRef`
- Axios `baseURL` 已设为 `/api`，组件中请求路径不要再加 `/api` 前缀
  - 正确：`api.get('/dashboard/metrics')`
  - 错误：`api.get('/api/dashboard/metrics')` (双重前缀)
- 图表使用 Recharts 3.8.0
- 动画使用 Motion 12.23 (原 framer-motion)
- 图标使用 Lucide React
- 构建命令：`npm run build` (在 `src/frontend/` 目录下，不用 bun)

### 后端规范
- 异步优先 (async/await)
- 日志使用 Loguru，不要 print
- 配置通过 Pydantic Settings 从 .env 读取
- 所有自动化动作必须输出日志，保证可审计、可追溯、可回滚
- 决策状态机：DRAFT → PENDING_APPROVAL → APPROVED → EXECUTING → SUCCESS/FAILED

### 数据公式化计算
以下指标直接用代码公式计算，不走 LLM：
- ACoS = 广告花费 / 广告销售额 × 100%
- ACoAS = 广告花费 / 总销售额 × 100%
- 转化率 = 订单量 / 点击量 × 100%
- CPC = 广告花费 / 点击量
- 预计可售天数 = 当前库存 / 近期日均销量

注意亚马逊归因时间问题：当天从 SP-API 获取的数据在 3 天后可能因归因调整而变动。

## 部署流程

```powershell
# 1. 构建前端
npm run build  # 在 src/frontend/ 目录

# 2. 打包 deploy-bundle.zip
# 包含: deploy/, src/, data/, alembic/, requirements.txt, alembic.ini

# 3. 上传到服务器
$PEM = "$env:USERPROFILE\Downloads\Pudiwind.pem"
scp -i $PEM deploy-bundle.zip ubuntu@52.221.207.30:/tmp/

# 4. 解压
ssh -i $PEM ubuntu@52.221.207.30 "sudo unzip -o /tmp/deploy-bundle.zip -d /opt/amazon-ai/"

# 5. 重建 & 启动 (⚠️ 前端变更必须删除 volume)
ssh -i $PEM ubuntu@52.221.207.30 "cd /opt/amazon-ai/deploy/docker; sudo docker compose down; sudo docker volume rm amazon-ai-frontend-dist 2>/dev/null; sudo docker compose build app; sudo docker compose up -d"
```

### 关键部署注意事项
- **前端变更必须删除 `amazon-ai-frontend-dist` volume**，否则 Nginx 会继续提供旧的静态文件
- Docker 容器：`amazon-ai-app` (FastAPI)、`amazon-ai-nginx` (反向代理)、`amazon-ai-postgres` (数据库)
- 数据库用户：`app_user` (不是 `postgres`)
- 服务器路径：`/opt/amazon-ai/`
- PowerShell 环境：不能使用 `export`、`&&`、`tail`，使用 PowerShell 等效命令

## 开发阶段

### Phase 1 (当前) — Mock Data
- 所有业务数据（订单、广告、库存）由 `data/mock/` 下的 Python 函数动态生成
- 前端 UI 逻辑与真实数据接入时保持一致
- SP-API 和广告 API 均为沙箱/Mock 状态

### Phase 2 (计划) — Real API Integration
- 接入真实 Amazon SP-API
- 接入真实 Amazon Advertising API
- 接入卖家精灵 MCP 实时数据
- OpenRouter 统一 LLM 网关

### 未实现功能 (明确不做)
- 毛利润/毛利率计算 (显示空/dash)
- 广告管理状态统计栏
- FBM 退货 / Voice of Customer tab
- 独立消息中心页面
- SSL 证书 (在所有功能完成后最后部署，使用 Let's Encrypt)

## 已知问题与历史 Bug

### 已修复
1. **白屏 Bug**：JWT payload 字段不匹配 (`"username"` → `"sub"`)
2. **双 `/api` 前缀**：部分页面重复添加 `/api` 前缀
3. **API 响应格式不匹配**：后端 JSON 结构与前端预期不一致
4. **Docker volume 缓存**：前端变更不生效，需删除 named volume

### 需关注
- 亚马逊数据归因延迟（3天归因窗口）的处理方案待确定
- 飞书机器人当前仅返回"请使用 Web 端"提示，尚未实现实际聊天功能
- Agent 对话历史持久化尚需优化（部分 Agent 退出后聊天记录不保留）
- 部分 Agent 出现 API Key 认证错误（OpenRouter 配置待统一）

## 外部依赖与集成

| 服务 | 用途 | 当前状态 |
|------|------|----------|
| Amazon SP-API | 订单/库存/目录/报表 | 沙箱 |
| Amazon Advertising API | 广告活动/关键词/预算 | 沙箱 |
| 卖家精灵 (SellerSprite) MCP | 亚马逊市场数据 | Mock |
| 飞书 (Lark) | 机器人/消息/审批/日报 | 部分接入 |
| OpenRouter | 统一 LLM 网关 | 待配置 |
| Google Trends (SerpApi) | 趋势分析 | 可选，待确认 |

## 环境变量 (.env)

关键变量参见 `src/config.py` 中的 `Settings` 类，主要包括：
- `DATABASE_URL` — PostgreSQL 连接串
- `OPENAI_API_KEY` / `OPENROUTER_API_KEY` — LLM 密钥
- `FEISHU_APP_ID` / `FEISHU_APP_SECRET` — 飞书集成
- `SELLER_SPRITE_API_KEY` — 卖家精灵
- `AMAZON_ADS_*` — 广告 API OAuth
- `AMAZON_SP_API_*` — SP-API OAuth
- `MAX_DAILY_LLM_COST_USD` — 日费用上限 (默认 $50)

## 快速参考

```bash
# 本地前端开发
cd src/frontend && npm install && npm run dev

# 本地后端开发
pip install -r requirements.txt
uvicorn src.api.main:app --reload --port 8000

# 前端构建
cd src/frontend && npm run build

# SSH 到服务器
ssh -i ~/Downloads/Pudiwind.pem ubuntu@52.221.207.30

# 查看 Docker 日志
ssh "cd /opt/amazon-ai/deploy/docker; sudo docker compose logs -f app"
```
