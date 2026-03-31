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

### Task 6 交付记录
- 已新增 docs/sp-api-guide.md，明确 Phase 1 仅使用 Mock 数据，SP-API 申请与联调放到 Phase 2。
- 已新增 src/amazon_api/mock.py，覆盖 products / orders / advertising / inventory 四类 Mock 数据与统一路由接口。
- 已补充 data/mock/products.json 与 data/mock/orders.json，并为订单数据准备了 30 天样例。
- 已新增 tests/test_mock_data.py，验证数量、字段完整性和路由行为。

## [2026-03-31] T2: ���ݿ���ƺʹ

### SQLAlchemy + pgvector �ؼ�ģʽ
- pgvector.sqlalchemy.Vector(1536) ����Ƕ�������У�ά�ȹ̶�Ϊ1536��text-embedding-3-small��
- pgvector �ڲ��Ի���������ʱ��ͨ�� try/except ����Ϊ UserDefinedType stub��SQLite �����δ֪����
- UUID ������Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4) ��� PostgreSQL ԭ�� UUID ����

### ����ʼ�����棨�ؼ������ѵ��
- **����** ��ģ�鼶�� engine = create_engine(settings.DATABASE_URL)����Ϊ��
  1. ����ʱ settings.DATABASE_URL ��δ mock�����Ի�ʧ�ܣ�
  2. psycopg2 δ��װʱ�� ImportError�����ػ�����
  3. SQLite ������ pool_size/max_overflow ����
- ��ȷ������������ get_engine()��ͨ���������� _LazyEngine ����ģ�鼶 engine ����
- ������ÿ�� test ǰ����� _reset_connection_cache() ��� _engine = None ����

### Alembic ����Ҫ��
- lembic.ini �� sqlalchemy.url �� %(DB_USER)s ռλ������Ӳ��������
- lembic/env.py ���ȶ�ȡ os.environ["DATABASE_URL"]��Docker/CI������� pydantic-settings
- compare_type=True ���������ͱ����⣨����ά�ȸı�ʱ Alembic �ɸ�֪��
- pool.NullPool ���� online migration mode������Ǩ�ƽ��̳������ӳأ�

### ���Բ���
- utouse=True fixture �����в���ǰע�� pgvector stub �� mock settings
- SQLite in-memory ��Ϊ ORM CRUD ���Ժ�ˣ�sqlite:// + StaticPool + check_same_thread=False��
- importlib.reload() �ڲ�����Ӧ����ʹ�ã����ܵ��� proxy ����ʧЧ��ֱ���� _reset_connection_cache() + get_engine() ���ȶ�

### 10�����Ĺؼ��ֶα���
- system_config: key �� PK��String�������� UUID
- udit_logs: �� gent_type���� ctor
- product_selection.agent_run_id: nullable��FK SET NULL��
- pproval_requests.approved_by: nullable������ǰΪ�գ�
- daily_reports.sent_at: nullable������ǰΪ�գ�
- gent_runs.finished_at: nullable��������Ϊ�գ�

## [2026-03-31] T4: ֪ʶ���ĵ�Ԥ����

### ������
- ���� src/knowledge_base/document_processor.py��DocumentProcessor �����ࣩ
- ���� scripts/preprocess_docs.py��CLI ��ڣ�
- ��� tests/golden_qa.json��20���ƽ�QA��6�������⸲�ǣ�
- ���� tests/test_preprocess.py��31����Ԫ���ԣ�ȫ��ͨ����

### �ؼ�ʵ��ϸ��
- ����ʹ�ùؼ��ʼ�����߷ֲ��ԣ��� LLM ����
- �ֿ鰴���䣨\n\n���и�ַ������� token��1 token �� 4 �ַ���
- ȥ���� MD5 ��ϣ��O(n) ���Ӷ�
- python-docx / unstructured ͨ�� try/except ImportError ����δ��װ����
- os.makedirs(path, exist_ok=True) ���� mkdir -p��Windows PowerShell ���ݣ�

### ���Բ���
- ȫ������ʵ��ʱ�ļ���tmp_path fixture������ mock_open�����ӽ���ʵ��Ϊ
- TestClassifyDocument: 8 ��������ȫ��6��� + �߽磨���ַ�������ؼ��ʣ�
- TestChunkDocument: 6 ���������顢��顢overlap�����ĵ���metadata��
- TestDeduplicate: 5 ���������ظ�����ȫ�ظ������ظ������б������ƣ�
- TestProcessBatch: 7 ����������ṹ��������JSON�������Ŀ¼��
- TestLoadDocument: 5 ������txt/md���ء��������ļ�����֧�ָ�ʽ����ϴ��

