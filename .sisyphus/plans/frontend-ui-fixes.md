# 前端 UI 问题修复计划

## TL;DR

> **Quick Summary**: 修复 PUDIWIND AI 系统前端的 17 个 UI 问题，包括 SKU 排名时间筛选、表头置顶、白色主题、文件预览功能、TopBar 标题、以及 Agent 聊天侧边栏。
> 
> **Deliverables**:
> - SKU 排名时间筛选扩展为 6 个选项
> - DataTable 表头 + 合计行 sticky 置顶
> - 白色主题配色修复
> - FilePreviewCard + FilePreviewModal 组件
> - FileSidebar 组件
> - AgentChat 页面集成文件预览和侧边栏
> - TopBar 标题逻辑修复
> 
> **Estimated Effort**: Medium (约 8-10 个任务)
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Task 1-3 → Task 4-6 → Task 7-9

---

## Context

### Original Request
用户逐个截图反馈了 17 个前端 UI 问题，要求收集完毕后统一修改。

### Interview Summary
**Key Discussions**:
- SKU 排名时间筛选需要从 2 个选项扩展到 6 个选项（与 TrendChart 一致）
- 表头和合计行需要 sticky 置顶
- 白色主题存在文字不可见、配色不协调问题
- 所有 Agent 都需要文件预览/下载功能
- Agent 分为两类：
  - **类型A（无侧边栏）**：AI主管、选品、Listing图片、产品上架
  - **类型B（有侧边栏+切换按钮）**：品牌路径规划、产品白皮书、竞品调研、用户画像、关键词库、Listing规划、库存监控、审计
- TopBar 对非 AI主管 Agent 显示"AI主管"是 bug

**Research Findings**:
- `TrendChart.tsx:40-47` 已有完整的 6 选项时间筛选实现
- `DataTable.tsx` 表头未使用 sticky 定位
- `index.css` 已有 dark/light 主题变量，但多处组件硬编码暗色
- `TopBar.tsx:52-63` 的 `getPageTitle` 对所有 `/agents` 路径返回"AI主管"
- `agents.ts` 定义了 Agent 元数据，但没有 `hasFileSidebar` 字段

### Metis Review
**Identified Gaps** (addressed):
- 白色主题范围不清晰 → 限定为用户截图中的页面 + 通用组件
- 文件预览类型未定义 → 使用 Mock 数据，支持 PDF 和图片即可
- 文件数据来源未确定 → 纯前端 Mock 静态数据
- SKU 合计行位置不确定 → 紧跟表头下方 sticky
- Agent 元数据缺少侧边栏标识 → 新增 `hasFileSidebar` 字段

---

## Work Objectives

### Core Objective
修复 17 个前端 UI 问题，提升用户体验和视觉一致性。

### Concrete Deliverables
- `src/frontend/src/pages/Dashboard.tsx` — SKU 时间筛选 6 选项
- `src/frontend/src/components/DataTable.tsx` — sticky 表头和合计行
- `src/frontend/src/index.css` — 白色主题 CSS 变量优化
- `src/frontend/src/components/Layout.tsx` — 主题感知背景色
- `src/frontend/src/components/Sidebar.tsx` — 白色主题文字颜色
- `src/frontend/src/components/TopBar.tsx` — Agent 标题逻辑修复
- `src/frontend/src/components/FilePreviewCard.tsx` — 新组件
- `src/frontend/src/components/FilePreviewModal.tsx` — 新组件
- `src/frontend/src/components/FileSidebar.tsx` — 新组件
- `src/frontend/src/pages/AgentChat.tsx` — 集成文件预览和侧边栏
- `src/frontend/src/data/agents.ts` — 新增 `hasFileSidebar` 字段

### Definition of Done
- [ ] `npm run build` 编译无错误
- [ ] 白色主题下所有文字可见
- [ ] SKU 排名有 6 个时间筛选选项
- [ ] 滚动 SKU 表格时表头和合计行保持可见
- [ ] Agent 聊天页面可显示文件卡片和预览
- [ ] 类型B Agent 显示可折叠的文件侧边栏
- [ ] TopBar 根据 Agent 类型显示正确标题

