# 白色主题全局修复计划

## TL;DR

> **Quick Summary**: 修复白色主题下多个页面显示异常的问题，包括趋势图时间筛选、Agent聊天界面、Agent矩阵页面等
> 
> **Deliverables**:
> - TrendChart.tsx 白色主题适配
> - AgentChat.tsx 白色主题适配
> - ChatWindow.tsx 白色主题适配
> - ConversationList.tsx 白色主题适配
> - AgentCatalog.tsx 白色主题适配
> - FileSidebar.tsx 白色主题适配
> - AdDashboard.tsx 白色主题适配
> 
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Task 1 → Task 2 → Task 3 → F1

---

## Context

### Original Request
用户反馈白色主题切换后多个页面显示不正确：
1. 数据大盘趋势图右上角时间筛选按钮区域（灰色背景看不清文字）
2. AI主管和其他Agent的聊天界面没有跟随变成白色主题
3. AI Agent矩阵页面的标题、Agent名称、标签、搜索框等文字看不清

### 参考案例风格
- 白色/浅灰背景
- 深色文字（标题、正文）
- 蓝色强调色（链接、按钮）
- 卡片有浅色边框和阴影
- 整体干净清爽

### 修复原则
- 将硬编码的深色样式改为 `dark:` 前缀版本
- 白色主题：白底、深色文字、蓝色强调
- 深色主题：保持不变（已有样式移到 `dark:` 前缀下）

---

## Work Objectives

### Core Objective
修复所有页面在白色主题下的显示问题，确保文字可见、背景正确、交互元素清晰

### Concrete Deliverables
- 7个文件的样式修复

### Definition of Done
- [ ] `npm run build` 通过
- [ ] 白色主题下所有页面文字清晰可见
- [ ] 深色主题保持原有效果不变

### Must Have
- 所有硬编码深色背景改为响应式（白色主题用浅色，深色主题用深色）
- 所有硬编码浅色文字改为响应式（白色主题用深色，深色主题用浅色）

### Must NOT Have (Guardrails)
- 不修改任何功能逻辑
- 不修改深色主题的视觉效果
- 不添加新的组件或文件
- 不修改 index.css 中的 CSS 变量

---

## Verification Strategy

### Test Decision
- **Automated tests**: None (纯样式修改)
- **Framework**: N/A

### QA Policy
每个任务完成后通过 `npm run build` 验证编译通过

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (数据大盘相关):
├── Task 1: TrendChart.tsx 白色主题修复 [quick]
└── Task 2: AdDashboard.tsx 白色主题修复 [quick]

Wave 2 (Agent聊天相关):
├── Task 3: AgentChat.tsx 白色主题修复 [quick]
├── Task 4: ChatWindow.tsx 白色主题修复 [quick]
├── Task 5: ConversationList.tsx 白色主题修复 [quick]
└── Task 6: FileSidebar.tsx 白色主题修复 [quick]

Wave 3 (Agent矩阵):
└── Task 7: AgentCatalog.tsx 白色主题修复 [quick]

