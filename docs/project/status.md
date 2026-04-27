# 项目状态

> 更新日期：2026-04-22

## 1. 当前总体状态
项目已具备内部运营系统的基础骨架，核心认证、主工作台页面、审批、系统管理与调度器后端接口均已存在。当前重点不再是扩散模块数量，而是持续收口页面与接口契约，并把缺口按优先级补齐。

## 2. 已完成事项
### 平台基础
- JWT 登录、刷新、当前用户信息
- 角色保护与 Boss 页面权限控制
- Axios 鉴权拦截器
- PostgreSQL / pgvector 模型基础
- Docker 部署基线

### 页面与业务能力
- 数据大盘首页已完成第一轮指标口径收口
- 广告看板与广告管理主流程已可用
- 订单列表与退货列表已完成字段归一化
- 订单详情前端映射已完成修复
- 审批中心、知识库审核、系统管理核心页面已存在

### 工程基线
- 已补充本地生成物忽略规则
- 已形成当前项目文档基线目录 `docs/project/`

## 3. 当前已知缺口
### P0
- `/system/schedules` 仍为占位页，前端尚未接入真实计划任务列表与操作能力

### P1
- 退货方向只有列表接口 `src/api/returns.py`，没有 detail endpoint
- 部分 Agent 对话历史与外部集成体验仍需后续优化

## 4. 为什么当前先做计划任务页
- 路由已存在：`src/frontend/src/App.tsx` 中已有 `/system/schedules`
- 后端 API 已存在：`src/api/main.py` 已提供 scheduler list / pause / resume / trigger
- 调度配置已存在：`src/scheduler/config.py` 已定义任务元数据
- 当前缺口主要在前端页面层，范围比退货详情闭合，适合继续做小步迭代

## 5. 最近完成
- 工作台第一批契约收口：Dashboard / Ads / Orders / Returns
- 修复订单详情响应归一化问题
- 补充 `.gitignore`，清理本地生成物残留
- 明确正式项目文档统一落在 `docs/project/`

## 6. 下一步
1. 实现 `/system/schedules` 独立计划任务页
2. 用契约测试锁住 scheduler API 与前端路由
3. 将 `SystemManagement` 中旧 scheduler mock 区块收口为真实入口
4. 完成后再评估退货详情链路是否进入下一轮

## 7. 当前风险与注意事项
- 计划任务页不要重复新建后端接口，应复用现有 `/api/scheduler/*`
- 不要把文档继续散落到 `docs/ai-agents/**` 或其他历史目录
- 不要顺手扩展 returns detail、本轮只记录不实现
- 继续保持 API key 仅在服务端、审批优先、最小改动范围三条基线