### Must Have
- 文件预览功能（使用 Mock 数据）
- 文件侧边栏及切换按钮（类型B Agent）
- 白色主题基本可用性修复

### Must NOT Have (Guardrails)
- ❌ 修改后端任何代码——纯前端任务
- ❌ 重构现有组件架构——只做修复和增量添加
- ❌ 为白色主题创建完整设计系统——只修复明显可见性问题
- ❌ 实现真实文件上传/下载后端——仅 UI 壳子 + Mock 数据
- ❌ 文件管理高级功能——不做编辑、版本管理、拖拽上传
- ❌ 文件侧边栏高级功能——不做搜索、分类、排序
- ❌ 全站扫描修复白色主题——只修用户反馈的页面

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (Vite + TypeScript)
- **Automated tests**: None (Phase 1 Mock，不做单元测试)
- **Framework**: N/A

### QA Policy
每个任务完成后必须运行 `npm run build` 验证编译通过。
UI 验证使用 Playwright 截图对比。
Evidence 保存到 `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`。

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately - 独立修复):
├── Task 1: SKU 排名时间筛选扩展 [quick]
├── Task 2: DataTable sticky 表头+合计行 [quick]
├── Task 3: TopBar Agent 标题逻辑修复 [quick]
└── Task 4: agents.ts 新增 hasFileSidebar 字段 [quick]

Wave 2 (After Wave 1 - 新组件开发):
├── Task 5: FilePreviewCard 组件 [visual-engineering]
├── Task 6: FilePreviewModal 组件 [visual-engineering]
└── Task 7: FileSidebar 组件 [visual-engineering]

Wave 3 (After Wave 2 - 集成+主题):
├── Task 8: AgentChat 集成文件预览和侧边栏 (depends: 4,5,6,7) [unspecified-high]
└── Task 9: 白色主题修复 (depends: 5,6,7) [visual-engineering]

Wave FINAL (After ALL tasks):
├── Task F1: npm run build 验证 [quick]
├── Task F2: Playwright 截图验证 [unspecified-high]
└── User okay before completion

Critical Path: Task 4 → Task 5-7 → Task 8 → Task 9 → F1-F2 → user okay
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 4 (Wave 1)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|------------|--------|
| 1 | - | - |
| 2 | - | - |
| 3 | - | - |
| 4 | - | 8 |
| 5 | - | 8, 9 |
| 6 | - | 8, 9 |
| 7 | - | 8, 9 |
| 8 | 4, 5, 6, 7 | F1, F2 |
| 9 | 5, 6, 7 | F1, F2 |

### Agent Dispatch Summary

- **Wave 1**: 4 tasks → T1-T4 all `quick`
- **Wave 2**: 3 tasks → T5-T7 all `visual-engineering`
- **Wave 3**: 2 tasks → T8 `unspecified-high`, T9 `visual-engineering`
- **FINAL**: 2 tasks → F1 `quick`, F2 `unspecified-high`

---

## TODOs