### ��
- PowerShell ��֧�� export ���git/python ֱ�ӵ��ü���
- ���Զ��� max_tokens ʱ�������䳬����������������ģ�����Ӧ��Ϊ����������ֿ项

## [2026-03-31] T4: ֪ʶ���ĵ�Ԥ����

### ������
- DocumentProcessor: load/classify/deduplicate/chunk/process_batch
- CLI: scripts/preprocess_docs.py (--input/--output/--check-duplicates)
- 20���ƽ�QA����6�����
- 31����Ԫ����ȫ��ͨ��

### �ؼ�ʵ��
- ����: �ؼ��ʼ�����߷ֲ��ԣ���LLM
- �ֿ�: �������и�ַ�����token(1t��4c)��100token�ص�
- ȥ��: MD5��ϣ
- ��ѡ����: try/except ImportError����

### ��
- chunk���Զ���ӦΪ��������项���ǡ�ÿ�鲻����X����������ɳ��ޣ�
- PowerShell��֧��export/2>&1���

## [2026-03-31] T5: ��������˻�������

### ��������
- src/feishu/bot_handler.py: FeishuBot �ࣨToken���� + ��Ϣ���� + Webhook������
- src/feishu/command_router.py: ��Ϣ����·�ɣ�4�ֹ���
- src/api/main.py: FastAPI Ӧ����ڣ�/health + /feishu/webhook��
- tests/test_feishu.py: 27����Ԫ���ԣ�ȫ�� PASSED

### �ؼ�ʵ��ϸ��
- tenant_access_token ������ԣ�expire_at - 300����ǰˢ�£���ֹ�߽�ʧЧ��
- ��Ϣ content �ֶα����� JSON �ַ�������Ƕ�� dict��������API�淶Ҫ��
- Webhook ǩ���㷨��SHA256(timestamp + nonce + encrypt_key + body_str)
- mock patch ·������ģ�鱻��������ִ�У�fixture ��Ҫ�� import �� patch

### ·�ɹ������ȼ�
1. �� ? �� �� ��ͷ �� knowledge_query���� query ��ȡ��
2. �������ձ����򡸱��桹 �� daily_report
3. ������ѡƷ�� �� selection_analysis
4. ���� �� unknown�����ذ�����ʾ��

### FastAPI Webhook �ؼ�����
1. ��ȡ body + headers
2. parse_webhook_event��ǩ����֤ + JSON������
3. type=url_verification �� ���� challenge
4. event_type=im.message.receive_v1 �� ��ȡ�ı� �� route_command
5. �����¼� �� ���ԣ����� {"code": 0}

### �ȿӼ�¼
- patch("src.feishu.bot_handler.settings") ��ģ��δ������ʱ�� AttributeError
  �����fixture ����ִ�� import src.feishu.bot_handler ��ʹ�� patch �����Ĺ�����
- Python 3.14 ��������ȱ�� requests/fastapi���� pip install ���루requirements.txt ���У�
- PowerShell ��֧�� export ���git ֱ�ӵ��ü���

## [2026-03-31] T7: RAG知识库系统搭建

### 交付物
- src/knowledge_base/rag_engine.py: RAGEngine 核心类（embed_text/ingest_chunks/search/answer + query 便捷函数）
- tests/test_rag.py: 19 项单元测试，全部 PASSED（全 mock，不调用真实 API）
- tests/eval_rag.py: RAGAS 评测脚本（自实现评分，不依赖 ragas 库）
- .sisyphus/evidence/task-7-*.txt/json: 正向/负向查询证据 + RAGAS 评测 JSON 报告

### 关键实现细节

#### rag_engine.py 架构要点
- openai/langchain 库均用 try/except ImportError 处理（本地未安装时注入 stub 降级）
- 模块顶部导入 db_session、DocumentChunk、text（而非延迟导入），使测试可用 patch 覆盖
- _OPENAI_AVAILABLE 模块级变量，控制 embed_text 是否可用
- answer() 中空检索结果 → 直接返回 "没有找到相关信息"，不调用 LLM

#### 拒绝编造逻辑（关键）
- search_results 为空时，直接返回固定文案，tokens_used=0
- 答案格式：根据现有知识库，我没有找到相关信息。（问题：{question}）
- 测试断言字符串为 "没有找到相关信息"（位于模板中间位置）

#### pgvector 查询格式
- query_vec_str = "[v1,v2,...]" 格式传给 CAST(:query_vec AS vector)
- 余弦距离：chunk_embedding <=> CAST(:query_vec AS vector) AS distance
- similarity_score = max(0.0, 1.0 - distance)

