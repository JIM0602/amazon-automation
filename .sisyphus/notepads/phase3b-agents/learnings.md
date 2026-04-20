# Phase 3b Learnings

## [2026-04-06] Session Start — Code Audit

### 关键代码契约（通过直接读取代码确认）

**src/api/schemas/agents.py**
- `AgentType` 有 5 个值: selection, listing, competitor, persona, ad_monitor
- `AgentRunStatus` 只有 `output_summary: Optional[str]`，没有 `result` 字段
- 完全没有 `AGENT_PARAM_SCHEMAS` 字典

**src/api/agents.py**
- `_run_agent_background()` 处理 5 个 agent_type，else 分支 raise ValueError
- `_VALID_AGENT_TYPES = {e.value for e in AgentType}` 在模块级定义，添加新类型后需重启才生效
- trigger endpoint 在 line 185 验证 agent_type 在 `_VALID_AGENT_TYPES` 中

**src/db/models.py**
- `AgentRun` 表没有 `result_json` 列，只有 `output_summary TEXT`
- `Document` model 有字段: id, title, content, source, category, embedding, doc_type, version, priority
- `DocumentChunk` 有: id, document_id (FK), chunk_text, chunk_embedding, chunk_index, doc_type
- **`Document.source` 字段 (NOT file_path)**

**src/api/main.py**
- 注册了: auth_router, system_router, agents_router
- 有基础 `GET /health` (无需认证)
- **没有** knowledge_base router
- **没有** /api/health/* 路由

**src/knowledge_base/document_processor.py**
- 有 `_load_docx()` 方法
- 有 `process_batch()` 但写JSON文件不直接返回chunks
- 需用 `load_document()` + `chunk_document()` 获取 chunks

**scripts/ 目录现有文件**
- init-demo.sh, preprocess_docs.py, setup-server.sh, test_feishu.py
- **没有** import_documents.py

### 部署信息
- 服务器: ubuntu@52.221.207.30
- 项目路径: /opt/amazon-ai/
- PEM: ~/Downloads/Pudiwind.pem
- Docker: 4容器运行中 (nginx, frontend, app, postgres)
- DB用户: app_user (NOT postgres)
- 重启命令: sudo docker compose -f /opt/amazon-ai/deploy/docker/docker-compose.yml down && build && up -d
[2026-04-06] ���α��
- AgentType ��չ�� 11 ��ֵ�������� AGENT_PARAM_SCHEMAS��ǰ�˿ɶ�̬�õ����� schema��
- AgentRunStatus ���� result �ֶΣ�_run_to_status() ���ȶ�ȡ result_json�����ݾɵ� output_summary JSON��
- _run_agent_background() Ϊ 6 ���� Agent ���� not_yet_implemented ռλ��֧�����ڳɹ�·��д�� result_json��
- ���� GET /api/agents/types �˵㣬����ȫ�� agent ���ͺͲ������塣
- ���� scripts/migrate_add_result_json.sql Ǩ�ƽű���
- Զ�˲���ʱ����������������Դ����أ��������Ķ������Զ���Ч����Ҫ docker cp ���ؽ���������� app��

## [2026-04-17] AgentCardInfo 文件侧边栏标记

### 交付记录
- 已在 `src/frontend/src/data/agents.ts` 的 `AgentCardInfo` 接口新增 `hasFileSidebar: boolean`。
- 已为 12 个 Agent 补齐该字段，配置与产品约定一致：`core_management`、`selection`、`image_generation`、`product_listing` 为 `false`；其余 8 个为 `true`。
- `npm run build` 在 `src/frontend/` 下执行通过，说明类型链路与打包结果正常。
