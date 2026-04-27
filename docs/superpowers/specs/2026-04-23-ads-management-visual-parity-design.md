# 广告管理视觉同构迁移设计稿

日期：2026-04-23

> 本文 supersedes `docs/superpowers/specs/2026-04-22-ads-management-design.md` 中对广告管理“8 个 tab 收口版”的目标定义。

## 1. 背景与目标

赛狐 ERP 将在 2026-04-28 左右到期。到期后，团队将无法继续进入赛狐广告管理模块参考页面结构与交互节奏，但仍需要在自有系统中完成广告管理相关日常操作。

本次目标因此从“广告管理工作台第一版收口”升级为：

- 在 2026-04-28 前，尽量把**广告管理总页以及从该页可进入的详情页、编辑页、弹窗、抽屉**迁入本系统
- 优先保证**页面结构与交互尽量接近赛狐 ERP**
- 允许部分功能在第一阶段仍处于 **mock / 半闭环** 状态，但必须明确区分
- 明确继续排除：**广告位、AMC**

本次不是单页重构，而是一个“广告管理前台子系统迁移项目”。

## 2. 已确认约束

### 2.1 核心优先级
用户已明确确认以下优先顺序：

1. **页面结构和交互尽量一致**
2. **广告管理可达页一起复刻**，包括从总页可点击进入的详情页、编辑页、弹窗、抽屉
3. **完整全覆盖优先**，而不是只做高频路径
4. 如果视觉同构与真实闭环能力冲突，先保前台完整性，再分阶段补后端闭环

### 2.2 明确排除范围
- 广告位
- AMC

### 2.3 第一阶段允许的交付形态
本阶段允许三种能力等级并存：

- **L1 全闭环**：真实前后端写入、状态刷新可见
- **L2 半闭环**：前台交互完整，但后端仍为 mock 或局部写入
- **L3 展示级**：入口、弹窗、页面、参数校验与反馈存在，但不承诺真实业务落地

设计与实现时必须显式标记当前等级，避免运营误判。

## 3. 信息架构

广告管理不再定义为“一个带 8 个 tab 的列表页”，而应升级为三层前台体系：

### 3.1 工作台层
入口保持：`/ads/manage`

职责：
- 左侧树形筛选
- 顶部全局筛选与快捷操作
- 对象 tab 切换
- 列表展示、批量选择、分页、排序
- 进入详情页、编辑页、抽屉、弹窗
- 承担 URL 恢复与来源上下文

### 3.2 详情层
职责：
- 展示从工作台进入的对象详情或二级页面
- 保持返回来源上下文
- 承载需要更深浏览与编辑的信息结构

典型对象包括但不限于：
- Campaign 详情
- Ad Group 详情 / 二级页
- Targeting / Search Term / Negative Targeting 深度视图
- 日志明细或上下文查看页

### 3.3 轻量操作层
职责：
- 承载赛狐式高频轻量操作
- 尽量保留在当前工作台就地处理的交互节奏

典型容器包括：
- Modal
- Drawer
- Confirm Dialog
- Dropdown Action Menu
- Batch Action Panel

原则：
- **复杂详情** 优先独立页
- **高频轻量编辑** 优先弹窗 / 抽屉
- **快速单步操作** 优先当前页完成

## 4. 功能模块拆分

本项目按 6 个功能模块组织：

### 4.1 主工作台壳层
负责赛狐广告管理主页面骨架：
- 左侧树
- 顶部筛选区
- 对象 tab
- 主列表区
- 行内操作区
- 批量操作区
- URL 恢复

### 4.2 对象列表矩阵
继续保留并扩展当前 8 个对象：
- 广告组合
- 广告活动
- 广告组
- 广告产品
- 投放
- 搜索词
- 否定投放
- 广告日志

要求每个对象都具备：
- 接近赛狐的列结构
- 接近赛狐的筛选语义
- 接近赛狐的批量选择方式
- 接近赛狐的行级操作入口
- 接近赛狐的进入详情或展开方式

### 4.3 详情与二级视图矩阵
凡是从总页点得进去的详情、设置、明细、二级页，都应纳入正式设计边界，而不是临时挂靠在单个列表页上。

### 4.4 轻量操作矩阵
承载：
- 暂停 / 启用
- 修改预算
- 修改竞价
- 添加否定词
- 批量编辑
- 规则应用
- 二次确认

要求：
- 操作入口位置尽量接近赛狐
- 操作反馈方式一致
- 成功 / 失败 / 半闭环提示一致

### 4.5 闭环分级矩阵
每个操作都必须归类为 L1 / L2 / L3，不能出现“按钮存在但当前能力等级不明确”的情况。

### 4.6 一致性与迁移保障模块
统一：
- 术语命名
- 筛选顺序
- 操作入口位置
- 列表进入详情的方式
- 批量工具栏显隐条件
- 成功 / 失败提示样式
- 返回与刷新后的行为