#### 测试策略（无 openai 库环境）
- 测试文件顶部注入 stub：sys.modules["openai"] = ModuleType("openai")
- _make_engine() 用 RAGEngine.__new__() 绕过 __init__，直接注入 mock client
- embed_text 正向测试需 patch("src.knowledge_base.rag_engine._OPENAI_AVAILABLE", True)
- db_session/DocumentChunk/text 在 rag_engine 模块级导入，可直接 patch

### 踩坑记录
1. patch("openai.OpenAI") 在 openai 未安装时会 ModuleNotFoundError → 改用 sys.modules 注入 stub
2. 延迟导入的函数（方法内 from x import y）无法通过 patch("rag_engine.y") 覆盖 → 改为模块顶部导入
3. 中文字符串 "没有找到相关信息" 在 "...没有找到关于xxx的相关信息" 中 **不是子串**（因为 "关于xxx的" 打断了连续性）→ 修改模板为 "没有找到相关信息。（问题：xxx）"
4. PowerShell 不支持 export 命令，git 直接调用即可

---

## [2026-03-31] T11: APScheduler 定时任务调度引擎

### 交付物
- src/scheduler/config.py: SCHEDULED_JOBS（3个任务 cron 配置）
- src/scheduler/jobs.py: run_daily_report / run_selection_analysis / run_llm_cost_report（stub + 日志 + db写入）
- src/scheduler/__init__.py: get_scheduler() / start_scheduler() / shutdown_scheduler() 模块级单例
- src/api/main.py: 新增4个调度器管理 API 路由
- tests/test_scheduler.py: 41项单元测试，全部 PASSED

### 关键实现细节

#### 模块级单例 + 懒加载模式
- APScheduler 相关类（BackgroundScheduler/MemoryJobStore/ThreadPoolExecutor）用 try/except ImportError 处理
- **即使安装了 APScheduler，也在模块顶部暴露这些名字**（设为 None 或真实值），这样 `patch("src.scheduler.MemoryJobStore")` 在两种情况下都能工作
- `_APSCHEDULER_AVAILABLE` 模块级标志控制所有降级路径

#### db_session 在 jobs.py 中的导入策略
- **必须在模块顶部导入** `from src.db.connection import db_session`（不能延迟导入）
- 原因：测试需要 `patch("src.scheduler.jobs.db_session", mock_cm)` — 只有模块级导入才能被 patch 覆盖
- 延迟导入（函数内 from x import y）无法被 patch，这是 T7 RAG engine 踩坑的重演

#### MagicMock 中 None 值的陷阱
- `_make_mock_job(job_id, next_run_time=None)` 中如果写 `job.next_run_time = next_run_time or default_value`，传 None 时会回退到默认值
- 正确写法：用哨兵默认值（模块级常量），直接 `job.next_run_time = next_run_time`，保留 None

#### FastAPI 路由中 APScheduler 不可用的处理
- 提取 `_get_scheduler_or_error()` 函数：返回 scheduler 或 raise HTTPException(503)
- 所有调度器 API 均调用此函数，统一处理降级

### 踩坑记录
1. `patch("src.scheduler.MemoryJobStore")` 失败 → 因为导入失败时只设了 `BackgroundScheduler = None`，没设 `MemoryJobStore = None` → 需要在 except 块中同时设置所有 3 个变量为 None
2. `job.next_run_time = None or default` 导致 None 被忽略 → 改用哨兵默认值 + 直接赋值
3. `from src.db.connection import db_session`（延迟导入）→ patch 不生效 → 改为模块顶部导入

---

## [2026-03-31] Task 9 — 卖家精灵MCP接入（阶段A Mock实现）

### 架构设计
- `SellerSpriteBase` ABC + `MockSellerSpriteClient` 实现，`get_client()` 工厂函数
- 模块级 dict 缓存 `_CACHE: dict[tuple, tuple[Any, datetime]]`，键为 `(method_name, normalized_args)`
- TTL = 24小时，过期自动删除并重新获取
- 错误重试：最多3次，前N-1次失败后 `time.sleep(2**attempt)` 指数退避，最后一次直接 raise

### loguru fallback 签名陷阱
**问题**：loguru 未安装时用 stdlib `logging` 模拟，但 fallback 方法签名只有 `(msg, **kwargs)`
而 loguru 风格调用为 `logger.info("msg {}", arg1, arg2)` → `TypeError`
**解决**：fallback 方法签名改为 `(msg, *args, **kwargs)`，并在内部 `msg.format(*args)`