- [ ] 1. SKU 排名时间筛选扩展

  **What to do**:
  - 修改 `Dashboard.tsx` 中的 `TimeRange` 类型，从 `'site_today' | 'last_24h'` 扩展为 `'site_today' | 'last_24h' | 'this_week' | 'this_month' | 'this_year' | 'custom'`
  - 复用 `TrendChart.tsx:40-47` 的 `TIME_RANGES` 映射对象
  - 修改 SKU 排名区域的时间筛选按钮渲染逻辑（第 248-261 行）
  - 如果选择 `custom`，显示日期选择器（参考 TrendChart 实现）

  **Must NOT do**:
  - 不修改后端 API
  - 不修改 TrendChart 组件

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 简单的类型扩展和 UI 调整，单文件修改
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `src/frontend/src/components/TrendChart.tsx:16` - TimeRange 类型定义
  - `src/frontend/src/components/TrendChart.tsx:40-47` - TIME_RANGES 映射对象
  - `src/frontend/src/components/TrendChart.tsx:139-157` - 自定义日期选择器实现
  - `src/frontend/src/pages/Dashboard.tsx:50` - 当前 TimeRange 定义
  - `src/frontend/src/pages/Dashboard.tsx:248-261` - SKU 时间筛选按钮

  **Acceptance Criteria**:
  - [ ] `npm run build` 编译成功
  - [ ] SKU 排名区域显示 6 个时间筛选按钮

  **QA Scenarios**:
  ```
  Scenario: SKU 排名时间筛选显示 6 个选项
    Tool: Playwright
    Preconditions: 登录系统，进入数据大盘页面
    Steps:
      1. 导航到 http://localhost:5173/
      2. 滚动到 SKU 排名区域
      3. 检查时间筛选按钮数量
    Expected Result: 显示 6 个按钮（站点今天、最近24小时、本周、本月、本年、自定义）
    Evidence: .sisyphus/evidence/task-1-sku-time-range.png

  Scenario: 自定义时间选择器显示
    Tool: Playwright
    Preconditions: 登录系统，进入数据大盘页面
    Steps:
      1. 点击"自定义"按钮
      2. 检查是否显示日期选择器
    Expected Result: 显示开始日期和结束日期输入框
    Evidence: .sisyphus/evidence/task-1-custom-date-picker.png
  ```

  **Commit**: YES
  - Message: `feat(dashboard): extend SKU time range to 6 options`
  - Files: `src/frontend/src/pages/Dashboard.tsx`

- [ ] 2. DataTable sticky 表头+合计行

  **What to do**:
  - 修改 `DataTable.tsx` 的 `<thead>` 添加 `position: sticky; top: 0; z-index: 10;`
  - 修改合计行 `<tr>` 添加 `position: sticky; top: 40px; z-index: 9;`（40px 为表头高度）
  - 确保 sticky 元素有背景色，避免透明导致内容穿透
  - 调整父容器的 overflow 属性以支持 sticky

  **Must NOT do**:
  - 不修改 DataTable 的 props 接口
  - 不影响其他使用 DataTable 的页面

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: CSS 样式调整，单文件修改
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `src/frontend/src/components/DataTable.tsx:76-106` - thead 渲染
  - `src/frontend/src/components/DataTable.tsx:108-120` - 合计行渲染
  - `src/frontend/src/pages/Dashboard.tsx:264-279` - DataTable 使用方式

  **Acceptance Criteria**:
  - [ ] `npm run build` 编译成功
  - [ ] 滚动 SKU 表格时表头保持可见
  - [ ] 滚动 SKU 表格时合计行紧跟表头下方保持可见

  **QA Scenarios**:
  ```
  Scenario: 表头 sticky 效果
    Tool: Playwright
    Preconditions: 登录系统，SKU 排名有足够数据显示滚动条
    Steps:
      1. 导航到数据大盘
      2. 滚动 SKU 表格到底部
      3. 截图验证表头是否可见
    Expected Result: 表头行始终可见在表格顶部
    Evidence: .sisyphus/evidence/task-2-sticky-header.png

  Scenario: 合计行 sticky 效果
    Tool: Playwright
    Preconditions: 登录系统，SKU 排名有足够数据
    Steps:
      1. 导航到数据大盘
      2. 滚动 SKU 表格到底部
      3. 截图验证合计行是否可见
    Expected Result: 合计行始终可见在表头下方
    Evidence: .sisyphus/evidence/task-2-sticky-summary.png
  ```

  **Commit**: YES
  - Message: `fix(datatable): add sticky header and summary row`
  - Files: `src/frontend/src/components/DataTable.tsx`