Wave FINAL:
└── F1: npm run build 验证
```

---

## TODOs

- [x] 1. TrendChart.tsx 白色主题修复

  **What to do**:
  修改以下硬编码深色样式为响应式：
  
  1. 外层容器：
     - `border border-white/5 bg-white/5` → `border border-gray-200 bg-white/50 dark:border-white/5 dark:bg-white/5`
  
  2. 自定义日期输入框容器：
     - `text-gray-300` → `text-gray-700 dark:text-gray-300`
  
  3. 日期输入框：
     - `bg-black/40 border border-white/10` → `bg-gray-100 dark:bg-black/40 border border-gray-200 dark:border-white/10`
     - `focus:border-white/20` → `focus:border-blue-500 dark:focus:border-white/20`
     - 删除 `style={{ colorScheme: 'dark' }}`，改为 `dark:[color-scheme:dark]`
  
  4. 时间筛选按钮容器：
     - `bg-black/40 rounded-lg p-1 border border-white/10` → `bg-gray-100 dark:bg-black/40 rounded-lg p-1 border border-gray-200 dark:border-white/10`
  
  5. 时间筛选按钮（选中态）：
     - `bg-white/10 text-white` → `bg-white text-blue-600 dark:bg-white/10 dark:text-white`
  
  6. 时间筛选按钮（未选中态）：
     - `text-gray-400 hover:text-gray-200 hover:bg-white/5` → `text-gray-500 hover:text-gray-900 hover:bg-white/50 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-white/5`

  **Must NOT do**:
  - 不修改图表内部样式（Recharts 组件）
  - 不修改指标选择按钮样式（已经有动态颜色）

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: F1
  - **Blocked By**: None

  **References**:
  - `src/frontend/src/components/TrendChart.tsx:125-175` - 需要修改的区域

  **Acceptance Criteria**:
  - [ ] `npm run build` 通过
  - [ ] 白色主题下时间筛选按钮文字清晰可见
  - [ ] 深色主题下效果保持不变

  **Commit**: NO (最后统一提交)

---

- [x] 2. AdDashboard.tsx 白色主题修复

  **What to do**:
  修改以下硬编码深色样式为响应式：
  
  1. 页面容器：
     - `text-gray-100` → `text-gray-900 dark:text-gray-100`
  
  2. KPI卡片时间筛选按钮容器：
     - `bg-black/40 rounded-lg p-1 border border-white/10` → `bg-gray-100 dark:bg-black/40 rounded-lg p-1 border border-gray-200 dark:border-white/10`
  
  3. KPI卡片时间筛选按钮（选中态）：
     - `bg-white/10 text-white` → `bg-white text-blue-600 dark:bg-white/10 dark:text-white`
  
  4. KPI卡片时间筛选按钮（未选中态）：
     - `text-gray-400 hover:text-gray-200 hover:bg-white/5` → `text-gray-500 hover:text-gray-900 hover:bg-white/50 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-white/5`
  
  5. KPI卡片：
     - `border border-white/5 bg-white/5` → `border border-gray-200 bg-white/50 dark:border-white/5 dark:bg-white/5`
     - 图标容器 `bg-white/5 rounded-lg border border-white/10` → `bg-gray-100/50 dark:bg-white/5 rounded-lg border border-gray-200/50 dark:border-white/10`
     - 标题 `text-gray-400` → `text-gray-500 dark:text-gray-400`
  
  6. 趋势图区域（与 Task 1 类似的修改）：
     - 外层容器、日期输入框、时间筛选按钮
  
  7. 设置按钮：
     - `bg-white/5 border border-white/10 hover:bg-white/10 text-gray-300` → `bg-gray-100 dark:bg-white/5 border border-gray-200 dark:border-white/10 hover:bg-gray-200 dark:hover:bg-white/10 text-gray-600 dark:text-gray-300`
  
  8. 设置弹出框：
     - `bg-gray-900 border border-white/10` → `bg-white dark:bg-gray-900 border border-gray-200 dark:border-white/10`
     - 标题 `text-gray-200` → `text-gray-700 dark:text-gray-200`
     - 选项文字 `text-gray-300` → `text-gray-600 dark:text-gray-300`
  
  9. 广告活动排名区域时间筛选按钮（同上）

  **Must NOT do**:
  - 不修改图表内部样式
  - 不修改数据表格样式（DataTable 组件）

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: F1
  - **Blocked By**: None

  **References**:
  - `src/frontend/src/pages/AdDashboard.tsx:272-560` - 需要修改的区域

  **Acceptance Criteria**:
  - [ ] `npm run build` 通过
  - [ ] 白色主题下 KPI 卡片、时间筛选、设置弹窗显示正确
  - [ ] 深色主题下效果保持不变

  **Commit**: NO

---

- [x] 3. AgentChat.tsx 白色主题修复

  **What to do**:
  修改以下硬编码深色样式为响应式：
  
  1. 主容器：
     - `bg-[#0a0a1a] text-white` → `bg-gray-50 text-gray-900 dark:bg-[#0a0a1a] dark:text-white`
  
  2. 左侧会话列表容器：
     - `border-r border-[var(--color-glass-border)] bg-[var(--color-glass)]` 保持不变（已用 CSS 变量）
  
  3. Agent 信息头部：
     - `bg-[rgba(255,255,255,0.08)]` → `bg-gray-100 dark:bg-[rgba(255,255,255,0.08)]`
     - `text-white` → `text-gray-900 dark:text-white`
     - `text-gray-400` → `text-gray-500 dark:text-gray-400`
  
  4. 侧边栏切换按钮区域：
     - `border-b border-[var(--color-glass-border)] bg-[var(--color-glass)]` 保持不变
     - 按钮未选中态 `text-gray-400 hover:text-white hover:bg-white/10` → `text-gray-500 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-white dark:hover:bg-white/10`
  
  5. AI 生成文件区域：
     - `border-t border-[var(--color-glass-border)] bg-[var(--color-glass)]` 保持不变
     - `text-gray-400` → `text-gray-500 dark:text-gray-400`
  
  6. NotFoundState 和 AccessDeniedState：
     - `bg-[#0a0a1a] text-white` → `bg-gray-50 text-gray-900 dark:bg-[#0a0a1a] dark:text-white`
     - `border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.05)]` → `border-gray-200 bg-white dark:border-[rgba(255,255,255,0.1)] dark:bg-[rgba(255,255,255,0.05)]`
     - 内部文字颜色同样改为响应式

  **Must NOT do**:
  - 不修改 themeVars 常量
  - 不修改 MOCK_FILES 数据

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 6)
  - **Blocks**: F1
  - **Blocked By**: None

  **References**:
  - `src/frontend/src/pages/AgentChat.tsx:20-46` - NotFoundState, AccessDeniedState
  - `src/frontend/src/pages/AgentChat.tsx:118-199` - 主要渲染区域

  **Acceptance Criteria**:
  - [ ] `npm run build` 通过
  - [ ] 白色主题下 Agent 聊天页面背景为白色/浅灰
  - [ ] 深色主题下效果保持不变

  **Commit**: NO