### 重试逻辑设计
```python
for attempt in range(MAX_RETRIES):  # 0, 1, 2
    try:
        return func()
    except Error:
        if attempt == MAX_RETRIES - 1:  # 最后一次直接raise，不sleep
            raise
        time.sleep(2 ** attempt)  # 1s, 2s
```
这样 sleep 调用次数 = MAX_RETRIES - 1 = 2（不包括最后一次）

### 环境变量优先级
工厂函数 `get_client()` 读取优先级：
1. 环境变量 `SELLER_SPRITE_USE_MOCK`（覆盖settings，方便测试）
2. `pydantic settings`（需要 .env 文件）
3. 默认值 `True`（安全降级为 Mock）

### 测试隔离要点
- `autouse=True` fixture 每个测试前后清空 `_CACHE`（防止跨测试缓存污染）
- `autouse=True` fixture 每个测试结束后 restore `SELLER_SPRITE_MOCK_ERROR` 环境变量
- `patch("time.sleep")` 避免测试等待实际时间

### Python 3.14 datetime 警告
- `datetime.utcnow()` 在 Python 3.14 中 DeprecationWarning
- 应改为 `datetime.now(timezone.utc)`，但为保持兼容性暂不修改（警告不影响功能）

## [2026-03-31] T10 �� LLM���÷�װ����ü��

### ģ�鼶import vs ������lazy import���ؼ���ѵ��
- **����**��`check_daily_limit`��`send_feishu_warning`��`db_session`��`AgentRun`��`settings` ԭ���ں����ڲ� lazy import
- **֢״**��`patch("src.llm.client.check_daily_limit")` �� AttributeError��ģ��û�и����ԣ�
- **���**������Щ����������ģ�鼶��`try/except ImportError` �������������ڿɼ���patch ·����Ч
- **ԭ��**��������Ҫ�ڲ����� mock �����ƣ������Ǳ���ģ���ģ�鼶����

### ������д������㱣��
```python
# _record_agent_run �ڲ��� try/except��DBʧ�ܲ�������
# chat() ���� _record_agent_run ʱҲ�� try/except
# ԭ�򣺲��Կ��ܰ���������mock�����쳣����㱣��ȷ��chat()��Ȼ����
try:
    _record_agent_run(...)
except Exception as e:
    logger.warning(f"��¼ʧ�ܣ���������: {e}")
```

### PII ��������˳��
- ���滻���ÿ���4��4λ���֣������ⱻ�绰����ģʽ��ƥ��
- ���滻����
- ����滻�绰����
- `_filter_messages_pii()` �����Ϣ�б������޸�ԭʼ����

### ���ü��㾫��
- ʹ�� `float`������ ~1e-15 USD���㹻ʵ��ʹ�ã�
- �۸����λ��USD/1K tokens����per-token��
- ���㹫ʽ��`(tokens / 1000.0) * price_per_1k`

### ������ mock settings
```python
# settings ��ģ�鼶����������Ҫ create=True
with patch("src.llm.cost_monitor.settings") as mock_settings:
    mock_settings.MAX_DAILY_LLM_COST_USD = 50.0
    result = check_daily_limit()
```

### conftest mock_external_apis fixture
- `conftest.py` �� `mock_external_apis` fixture ���� True/False
- ���Ա�������Ҫ������fixture�ķ���ֵ��ֻ����Ϊ����ע�뵽��Ҫ mock �Ĳ���

## [2026-03-31] Task 8 — 飞书机器人问答功能

### handle_qa 完整流程设计
- 顺序：send_thinking → rag_query → _add_to_context → update_message
- send_thinking 失败不终止流程（try/except 继续）
- update_message 失败时降级为 send_text_message
- 所有外部异常统一返回'系统出错，请稍后重试'，禁止暴露堆栈

### 会话上下文（_CONTEXT）边界逻辑
- _CONTEXT 是模块级字典，键为 user_id，值为 list
- 每轮添加2条：先 user，后 assistant
- 清除判断在每次 _add_to_context 时执行（len > _MAX_CONTEXT_ROUNDS * 2）
- 边界：第11条（即第6轮 user 消息）触发清空 → 清空后添加 assistant → 结果1条
- 测试边界断言应使用 <= 2 而非 == 2

### update_message 使用 PATCH 而非 PUT
- 飞书 PUT /im/v1/messages/{message_id} 为全量替换
- 实现中使用 requests.patch 对应飞书 PATCH 接口
- URL 模板：_UPDATE_MSG_URL = f'{_FEISHU_API_BASE}/im/v1/messages/{message_id}'