- [ ] 3. TopBar Agent 标题逻辑修复

  **What to do**:
  - 修改 `TopBar.tsx` 的 `getPageTitle` 函数
  - 解析 `/agents/:type` 路径中的 type 参数
  - 根据 type 从 `AGENTS` 数组中获取对应的 Agent 名称
  - AI主管 (core_management) 显示"AI主管"，其他 Agent 显示其 `name` 字段

  **Must NOT do**:
  - 不修改其他路径的标题逻辑
  - 不引入新的状态管理

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 简单的逻辑修改，单文件
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `src/frontend/src/components/TopBar.tsx:52-63` - getPageTitle 函数
  - `src/frontend/src/data/agents.ts:31-44` - AGENTS 数组定义

  **Acceptance Criteria**:
  - [ ] `npm run build` 编译成功
  - [ ] AI主管页面 TopBar 显示"AI主管"
  - [ ] 选品Agent 页面 TopBar 显示"选品Agent"
  - [ ] 品牌路径规划 Agent 页面 TopBar 显示"品牌路径规划Agent"

  **QA Scenarios**:
  ```
  Scenario: AI主管标题正确
    Tool: Playwright
    Preconditions: 登录系统
    Steps:
      1. 导航到 /agents/core_management
      2. 检查 TopBar 标题文字
    Expected Result: 显示"AI主管"
    Evidence: .sisyphus/evidence/task-3-title-core.png

  Scenario: 选品Agent标题正确
    Tool: Playwright
    Preconditions: 登录系统
    Steps:
      1. 导航到 /agents/selection
      2. 检查 TopBar 标题文字
    Expected Result: 显示"选品Agent"
    Evidence: .sisyphus/evidence/task-3-title-selection.png

  Scenario: 品牌路径规划Agent标题正确
    Tool: Playwright
    Preconditions: 使用 boss 账号登录
    Steps:
      1. 导航到 /agents/brand_planning
      2. 检查 TopBar 标题文字
    Expected Result: 显示"品牌路径规划Agent"
    Evidence: .sisyphus/evidence/task-3-title-brand.png
  ```

  **Commit**: YES
  - Message: `fix(topbar): show correct agent title based on type`
  - Files: `src/frontend/src/components/TopBar.tsx`

- [ ] 4. agents.ts 新增 hasFileSidebar 字段

  **What to do**:
  - 在 `AgentCardInfo` 接口中新增 `hasFileSidebar: boolean` 字段
  - 为每个 Agent 配置该字段：
    - `hasFileSidebar: false`：core_management, selection, image_generation, product_listing
    - `hasFileSidebar: true`：brand_planning, whitepaper, competitor, persona, keyword_library, listing, inventory, auditor
  - 同步更新 `types.ts` 中的相关类型（如有必要）

  **Must NOT do**:
  - 不修改现有字段
  - 不删除任何 Agent 定义

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 简单的数据配置修改
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3)
  - **Blocks**: Task 8
  - **Blocked By**: None

  **References**:
  - `src/frontend/src/data/agents.ts:20-29` - AgentCardInfo 接口定义
  - `src/frontend/src/data/agents.ts:31-44` - AGENTS 数组

  **Acceptance Criteria**:
  - [ ] `npm run build` 编译成功
  - [ ] TypeScript 类型检查通过
  - [ ] 所有 Agent 都有 `hasFileSidebar` 字段

  **QA Scenarios**:
  ```
  Scenario: TypeScript 编译验证
    Tool: Bash
    Preconditions: 代码已保存
    Steps:
      1. cd src/frontend
      2. npm run build
    Expected Result: 编译成功，无类型错误
    Evidence: .sisyphus/evidence/task-4-build-success.txt
  ```

  **Commit**: YES
  - Message: `feat(agents): add hasFileSidebar field for sidebar config`
  - Files: `src/frontend/src/data/agents.ts`