---

- [x] 4. ChatWindow.tsx 白色主题修复

  **What to do**:
  修改以下硬编码深色样式为响应式：
  
  1. 主容器：
     - `bg-[#0a0a1a]` → `bg-white dark:bg-[#0a0a1a]`
     - `border border-[rgba(255,255,255,0.1)]` → `border border-gray-200 dark:border-[rgba(255,255,255,0.1)]`
  
  2. 头部：
     - `border-b border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.02)]` → `border-b border-gray-200 bg-gray-50 dark:border-[rgba(255,255,255,0.1)] dark:bg-[rgba(255,255,255,0.02)]`
     - 图标容器 `bg-[rgba(255,255,255,0.05)]` → `bg-gray-100 dark:bg-[rgba(255,255,255,0.05)]`
     - Agent 名称 `text-white` → `text-gray-900 dark:text-white`
     - `text-gray-400` → `text-gray-500 dark:text-gray-400`
  
  3. 消息区域空状态：
     - `bg-[rgba(255,255,255,0.05)] text-gray-400` → `bg-gray-100 text-gray-500 dark:bg-[rgba(255,255,255,0.05)] dark:text-gray-400`
     - `text-gray-500` → `text-gray-400 dark:text-gray-500`
  
  4. AI 消息气泡：
     - `bg-[rgba(255,255,255,0.05)] backdrop-blur-md border border-[rgba(255,255,255,0.05)] text-gray-200` → `bg-gray-100 border border-gray-200 text-gray-700 dark:bg-[rgba(255,255,255,0.05)] dark:backdrop-blur-md dark:border-[rgba(255,255,255,0.05)] dark:text-gray-200`
  
  5. AI 头像：
     - `bg-[rgba(255,255,255,0.1)]` → `bg-gray-100 dark:bg-[rgba(255,255,255,0.1)]`
  
  6. 正在输入指示器：
     - `bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.05)]` → `bg-gray-100 border border-gray-200 dark:bg-[rgba(255,255,255,0.05)] dark:border-[rgba(255,255,255,0.05)]`
  
  7. 输入区域：
     - `border-t border-[rgba(255,255,255,0.1)] bg-[rgba(0,0,0,0.2)]` → `border-t border-gray-200 bg-gray-50 dark:border-[rgba(255,255,255,0.1)] dark:bg-[rgba(0,0,0,0.2)]`
     - 输入框容器 `bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)]` → `bg-white border border-gray-200 dark:bg-[rgba(255,255,255,0.05)] dark:border-[rgba(255,255,255,0.1)]`
     - 输入框文字 `text-white` → `text-gray-900 dark:text-white`
     - 发送按钮禁用态 `bg-[rgba(255,255,255,0.05)] text-gray-500` → `bg-gray-100 text-gray-400 dark:bg-[rgba(255,255,255,0.05)] dark:text-gray-500`

  **Must NOT do**:
  - 不修改用户消息气泡样式（蓝色背景保持不变）
  - 不修改 Markdown 渲染样式

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 3, 5, 6)
  - **Blocks**: F1
  - **Blocked By**: None

  **References**:
  - `src/frontend/src/components/ChatWindow.tsx:93-226` - 主要渲染区域

  **Acceptance Criteria**:
  - [ ] `npm run build` 通过
  - [ ] 白色主题下聊天窗口背景为白色，AI消息可读
  - [ ] 深色主题下效果保持不变

  **Commit**: NO