### command_router 新增路由兼容性
- emergency_stop 优先级在 help 之前，在日报之前（因为紧急程度高）
- help 路由精确匹配（stripped.lower() in ('帮助', 'help')），不影响其他含'帮'字的消息
- '问：' 前缀支持需取 [2:] 而非 [1:]（两个字符）
- 原有 '报告' 路由保持有效（兼容性测试通过）

## [2026-03-31] T15 飞书多维表格（Bitable）同步模块

### httpx.Client 测试 mock 模式
```python
# mock httpx.Client（需模拟 context manager 协议）
mock_client = MagicMock()
mock_client.__enter__ = MagicMock(return_value=mock_client)
mock_client.__exit__ = MagicMock(return_value=False)
mock_client.post.return_value = mock_resp

with patch("httpx.Client", return_value=mock_client):
    result = bitable_client.create_record(...)
```

### 飞书 Bitable API URL 规律
- 单记录 CRUD：`/bitable/v1/apps/{app_token}/tables/{table_id}/records[/{record_id}]`
- 批量创建：`/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create`
- 列表翻页：通过 `has_more` + `page_token` 字段控制，page_size 最大 100

### 批量操作分批逻辑
- 飞书单次 batch_create 上限 50 条
- 超过时用 `range(0, len(records), BATCH_SIZE)` 切片，每批独立发送
- 某批失败时 `continue` 跳过，不影响其他批次，最终返回所有成功记录

### audit_logs 字段（再次确认）
- `id, action, actor, pre_state(JSON), post_state(JSON), created_at`
- `actor` 字段填写模块标识符（如 `bitable_sync`），非用户 ID
- 写操作中 audit log 失败不影响主流程（独立 try/except）

### 多批次 httpx.Client mock 技巧
```python
call_count = {"n": 0}
def client_factory(*args, **kwargs):
    idx = call_count["n"]
    call_count["n"] += 1
    return mock_clients[idx]

with patch("httpx.Client", side_effect=client_factory):
    result = bitable_client.batch_create_records(...)
```

## [2026-03-31] T16 — 审计日志系统 & 紧急停机（Kill Switch）

### 模块结构
- `src/utils/audit.py`：`log_action / get_recent_logs / audit_decorator`
- `src/utils/killswitch.py`：`is_stopped / activate_stop / deactivate_stop / check_killswitch / SystemStoppedError`
- `src/api/system.py`：4个 FastAPI 路由（GET status / POST stop / POST resume / GET audit-logs）
- `src/utils/__init__.py`：re-export 上述所有公共 API

### 关键设计决策

#### Kill Switch 无缓存原则
- `is_stopped()` 每次必须读 DB，绝不缓存
- 使用模块级 `db_session` 导入，测试 patch 可正常覆盖
- system_config 中使用多个辅助 key：`emergency_stop_reason/triggered_by/activated_at`

#### audit_logs 写入非阻塞模式
```python
try:
    with db_session() as session:
        session.add(AuditLog(...))
        session.commit()
except Exception as exc:
    logger.error("审计日志写入失败（非致命）: %s", exc)
    # 不 re-raise，保证主流程继续
```

#### _upsert_config 不依赖 PostgreSQL 特有语法
- 使用 `session.get(SystemConfig, key)` → 若 None 则 add，否则修改 value
- 避免 `pg_insert().on_conflict_do_update()`，确保 SQLite 兼容（测试环境）

#### check_killswitch 装饰器工厂模式
```python
@check_killswitch()   # 注意：必须带括号，是装饰器工厂
def run_agent():
    ...
```
- 工厂模式允许未来扩展参数（如指定豁免角色）

#### activate_stop 操作顺序（重要）
1. 写入 system_config（先持久化，保证状态可恢复）
2. 暂停调度任务（调用 _pause_all_jobs）
3. 写入 audit_log（记录，非阻塞）
4. 飞书通知（最后，非关键路径）

### system_config 表字段使用约定
- key `emergency_stop`: "true" / "false"（字符串）
- 存储 JSON 字段的 value 类型 = JSON，所以实际是 `"true"` 字符串
- `is_stopped()` 中同时处理 bool/str 两种情况

### 踩坑预防
1. `_upsert_config` 避免使用 PostgreSQL 特有的 UPSERT 语法（`insert().on_conflict_do_update()`），改用 get-then-set
2. killswitch.py 中导入 audit 模块时使用函数内导入（`from src.utils.audit import log_action`），避免循环导入
3. FastAPI 路由注册：在 main.py 中用 `from src.api.system import router; app.include_router(router)` 完成

### 测试结果
27/27 PASSED（test_audit.py: 9 + test_killswitch.py: 18）