## 5. 状态模型

当前 `src/frontend/src/pages/ad-management/types.ts` 中的 `AdsQueryState` 适合继续承担**列表查询状态**，但不能继续单独承担整个广告管理子系统的全部状态。

建议拆成 3 层：

### 5.1 列表查询状态（Query State）
负责：
- activeTab
- filters
- page / pageSize
- sort
- selected rows
- tree selection

职责：
- 服务工作台列表
- 作为 URL 主要恢复来源

### 5.2 视图导航状态（View State）
负责描述：
- 当前位于列表 / 详情 / 编辑 / drawer / modal 哪一层
- 当前对象类型与对象 id
- 来源 tab
- 来源 query snapshot

职责：
- 保证从工作台进入详情和返回时不丢上下文
- 保证路由与页面层级可解释

### 5.3 操作会话状态（Action State）
负责描述：
- 当前正在执行什么操作
- 目标对象是谁
- 是单条还是批量
- 是否有脏数据
- 是否提交中
- 是否成功 / 失败
- 是否需要二次确认

职责：
- 驱动弹窗 / 抽屉 / toast / confirm dialog / batch panel

## 6. 路由模型

### 6.1 总页
- `/ads/manage`

### 6.2 详情页建议显式路由化
根据对象复杂度提供独立详情路径，例如：
- `/ads/manage/campaign/:id`
- `/ads/manage/ad-group/:id`
- `/ads/manage/targeting/:id`
- `/ads/manage/search-term/:id`

是否为独立路由的原则：
- **复杂详情** → 独立路由
- **轻量编辑** → Drawer / Modal
- **快速操作** → 当前页完成

### 6.3 URL 承载原则
URL 承载“可恢复的业务视图状态”，不承载所有瞬时 UI 状态。

#### URL 应承载
- activeTab
- filters
- page
- sort
- current entity id（若在详情页）
- 必要的来源标识

#### URL 不应承载
- 弹窗打开状态
- 输入框未提交草稿
- hover / 展开等瞬时态
- 未确认的临时编辑内容

## 7. 组件边界与文件组织

### 7.1 保留并重新定义的现有骨架
以下文件保留，但职责收敛：

- `src/frontend/src/pages/AdManagement.tsx`
  - 作为工作台入口页与编排层
- `src/frontend/src/pages/ad-management/AdsLeftFilterPanel.tsx`
  - 左侧树筛选组件
- `src/frontend/src/pages/ad-management/AdsTopToolbar.tsx`
  - 顶部筛选与入口条
- `src/frontend/src/pages/ad-management/AdsDataTablePanel.tsx`
  - 列表区容器
- `src/frontend/src/pages/ad-management/adsSchemas.tsx`
  - 继续承担**列表 schema 中心**，但不再承担详情、弹窗和复杂状态逻辑

### 7.2 必须新增的层
建议在 `src/frontend/src/pages/ad-management/` 下新增以下分层：

```text
workspace/
  AdWorkspaceShell.tsx
  AdWorkspaceLayout.tsx
  AdWorkspaceState.ts

detail/
  CampaignDetailPage.tsx
  AdGroupDetailPage.tsx
  TargetingDetailPage.tsx
  SearchTermDetailPage.tsx
  NegativeTargetingDetailPage.tsx
  LogDetailPage.tsx

actions/
  EditBudgetModal.tsx
  ChangeStatusModal.tsx
  EditBidDrawer.tsx
  NegativeKeywordModal.tsx
  BatchActionPanel.tsx
  ConfirmOperationDialog.tsx

config/
  tabs.ts
  schemas.tsx
  actions.ts
  routes.ts

state/
  queryState.ts
  viewState.ts
  actionState.ts

components/
  AdsLeftFilterPanel.tsx
  AdsTopToolbar.tsx
  AdsObjectTabs.tsx
  AdsDataTablePanel.tsx
```

目标：
- workspace 只管工作台
- detail 只管详情
- actions 只管操作容器
- config 只管配置映射
- state 只管状态模型

## 8. 数据流与接口策略

### 8.1 读取三通道

#### A. 列表读取通道
服务：工作台各对象列表。

要求：
- 统一分页、排序、筛选
- 契约稳定
- 与 URL 恢复强相关

#### B. 详情读取通道
服务：对象详情、二级页、设置页、明细查看。

要求：
- 支持从列表上下文进入
- 支持更深层数据结构
- 支持返回来源上下文

#### C. 操作提交通道
服务：弹窗、抽屉、批量操作、单条编辑。

要求：
- 状态机清晰
- 能承接 L1 / L2 / L3
- 成功 / 失败反馈统一

### 8.2 列表接口契约
各对象列表应统一返回：
- `items`
- `total_count`
- `summary_row`
- 可扩展 `meta`

前端每个 tab 继续坚持“只发送当前 tab 支持的参数”，避免重新回退为一套通用大广播参数。