---

- [x] 5. ConversationList.tsx 白色主题修复

  **What to do**:
  修改以下硬编码深色样式为响应式：
  
  1. 主容器：
     - `bg-[#0a0a1a]` → `bg-white dark:bg-[#0a0a1a]`
  
  2. 新建对话按钮区域边框：
     - `border-b border-[rgba(255,255,255,0.1)]` → `border-b border-gray-200 dark:border-[rgba(255,255,255,0.1)]`
  
  3. 加载中/暂无记录文字：
     - `text-gray-500` 保持不变（在两个主题下都可见）
  
  4. 对话项选中态：
     - `bg-[rgba(255,255,255,0.1)] text-white` → `bg-blue-50 text-blue-600 dark:bg-[rgba(255,255,255,0.1)] dark:text-white`
  
  5. 对话项未选中态：
     - `text-gray-400 hover:bg-[rgba(255,255,255,0.05)] hover:text-white` → `text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-[rgba(255,255,255,0.05)] dark:hover:text-white`

  **Must NOT do**:
  - 不修改新建对话按钮样式（蓝色背景）

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 3, 4, 6)
  - **Blocks**: F1
  - **Blocked By**: None

  **References**:
  - `src/frontend/src/components/ConversationList.tsx:42-82` - 主要渲染区域

  **Acceptance Criteria**:
  - [ ] `npm run build` 通过
  - [ ] 白色主题下对话列表背景为白色，文字清晰
  - [ ] 深色主题下效果保持不变

  **Commit**: NO

---

- [x] 6. FileSidebar.tsx 白色主题修复

  **What to do**:
  修改以下硬编码深色样式为响应式：
  
  1. 侧边栏标题：
     - `text-white` → `text-gray-900 dark:text-white`
  
  2. 关闭按钮：
     - `text-gray-400 hover:text-white` → `text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white`
  
  3. 文件项文件名：
     - `text-white` → `text-gray-900 dark:text-white`

  **Must NOT do**:
  - 不修改图标颜色
  - 不修改文件大小、日期文字颜色（gray-400 两个主题都可见）

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 3, 4, 5)
  - **Blocks**: F1
  - **Blocked By**: None

  **References**:
  - `src/frontend/src/components/FileSidebar.tsx:39-72` - 主要渲染区域

  **Acceptance Criteria**:
  - [ ] `npm run build` 通过
  - [ ] 白色主题下文件侧边栏文字清晰
  - [ ] 深色主题下效果保持不变

  **Commit**: NO

---