- [ ] 5. FilePreviewCard 组件

  **What to do**:
  - 新建 `src/frontend/src/components/FilePreviewCard.tsx`
  - 组件接收 props: `{ fileName: string; fileType: 'pdf' | 'image' | 'doc' | 'excel'; fileSize: string; fileUrl: string; onPreview: () => void; onDownload: () => void }`
  - 显示文件图标（根据 fileType）、文件名、文件大小
  - 提供"预览"和"下载"按钮
  - 支持 dark/light 主题
  - 使用玻璃拟态样式，与系统风格一致

  **Must NOT do**:
  - 不实现真实的文件上传
  - 不处理文件数据读取

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: UI 组件开发，需要视觉设计
  - **Skills**: `["frontend-design"]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7)
  - **Blocks**: Task 8, Task 9
  - **Blocked By**: None

  **References**:
  - `src/frontend/src/index.css:42-46` - glass 样式定义
  - `src/frontend/src/components/DataTable.tsx` - 组件结构参考
  - Lucide React 图标：FileText, Image, FileSpreadsheet, File

  **Acceptance Criteria**:
  - [ ] `npm run build` 编译成功
  - [ ] 组件正确导出
  - [ ] 支持 4 种文件类型图标
  - [ ] dark/light 主题下可见

  **QA Scenarios**:
  ```
  Scenario: FilePreviewCard 渲染 PDF 文件
    Tool: Playwright
    Preconditions: 组件集成到测试页面
    Steps:
      1. 渲染 FilePreviewCard with fileType='pdf'
      2. 检查是否显示 PDF 图标
      3. 检查文件名和大小显示
    Expected Result: 显示 PDF 图标、文件名、大小、预览/下载按钮
    Evidence: .sisyphus/evidence/task-5-card-pdf.png

  Scenario: FilePreviewCard dark/light 主题
    Tool: Playwright
    Preconditions: 组件已渲染
    Steps:
      1. 在 dark 主题下截图
      2. 切换到 light 主题
      3. 再次截图
    Expected Result: 两种主题下文字都可见，样式协调
    Evidence: .sisyphus/evidence/task-5-card-themes.png
  ```

  **Commit**: NO (groups with Task 6, 7)

- [ ] 6. FilePreviewModal 组件

  **What to do**:
  - 新建 `src/frontend/src/components/FilePreviewModal.tsx`
  - 组件接收 props: `{ isOpen: boolean; onClose: () => void; fileName: string; fileType: string; fileUrl: string }`
  - 全屏模态框，带半透明黑色背景
  - 顶部显示文件名和关闭按钮
  - 中间区域：
    - PDF：使用 `<iframe>` 或 `<embed>` 预览
    - 图片：使用 `<img>` 标签
    - 其他：显示"不支持预览，请下载查看"
  - 底部提供下载按钮
  - 支持 ESC 键关闭

  **Must NOT do**:
  - 不引入第三方 PDF 库
  - 不实现文件编辑功能

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: 模态框 UI 开发
  - **Skills**: `["frontend-design"]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 7)
  - **Blocks**: Task 8, Task 9
  - **Blocked By**: None

  **References**:
  - `src/frontend/src/components/TopBar.tsx:104-157` - 通知面板弹出层参考
  - Motion 库用于动画效果

  **Acceptance Criteria**:
  - [ ] `npm run build` 编译成功
  - [ ] 模态框可打开/关闭
  - [ ] PDF 文件可在 iframe 中预览
  - [ ] 图片文件可直接显示
  - [ ] ESC 键可关闭模态框

  **QA Scenarios**:
  ```
  Scenario: 预览 PDF 文件
    Tool: Playwright
    Preconditions: 模态框打开，fileType='pdf'
    Steps:
      1. 触发 onPreview 打开模态框
      2. 检查是否显示 iframe
      3. 检查文件名是否正确
    Expected Result: 显示 PDF 预览区域，文件名正确
    Evidence: .sisyphus/evidence/task-6-modal-pdf.png

  Scenario: 预览图片文件
    Tool: Playwright
    Preconditions: 模态框打开，fileType='image'
    Steps:
      1. 触发 onPreview 打开模态框
      2. 检查是否显示 img 标签
    Expected Result: 显示图片预览
    Evidence: .sisyphus/evidence/task-6-modal-image.png

  Scenario: ESC 键关闭
    Tool: Playwright
    Preconditions: 模态框已打开
    Steps:
      1. 按下 ESC 键
      2. 检查模态框是否关闭
    Expected Result: 模态框关闭
    Evidence: .sisyphus/evidence/task-6-modal-esc.png
  ```

  **Commit**: NO (groups with Task 5, 7)