### 8.3 详情接口策略
分为两类：

- **独立详情接口**：复杂对象深度页
- **列表上下文详情**：轻量查看 / 抽屉式查看

### 8.4 操作网关
不建议每个弹窗直接分散调用 API。建议设计统一操作层，概念上统一为：
- 操作名
- 对象类型
- 对象 id / id 列表
- payload
- 能力等级（L1 / L2 / L3）
- 成功后的刷新策略
- 失败后的反馈策略

### 8.5 刷新策略
操作完成后只允许三种刷新策略：
- 局部更新当前行
- 局部刷新当前列表
- 刷新详情并回写列表

禁止每个页面自行发散出不同刷新习惯。

## 9. 当前基础与演进方向

### 9.1 当前已具备的基础
- `src/frontend/src/pages/AdManagement.tsx`
- `src/frontend/src/pages/ad-management/AdsLeftFilterPanel.tsx`
- `src/frontend/src/pages/ad-management/AdsTopToolbar.tsx`
- `src/frontend/src/pages/ad-management/AdsDataTablePanel.tsx`
- `src/frontend/src/pages/ad-management/adsSchemas.tsx`
- `src/api/ads.py`
- `data/mock/ads.py`
- `tests/api/test_ads_api.py`
- `tests/api/test_navigation_contract.py`

### 9.2 当前基础的定位
这些内容可以继续作为“第一层工作台骨架”，但必须从“8 个 tab 单页实现”升级为“工作台 + 详情 + 轻量操作 + 状态分层”的子系统。

## 10. 验收标准

### 10.1 结构一致性验收
需满足：
- 主分区接近赛狐（左侧树 / 顶部筛选 / 中央列表 / 行内操作 / 批量工具栏）
- tab 组织方式接近
- 常用筛选顺序接近
- 高频入口位置接近
- 详情页 / 抽屉 / 弹窗进入方式接近

通过口径：
> 运营打开后，能凭赛狐肌肉记忆快速知道“在哪筛、在哪点、点进去会去哪”。

### 10.2 路径覆盖验收
从 `/ads/manage` 出发，所有应可达路径都必须：
- 有入口
- 能点击进入
- 有内容承载
- 能返回
- 不死链
- 不出现“点了没反应”

### 10.3 操作分级验收
每个操作必须明确：
- 操作名
- 入口位置
- 对象范围
- 当前等级（L1 / L2 / L3）
- 成功后行为
- 失败后行为
- 是否真实写入

### 10.4 恢复能力验收
需验证：
- 刷新后核心上下文能恢复
- 浏览器前进 / 后退不乱
- 从详情返回列表时筛选与分页尽量保留
- 批量操作后不会把用户带丢

## 11. 测试策略

### 11.1 源码级契约测试
保护：
- 页面结构
- 参数矩阵
- 路由字符串
- 排除项（广告位 / AMC）

### 11.2 API 契约测试
保护：
- 列表接口
- 详情接口
- 操作接口
- L1 / L2 / L3 的响应语义

### 11.3 浏览器级路径回归
重点覆盖：
- tab 切换
- 筛选
- 下钻
- 打开弹窗 / 抽屉
- 返回
- URL 恢复
- 刷新恢复
- 批量入口显隐
- 高频操作反馈

### 11.4 人工对照验收
按“赛狐页面 → 我们页面”做对照清单，逐项核验：
- 页面区域
- 操作入口
- 点击去向
- 交互节奏
- 是否存在运营会迷路的地方

## 12. 分阶段实施建议

由于目标已升级为完整前台迁移，建议实施层面按以下顺序推进：

### 阶段 1：工作台全骨架
- 工作台壳层
- 左侧树 / 顶部筛选 / tab / 列表矩阵
- 所有可达子页面的路由骨架
- URL / 返回链路骨架

### 阶段 2：详情与操作容器全铺开
- 详情页
- 编辑页
- Modal / Drawer / Batch Panel / Confirm Dialog
- 让所有可达页真正“能进去、能回来、能理解”

### 阶段 3：高频操作闭环优先
- 暂停 / 启用
- 修改预算
- 修改竞价
- 否定词相关
- 高频批量操作

### 阶段 4：细节对齐与验收
- 结构与交互细修
- 浏览器级回归
- 人工对照赛狐逐项校验
- 标注未完成闭环的 L2 / L3 能力

## 13. 非目标提醒

本设计仍不覆盖：
- 广告位
- AMC
- 与当前广告管理工作台无关的外围模块
- 赛狐广告系统之外的其它 ERP 模块

## 14. 设计结论

本项目的成功标准不是“又做了一个广告页”，而是：

> 在赛狐到期后，运营仍能按熟悉的页面结构和交互路径，在本系统中完成广告管理工作，并且不会在系统里迷路。

因此，本次广告管理建设必须从“8 个 tab 的工作台页面”升级为“广告管理前台子系统迁移工程”。
