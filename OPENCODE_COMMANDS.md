# OpenCode + OhMyOpenCode 命令行指令大全

> 基于当前安装版本，结合 OhMyOpenCode 插件实际配置整理

---

## 一、基础启动

| 命令 | 说明 |
|------|------|
| `opencode` | 在当前目录启动交互式 TUI 界面（最常用） |
| `opencode /path/to/project` | 在指定目录启动 |
| `opencode -c` | 继续上一次的会话 |
| `opencode -s <sessionID>` | 继续指定 ID 的会话 |
| `opencode --fork -c` | Fork 上一次会话后继续（不污染原会话） |
| `opencode --pure` | 纯净模式启动，不加载任何外部插件 |
| `opencode -m <provider/model>` | 指定模型启动，例如 `opencode -m github-copilot/gpt-4o` |
| `opencode --agent <name>` | 指定 Agent 启动，例如 `--agent sisyphus` |

---

## 二、非交互式运行（脚本/自动化）

```bash
# 直接发送一条消息并输出结果（不进入 TUI）
opencode run "帮我写一个 hello world 的 Python 脚本"

# 附带文件
opencode run "分析这个文件" -f src/main.py

# 继续上一次会话并发消息
opencode run -c "继续刚才的任务"

# 指定模型运行
opencode run -m github-copilot/claude-sonnet-4.6 "优化这段代码"

# 输出原始 JSON 事件流（适合管道/脚本处理）
opencode run --format json "给我一个列表"

# 显示思考过程（thinking blocks）
opencode run --thinking "解释这个算法的时间复杂度"

# 指定 Agent 运行
opencode run --agent sisyphus "帮我重构登录模块"

# 附加到远程 opencode 服务端运行
opencode run --attach http://localhost:4096 "查看项目状态"
```

---

## 三、会话管理

```bash
# 列出所有历史会话
opencode session list

# 删除某个会话
opencode session delete <sessionID>

# 导出会话为 JSON 文件
opencode export <sessionID>

# 从 JSON 文件导入会话
opencode import session-backup.json
```

---

## 四、模型与 Provider 管理

```bash
# 列出所有可用模型
opencode models

# 列出指定 provider 的模型
opencode models github-copilot

# 列出已配置的 provider 和认证状态
opencode providers list
opencode auth list          # 别名，效果相同

# 登录某个 provider
opencode providers login

# 登出某个 provider
opencode providers logout
```

---

## 五、统计与费用

```bash
# 查看全部 token 用量和费用统计
opencode stats

# 查看最近 7 天的统计
opencode stats --days 7

# 查看当前项目的统计
opencode stats --project ""

# 查看 top 5 工具使用情况
opencode stats --tools 5

# 显示各模型的统计详情
opencode stats --models
```

---

## 六、MCP 服务器管理

```bash
# 列出所有 MCP 服务器及状态
opencode mcp list
opencode mcp ls             # 别名

# 添加一个 MCP 服务器
opencode mcp add

# OAuth 认证
opencode mcp auth <name>

# 登出 MCP
opencode mcp logout <name>

# 调试 MCP 连接
opencode mcp debug <name>
```

---

## 七、Agent 管理（OhMyOpenCode 核心）

本项目配置的 Agent（`.opencode/oh-my-openagent.json`）：

| Agent | 类型 | 模型 | 职责 |
|-------|------|------|------|
| `sisyphus` | primary | claude-sonnet-4.6 | 主力编程 Agent |
| `oracle` | subagent | gpt-5.4 | 高质量推理 / 架构决策 |
| `explore` | subagent | grok-code-fast-1 | 快速代码搜索探索 |
| `librarian` | subagent | gemini-3-flash | 外部文档 / 库搜索 |
| `momus` | subagent | gpt-5.4 | 方案评审 |
| `metis` | subagent | claude-sonnet-4.6 | 需求分析 / 歧义识别 |
| `atlas` | subagent | claude-sonnet-4.6 | 通用任务 |

```bash
# 列出所有可用 Agent
opencode agent list

# 创建新 Agent
opencode agent create

# 查看某个 Agent 的详细配置
opencode debug agent sisyphus
opencode debug agent oracle
```

---

## 八、服务端模式（多端协作）

```bash
# 启动无头服务端（供其他客户端连接）
opencode serve --port 4096

# 启动服务端并开启 mDNS（局域网自动发现）
opencode serve --mdns

# 启动服务端并打开 Web 界面
opencode web

# 从另一个终端连接到正在运行的服务端
opencode attach http://localhost:4096

# 启动 ACP 协议服务端（用于 IDE 集成）
opencode acp --port 4096
```

---

## 九、调试工具

```bash
# 查看当前解析后的完整配置
opencode debug config

# 查看所有全局路径（数据、缓存、日志等）
opencode debug paths
# 本机路径参考：
#   data    C:\Users\zhjim\.local\share\opencode
#   config  C:\Users\zhjim\.config\opencode
#   log     C:\Users\zhjim\.local\share\opencode\log
#   cache   C:\Users\zhjim\.cache\opencode

# 列出所有已识别的项目
opencode debug scrap

# 列出所有可用的 Skills
opencode debug skill

# 查看某个 Agent 的详细权限配置
opencode debug agent <name>

# 调试文件系统
opencode debug file

# 调试 LSP（语言服务器）
opencode debug lsp

# 调试 ripgrep 搜索
opencode debug rg

# 查看快照（Snapshot）
opencode debug snapshot
```

---

## 十、GitHub 集成

```bash
# 安装 GitHub Agent
opencode github install

# 运行 GitHub Agent
opencode github run

# 拉取某个 PR 分支并直接在其上启动 opencode
opencode pr 123
```

---

## 十一、插件安装

```bash
# 安装插件（如 OhMyOpenCode）
opencode plugin <npm-module-name>
opencode plug <npm-module-name>     # 别名
```

---

## 十二、版本与维护

```bash
# 查看当前版本
opencode --version
opencode -v

# 升级到最新版本
opencode upgrade

# 升级到指定版本
opencode upgrade 0.5.0

# 卸载 opencode
opencode uninstall
```

---

## 十三、日志调试选项（全局通用）

所有命令都支持以下调试参数：

```bash
# 将日志打印到 stderr
opencode --print-logs

# 设置日志级别（可选: DEBUG / INFO / WARN / ERROR）
opencode --log-level DEBUG
```

---

## 快速备忘

```bash
# 日常最常用
opencode                          # 启动 TUI
opencode -c                       # 继续上次会话
opencode run "你的问题"            # 非交互式提问

# 最实用的查询
opencode stats --days 7           # 查本周用量
opencode session list             # 查历史会话
opencode models github-copilot    # 查可用模型
opencode debug paths              # 查本机数据路径
```