- [ ] 7. FileSidebar 组件

  **What to do**:
  - 新建 `src/frontend/src/components/FileSidebar.tsx`
  - 组件接收 props: `{ isOpen: boolean; onToggle: () => void; files: FileItem[]; onFilePreview: (file: FileItem) => void }`
  - `FileItem` 类型: `{ id: string; name: string; type: string; size: string; createdAt: string; url: string }`
  - 侧边栏宽度 280px，可折叠
  - 顶部：标题"生成文件" + 折叠按钮
  - 内容区：文件列表，每项显示图标、文件名、日期、大小
  - 点击文件项触发预览
  - 支持 dark/light 主题
  - 使用玻璃拟态样式

  **Must NOT do**:
  - 不实现文件搜索
  - 不实现文件分类
  - 不实现文件排序

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: 侧边栏 UI 开发
  - **Skills**: `["frontend-design"]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6)
  - **Blocks**: Task 8, Task 9
  - **Blocked By**: None

  **References**:
  - `src/frontend/src/components/Sidebar.tsx` - 主侧边栏结构参考
  - `src/frontend/src/pages/AgentChat.tsx:109-127` - 左侧会话列表面板参考

  **Acceptance Criteria**:
  - [ ] `npm run build` 编译成功
  - [ ] 侧边栏可展开/折叠
  - [ ] 文件列表正确渲染
  - [ ] 点击文件项触发回调
  - [ ] dark/light 主题下可见

  **QA Scenarios**:
  ```
  Scenario: 侧边栏展开状态
    Tool: Playwright
    Preconditions: isOpen=true，files 有 3 个文件
    Steps:
      1. 渲染 FileSidebar
      2. 检查宽度是否为 280px
      3. 检查文件列表是否显示 3 项
    Expected Result: 侧边栏展开，显示 3 个文件
    Evidence: .sisyphus/evidence/task-7-sidebar-open.png

  Scenario: 侧边栏折叠状态
    Tool: Playwright
    Preconditions: isOpen=false
    Steps:
      1. 渲染 FileSidebar with isOpen=false
      2. 检查侧边栏是否隐藏或收窄
    Expected Result: 侧边栏折叠/隐藏
    Evidence: .sisyphus/evidence/task-7-sidebar-closed.png

  Scenario: 点击文件触发预览
    Tool: Playwright
    Preconditions: 侧边栏展开，有文件
    Steps:
      1. 点击第一个文件项
      2. 检查 onFilePreview 是否被调用
    Expected Result: 触发预览回调
    Evidence: .sisyphus/evidence/task-7-file-click.png
  ```

  **Commit**: YES (groups Task 5, 6, 7)
  - Message: `feat(components): add file preview and sidebar components`
  - Files: `FilePreviewCard.tsx, FilePreviewModal.tsx, FileSidebar.tsx`

- [ ] 8. AgentChat 集成文件预览和侧边栏

  **What to do**:
  - 修改 `AgentChat.tsx`，导入新组件
  - 添加 Mock 文件数据（用于测试）
  - 根据 `agentInfo.hasFileSidebar` 决定是否渲染 FileSidebar
  - 为类型B Agent 添加侧边栏切换按钮（右上角）
  - 在聊天消息中集成 FilePreviewCard（模拟 AI 回复中附带文件）
  - 管理 FilePreviewModal 的打开/关闭状态
  - 确保布局响应式：侧边栏展开时聊天区域收窄

  **Must NOT do**:
  - 不修改后端 API
  - 不实现真实文件数据获取

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 复杂的状态管理和组件集成
  - **Skills**: `["frontend-design"]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3
  - **Blocks**: F1, F2
  - **Blocked By**: Task 4, 5, 6, 7

  **References**:
  - `src/frontend/src/pages/AgentChat.tsx` - 当前实现
  - `src/frontend/src/data/agents.ts` - Agent 配置（含 hasFileSidebar）
  - `src/frontend/src/components/FilePreviewCard.tsx` - 文件卡片组件
  - `src/frontend/src/components/FilePreviewModal.tsx` - 预览模态框
  - `src/frontend/src/components/FileSidebar.tsx` - 文件侧边栏

  **Acceptance Criteria**:
  - [ ] `npm run build` 编译成功
  - [ ] AI主管页面：显示文件预览卡片，无侧边栏
  - [ ] 品牌路径规划页面：显示文件预览卡片 + 侧边栏 + 切换按钮
  - [ ] 选品Agent页面：显示文件预览卡片，无侧边栏
  - [ ] 点击文件卡片可打开预览模态框

  **QA Scenarios**:
  ```
  Scenario: AI主管无侧边栏
    Tool: Playwright
    Preconditions: 登录系统
    Steps:
      1. 导航到 /agents/core_management
      2. 检查是否有文件侧边栏
      3. 检查聊天区域是否有 Mock 文件卡片
    Expected Result: 无侧边栏，聊天区有文件卡片
    Evidence: .sisyphus/evidence/task-8-core-no-sidebar.png

  Scenario: 品牌路径规划有侧边栏
    Tool: Playwright
    Preconditions: 使用 boss 账号登录
    Steps:
      1. 导航到 /agents/brand_planning
      2. 检查是否有文件侧边栏
      3. 检查是否有切换按钮
    Expected Result: 显示侧边栏和切换按钮
    Evidence: .sisyphus/evidence/task-8-brand-with-sidebar.png

  Scenario: 侧边栏切换
    Tool: Playwright
    Preconditions: 在品牌路径规划页面
    Steps:
      1. 点击切换按钮
      2. 检查侧边栏是否收起
      3. 再次点击
      4. 检查侧边栏是否展开
    Expected Result: 侧边栏可切换显示/隐藏
    Evidence: .sisyphus/evidence/task-8-sidebar-toggle.png

  Scenario: 文件预览模态框
    Tool: Playwright
    Preconditions: 聊天区有文件卡片
    Steps:
      1. 点击文件卡片的"预览"按钮
      2. 检查是否打开模态框
      3. 按 ESC 关闭
    Expected Result: 模态框正确打开/关闭
    Evidence: .sisyphus/evidence/task-8-preview-modal.png
  ```

  **Commit**: YES
  - Message: `feat(agent-chat): integrate file preview and sidebar`
  - Files: `src/frontend/src/pages/AgentChat.tsx`