- [x] 7. AgentCatalog.tsx 白色主题修复

  **What to do**:
  修改以下硬编码深色样式为响应式：
  
  1. 页面容器：
     - `text-white` → `text-gray-900 dark:text-white`
  
  2. 页面标题：
     - `text-3xl font-bold` 保持不变（颜色继承自容器）
  
  3. 页面副标题：
     - `text-gray-400` → `text-gray-500 dark:text-gray-400`
  
  4. 分类按钮未选中态：
     - `bg-[rgba(255,255,255,0.05)] text-gray-400 hover:text-white hover:bg-[rgba(255,255,255,0.1)] border border-[rgba(255,255,255,0.05)]` → `bg-gray-100 text-gray-500 hover:text-gray-900 hover:bg-gray-200 border border-gray-200 dark:bg-[rgba(255,255,255,0.05)] dark:text-gray-400 dark:hover:text-white dark:hover:bg-[rgba(255,255,255,0.1)] dark:border-[rgba(255,255,255,0.05)]`
  
  5. 搜索框：
     - `border border-[rgba(255,255,255,0.1)] bg-[rgba(0,0,0,0.2)] text-gray-300 placeholder-gray-500` → `border border-gray-200 bg-white text-gray-700 placeholder-gray-400 dark:border-[rgba(255,255,255,0.1)] dark:bg-[rgba(0,0,0,0.2)] dark:text-gray-300 dark:placeholder-gray-500`
  
  6. Agent 卡片：
     - `bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.08)] hover:bg-[rgba(255,255,255,0.06)] hover:border-[rgba(255,255,255,0.15)]` → `bg-white border border-gray-200 hover:bg-gray-50 hover:border-gray-300 dark:bg-[rgba(255,255,255,0.03)] dark:border-[rgba(255,255,255,0.08)] dark:hover:bg-[rgba(255,255,255,0.06)] dark:hover:border-[rgba(255,255,255,0.15)]`
     - `shadow-xl shadow-black/20` → `shadow-lg shadow-gray-200/50 dark:shadow-xl dark:shadow-black/20`
  
  7. Agent 卡片分类标签：
     - `bg-[rgba(255,255,255,0.05)] text-gray-400 border border-[rgba(255,255,255,0.1)]` → `bg-gray-100 text-gray-500 border border-gray-200 dark:bg-[rgba(255,255,255,0.05)] dark:text-gray-400 dark:border-[rgba(255,255,255,0.1)]`
  
  8. Agent 名称：
     - `text-white` → `text-gray-900 dark:text-white`
  
  9. Agent 描述：
     - `text-gray-400` → `text-gray-500 dark:text-gray-400`
  
  10. Agent 标签：
      - `bg-black/30 text-gray-300 border border-white/5` → `bg-gray-100 text-gray-600 border border-gray-200 dark:bg-black/30 dark:text-gray-300 dark:border-white/5`
  
  11. "开始对话"链接：
      - `text-gray-400` → `text-gray-500 dark:text-gray-400`
  
  12. 无结果提示：
      - `bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)]` → `bg-gray-50 border border-gray-200 dark:bg-[rgba(255,255,255,0.02)] dark:border-[rgba(255,255,255,0.05)]`
      - `text-gray-300` → `text-gray-700 dark:text-gray-300`
      - `text-gray-500` 保持不变

  **Must NOT do**:
  - 不修改选中态分类按钮样式（蓝色背景）
  - 不修改 Agent 图标颜色
  - 不修改动画效果

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (单独)
  - **Blocks**: F1
  - **Blocked By**: None

  **References**:
  - `src/frontend/src/pages/AgentCatalog.tsx:49-156` - 主要渲染区域

  **Acceptance Criteria**:
  - [ ] `npm run build` 通过
  - [ ] 白色主题下 Agent 矩阵页面标题、卡片、文字全部清晰可见
  - [ ] 深色主题下效果保持不变

  **Commit**: NO

---

## Final Verification Wave

- [x] F1. **npm run build 验证**

  执行 `cd E:\amazon-automation\src\frontend && npm run build`，确保所有修改后编译通过。

---

## Commit Strategy

所有任务完成后统一提交：
- Message: `fix(frontend): 修复白色主题下多页面显示异常`
- Files: TrendChart.tsx, AdDashboard.tsx, AgentChat.tsx, ChatWindow.tsx, ConversationList.tsx, FileSidebar.tsx, AgentCatalog.tsx

---

## Success Criteria

### Verification Commands
```bash
cd E:\amazon-automation\src\frontend && npm run build  # Expected: 编译成功
```

### Final Checklist
- [ ] 白色主题下数据大盘趋势图时间筛选按钮可见
- [ ] 白色主题下所有 Agent 聊天页面背景为白色/浅灰
- [ ] 白色主题下 Agent 矩阵页面标题、卡片、文字清晰
- [ ] 深色主题下所有页面效果保持不变
- [ ] `npm run build` 通过
