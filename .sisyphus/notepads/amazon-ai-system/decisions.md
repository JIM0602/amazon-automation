# Decisions — amazon-ai-system

## [2026-03-31] 架构决策

### 决策1：T1云服务器处理方式
- 结论：产出指南文档+脚本，由JIM自行操作
- 理由：无法代码自动化购买云服务器，但可以提供完整的步骤指南

### 决策2：Wave 1执行顺序
- T1：产出文档+脚本（不阻塞其他任务）
- T2/T3/T4/T5/T6：并行执行，全部可在本地开发

### 决策3：测试策略
- 所有外部API调用使用--mock-external-apis标记
- pytest fixture在conftest.py中统一管理
- 集成测试在tests/integration/目录中单独管理
## 2026-03-31
- 仅修复 `tests/integration/test_concurrent.py`，不改 `src/` 生产代码。
- RAG 并发测试改为验证 `RAGEngine` 实例创建本身的线程安全，不依赖不存在的 `get_engine()`。