- [ ] 9. 白色主题修复

  **What to do**:
  - 修改 `index.css` 中 light 主题的 CSS 变量
  - 修改 `Layout.tsx` 的背景色，使用主题变量而非硬编码
  - 修改 `Sidebar.tsx` 中硬编码的颜色，改用主题变量
  - 修改 `TopBar.tsx` 中硬编码的颜色
  - 修改 `Dashboard.tsx` 中硬编码的颜色
  - 修改 `AgentChat.tsx` 中硬编码的颜色
  - 修改新组件（FilePreviewCard, FilePreviewModal, FileSidebar）确保主题兼容
  - 白色主题目标配色：白底、蓝色强调、深色文字

  **Must NOT do**:
  - 不创建完整的设计系统
  - 不修改所有页面——只修主要页面和通用组件

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: 主题和样式修复
  - **Skills**: `["frontend-design", "tailwind-design-system"]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (after Task 8)
  - **Blocks**: F1, F2
  - **Blocked By**: Task 5, 6, 7

  **References**:
  - `src/frontend/src/index.css:5-26` - 主题 CSS 变量
  - `src/frontend/src/components/Layout.tsx:10` - 硬编码 bg-[#0a0a1a]
  - `src/frontend/src/components/Sidebar.tsx:103` - 硬编码暗色
  - `src/frontend/src/pages/Dashboard.tsx:179` - 硬编码 text-gray-100
  - `src/frontend/src/pages/AgentChat.tsx:108` - 硬编码 bg-[#0a0a1a]
  - 用户提供的白色主题参考图

  **Acceptance Criteria**:
  - [ ] `npm run build` 编译成功
  - [ ] 白色主题下 Sidebar 文字可见
  - [ ] 白色主题下 TopBar 文字可见
  - [ ] 白色主题下 Dashboard 内容可见
  - [ ] 白色主题下 AgentChat 内容可见
  - [ ] 整体配色协调（白底、蓝调）

  **QA Scenarios**:
  ```
  Scenario: Sidebar 白色主题
    Tool: Playwright
    Preconditions: 切换到白色主题
    Steps:
      1. 检查 Sidebar 背景色
      2. 检查导航文字颜色
      3. 检查 PUDIWIND AI logo 可见性
    Expected Result: 背景白/浅色，文字深色可见
    Evidence: .sisyphus/evidence/task-9-sidebar-light.png

  Scenario: Dashboard 白色主题
    Tool: Playwright
    Preconditions: 切换到白色主题
    Steps:
      1. 导航到数据大盘
      2. 检查 KPI 卡片可见性
      3. 检查 SKU 表格可见性
    Expected Result: 所有内容清晰可见，配色协调
    Evidence: .sisyphus/evidence/task-9-dashboard-light.png

  Scenario: AgentChat 白色主题
    Tool: Playwright
    Preconditions: 切换到白色主题
    Steps:
      1. 导航到 AI主管
      2. 检查聊天界面可见性
      3. 检查文件卡片可见性
    Expected Result: 聊天内容清晰可见
    Evidence: .sisyphus/evidence/task-9-chat-light.png
  ```

  **Commit**: YES
  - Message: `fix(theme): improve light mode visibility across components`
  - Files: `index.css, Layout.tsx, Sidebar.tsx, TopBar.tsx, Dashboard.tsx, AgentChat.tsx, FilePreviewCard.tsx, FilePreviewModal.tsx, FileSidebar.tsx`

---

## Final Verification Wave

- [ ] F1. **npm run build 验证** — `quick`
  在 `src/frontend/` 目录运行 `npm run build`，确保无编译错误。
  Output: `BUILD SUCCESS | FAIL`

- [ ] F2. **Playwright 截图验证** — `unspecified-high` (+ `playwright` skill)
  启动开发服务器，使用 Playwright 截图验证：
  1. 数据大盘 SKU 排名时间筛选显示 6 个选项
  2. SKU 表格滚动时表头和合计行保持可见
  3. 白色主题下 Sidebar、TopBar、Dashboard 文字可见
  4. AI主管聊天页面显示文件卡片（Mock）
  5. 品牌路径规划 Agent 显示文件侧边栏和切换按钮
  6. TopBar 在不同 Agent 页面显示正确标题
  Evidence: `.sisyphus/evidence/final-qa/`

---

## Commit Strategy

| 任务范围 | Commit Message | Files |
|----------|----------------|-------|
| Task 1 | `feat(dashboard): extend SKU time range to 6 options` | Dashboard.tsx |
| Task 2 | `fix(datatable): add sticky header and summary row` | DataTable.tsx |
| Task 3 | `fix(topbar): show correct agent title` | TopBar.tsx |
| Task 4 | `feat(agents): add hasFileSidebar field` | agents.ts, types.ts |
| Task 5-7 | `feat(components): add file preview and sidebar components` | FilePreviewCard.tsx, FilePreviewModal.tsx, FileSidebar.tsx |
| Task 8 | `feat(agent-chat): integrate file preview and sidebar` | AgentChat.tsx |
| Task 9 | `fix(theme): improve light mode visibility` | index.css, Layout.tsx, Sidebar.tsx, ... |

---

## Success Criteria

### Verification Commands
```bash
cd src/frontend && npm run build  # Expected: Build successful
```

### Final Checklist
- [ ] SKU 排名显示 6 个时间筛选选项
- [ ] 滚动 SKU 表格时表头+合计行 sticky
- [ ] 白色主题下文字可见、配色协调
- [ ] AI主管聊天可显示文件卡片并预览
- [ ] 类型B Agent 显示文件侧边栏（可折叠）
- [ ] TopBar 根据 Agent 显示正确标题
- [ ] `npm run build` 无错误
