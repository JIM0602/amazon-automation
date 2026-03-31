# PUDIWIND AI System 部署指南

> **写给完全没有技术背景的你** 👋  
> 这份指南会一步一步带你把这套系统部署到云服务器上，让它24小时不间断运行。
> 每步操作我都会告诉你：为什么要这么做，以及成功的标志是什么。

---

## 目录

1. [准备工作](#1-准备工作)
2. [连接服务器](#2-连接服务器)
3. [一键初始化服务器](#3-一键初始化服务器)
4. [配置 .env 文件](#4-配置-env-文件)
5. [一键部署](#5-一键部署)
6. [配置域名和HTTPS（可选）](#6-配置域名和https可选)
7. [验证系统运行](#7-验证系统运行)
8. [日常维护](#8-日常维护)
9. [常见问题排查](#9-常见问题排查)

---

## 1. 准备工作

### 为什么要做这步？
系统需要运行在一台24小时开机的服务器上，不是你的电脑（关了就断了）。我们需要租一台云服务器。

### 服务器选择建议

**推荐方案一：AWS EC2（美国用户多、稳定）**
- 机型：`t3.medium`（2核 CPU + 4GB 内存）
- 系统：Ubuntu 22.04 LTS
- 存储：30GB SSD（gp3 类型）
- 预计费用：约 $30/月

**推荐方案二：阿里云 ECS（国内访问快）**
- 规格：2核 4GB（ecs.t5-lc1m2.small 或更高）
- 系统：Ubuntu 22.04 LTS
- 存储：40GB ESSD
- 预计费用：约 ¥100-200/月（按需付费）

**推荐方案三：腾讯云 CVM（国内用，性价比高）**
- 规格：2核 4GB
- 系统：Ubuntu 22.04 LTS
- 预计费用：约 ¥100-150/月

> ⚠️ **注意**：飞书 webhook 需要公网 IP。所有云服务商默认会给公网 IP，没问题。

### 创建服务器时的关键设置

1. **选择 Ubuntu 22.04 LTS**（不要用 20.04 以下或 CentOS 7）
2. **开放端口**：在安全组/防火墙设置里，至少开放以下端口：
   - `22`（SSH 远程连接，非常重要，不开就进不去）
   - `80`（HTTP）
   - `443`（HTTPS）
3. **保存 SSH 密钥**：创建时下载的 `.pem` 文件一定要妥善保存，丢了就进不去服务器了！

### 成功的标志
- 服务器状态显示"运行中"
- 有一个公网 IP 地址（类似 `1.2.3.4`）
- 下载了 SSH 密钥文件（`.pem` 格式）

---

## 2. 连接服务器

### 为什么要做这步？
我们需要在服务器上执行命令，SSH 是远程控制服务器的方式，就像用键盘控制一台远在机房里的电脑。

### 在 macOS / Linux 上连接

打开终端，输入以下命令：

```bash
# 第一步：设置密钥文件权限（只需要第一次）
chmod 400 ~/Downloads/your-key.pem

# 第二步：连接服务器（把 1.2.3.4 换成你的服务器 IP）
ssh -i ~/Downloads/your-key.pem ubuntu@1.2.3.4
```

> 💡 **说明**：
> - `chmod 400` 是设置密钥文件只有你自己能读，不设置 SSH 会拒绝使用
> - `ubuntu` 是 Ubuntu 系统的默认用户名，AWS 用 `ubuntu`，阿里云可能是 `root`
> - 第一次连接会问 "Are you sure you want to continue connecting?"，输入 `yes` 回车

### 在 Windows 上连接

**方法一（推荐）：使用 PuTTY**
1. 下载并安装 [PuTTY](https://www.putty.org/)
2. 先用 PuTTYgen 把 `.pem` 文件转换为 `.ppk` 格式
3. 打开 PuTTY，填入服务器 IP，加载 `.ppk` 密钥，点连接

**方法二：使用 Windows Terminal（Windows 10/11 自带）**
```powershell
# PowerShell 中执行（把路径和 IP 换成你的）
ssh -i "C:\Users\你的名字\Downloads\your-key.pem" ubuntu@1.2.3.4
```

### 成功的标志
命令行提示符变成类似这样：
```
ubuntu@ip-172-31-1-2:~$
```
说明你已经成功进入服务器了！

---

## 3. 一键初始化服务器

### 为什么要做这步？
刚买的服务器是空的，我们需要安装 Docker（用来运行程序）、配置防火墙（保护安全），这个脚本帮你自动完成所有准备工作。

### 上传并运行初始化脚本

**第一步：在服务器上创建应用目录并上传代码**

在你的本地电脑（不是服务器上）执行：
```bash
# 把整个项目上传到服务器（把 1.2.3.4 换成你的 IP）
scp -i ~/Downloads/your-key.pem -r /path/to/amazon-automation ubuntu@1.2.3.4:/opt/amazon-ai
```

或者使用 git 克隆（在服务器上执行）：
```bash
# 在服务器上执行
sudo mkdir -p /opt/amazon-ai
sudo chown ubuntu:ubuntu /opt/amazon-ai
cd /opt/amazon-ai
git clone https://github.com/your-org/amazon-automation.git .
```

**第二步：运行初始化脚本**

在服务器上执行：
```bash
# 进入项目目录
cd /opt/amazon-ai

# 运行初始化脚本（需要管理员权限，sudo 会要求输入密码）
sudo bash deploy/scripts/setup-server.sh
```

这个脚本会自动：
- 安装 Docker 和 Docker Compose
- 创建必要的目录
- 配置防火墙（只开放 22、80、443 端口）
- 创建 appuser 非管理员用户

> ⚠️ **注意**：这个过程需要 5-10 分钟，请耐心等待，不要中途关闭。

### 成功的标志
脚本最后显示：
```
  服务器初始化完成！
  下一步操作：
  1. 上传项目代码到 /opt/amazon-ai/
  2. 创建并配置 .env 文件
  3. 运行 bash deploy.sh 启动服务
```

验证 Docker 安装成功：
```bash
docker --version
# 应该显示类似：Docker version 24.0.5, build 1234567
```

---

## 4. 配置 .env 文件

### 为什么要做这步？
这套系统需要知道数据库密码、OpenAI 密钥、飞书配置等敏感信息。这些信息不能直接写在代码里（别人能看到），要单独放在 `.env` 文件里，而且这个文件不会上传到 git。

### 创建 .env 文件

在服务器上执行：
```bash
# 进入项目目录
cd /opt/amazon-ai

# 复制模板文件
cp .env.example .env

# 用 nano 编辑器编辑（上下键移动光标，Ctrl+O 保存，Ctrl+X 退出）
nano .env
```

### 逐行说明每个配置项

编辑 `.env` 文件，把每个配置项填上真实的值：

---

**📦 数据库配置**
```bash
DATABASE_URL=postgresql://app_user:你的数据库密码@postgres:5432/amazon_ai
```
> 📖 **这是什么**：程序连接数据库的地址，格式是固定的。  
> 📝 **你需要做**：把 `你的数据库密码` 换成一个复杂密码（建议：字母+数字+符号，至少16位）。  
> 💡 **同时设置**：把这个密码也填到下面 `POSTGRES_PASSWORD` 里（必须一致）。

```bash
POSTGRES_PASSWORD=你的数据库密码
```
> 📖 **这是什么**：Docker 启动 PostgreSQL 数据库时用这个密码。必须和上面 `DATABASE_URL` 里的密码完全相同！

---

**🤖 OpenAI 配置**
```bash
OPENAI_API_KEY=sk-你的OpenAI密钥
OPENAI_MODEL=gpt-4o-mini
```
> 📖 **这是什么**：程序用这个密钥调用 AI 分析商品数据。  
> 📝 **去哪里获取**：登录 [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)，点"Create new secret key"。  
> 💡 **关于模型**：`gpt-4o-mini` 便宜但够用，`gpt-4o` 更聪明但贵3倍。  
> ⚠️ **警告**：这个密钥非常重要，泄露了别人会用你的钱！不要分享给任何人。

---

**✉️ Anthropic 配置（可选）**
```bash
ANTHROPIC_API_KEY=
```
> 📖 **这是什么**：可选的 Claude AI 密钥，不用就留空。

---

**🐦 飞书配置**
```bash
FEISHU_APP_ID=cli_你的应用ID
FEISHU_APP_SECRET=你的应用密钥
FEISHU_VERIFY_TOKEN=你的验证Token
FEISHU_ENCRYPT_KEY=你的加密Key
FEISHU_TEST_CHAT_ID=oc_测试群ID
```
> 📖 **这是什么**：飞书机器人的"身份证"，系统用这些信息接收和发送飞书消息。  
> 📝 **去哪里获取**：登录飞书开放平台 [https://open.feishu.cn/](https://open.feishu.cn/)，进入你的应用 → 凭证与基础信息。

---

**🛒 卖家精灵配置**
```bash
SELLER_SPRITE_API_KEY=你的卖家精灵密钥
SELLER_SPRITE_USE_MOCK=false
```
> 📖 **这是什么**：卖家精灵是获取亚马逊商品数据的工具。  
> 💡 **Mock 模式**：`true` 用假数据测试（不消耗 API 额度），`false` 用真实数据。  
> 📝 **正式上线前**：把 `SELLER_SPRITE_USE_MOCK` 改成 `false`。

---

**💰 费用控制**
```bash
MAX_DAILY_LLM_COST_USD=50.0
```
> 📖 **这是什么**：每天 AI 调用费用上限（美元）。超过这个数，系统会停止调用 AI，防止账单爆炸。  
> 📝 **建议**：先设 `10.0`（$10/天），稳定后再调高。

---

**⚙️ 系统配置**
```bash
DRY_RUN=false
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
```
> 📖 **DRY_RUN**：`true` 表示只分析不执行（测试用），`false` 正常运行。  
> 📖 **APP_HOST/PORT**：服务监听地址，不用改。  
> 📖 **LOG_LEVEL**：日志详细程度，`INFO` 够用，问题多时改 `DEBUG`。

---

**🛒 Amazon SP-API（Phase 2，现在留空）**
```bash
AMAZON_SP_API_ACCESS_KEY=
AMAZON_SP_API_SECRET_KEY=
AMAZON_SP_API_REFRESH_TOKEN=
AMAZON_MARKETPLACE_ID=ATVPDKIKX0DER
```
> 📖 **这是什么**：直接调用亚马逊 API 的密钥，Phase 2 才需要，现在留空。

---

**📨 飞书告警 Webhook（监控脚本用）**
```bash
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/你的webhook
```
> 📖 **这是什么**：服务器出问题时，监控脚本通过这个地址发飞书消息告警你。  
> 📝 **获取方式**：在飞书群里 → 设置 → 机器人 → 添加自定义机器人 → 复制 webhook 地址。

---

### 保护 .env 文件安全
```bash
# 设置文件权限，只有当前用户能读（保护密钥安全）
chmod 600 /opt/amazon-ai/.env
```

### 成功的标志
运行以下命令不报错，能看到配置内容：
```bash
cat /opt/amazon-ai/.env
```

---

## 5. 一键部署

### 为什么要做这步？
现在服务器准备好了，配置也填完了，运行 `deploy.sh` 会自动构建 Docker 镜像并启动所有服务。

### 运行部署脚本

```bash
cd /opt/amazon-ai
bash deploy/scripts/deploy.sh
```

脚本会自动执行：
1. 拉取最新代码（`git pull`）
2. 构建 Docker 镜像（打包程序）
3. 启动所有容器（app + postgres）
4. 等待健康检查通过
5. 发送飞书通知

> ⚠️ **第一次部署比较慢**：需要下载 Docker 镜像和安装依赖，可能需要 5-15 分钟，请耐心等待。

### 成功的标志
脚本最后显示：
```
  ✅ 部署成功！
  访问地址：http://your-domain.com/health
```

验证容器正在运行：
```bash
docker ps
# 应该看到类似：
# amazon-ai-app      Up 2 minutes (healthy)
# amazon-ai-postgres Up 2 minutes (healthy)
```

---

## 6. 配置域名和HTTPS（可选）

### 为什么要做这步？
飞书 webhook 要求回调地址必须是 HTTPS（`https://`），不是 HTTP。而且域名比 IP 地址更好记、更专业。

> 💡 **如果只是测试**：可以跳过这步，直接用 `http://服务器IP:8000`，但飞书正式环境需要 HTTPS。

### 步骤一：购买域名

在阿里云、腾讯云或 GoDaddy 购买一个域名，例如 `your-company.com`。

### 步骤二：配置 DNS 解析

在域名服务商控制台，添加一条 A 记录：
- 主机记录：`@`（或 `www`）
- 记录类型：`A`
- 记录值：你的服务器公网 IP

等待 DNS 生效（通常 5-30 分钟）。

验证 DNS 生效：
```bash
# 在服务器上执行
ping your-domain.com
# 应该解析到你的服务器 IP
```

### 步骤三：安装 Nginx 配置

把我们的 nginx 配置复制到正确位置：
```bash
# 修改 nginx.conf 中的域名（把 your-domain.com 换成你的真实域名）
nano /opt/amazon-ai/deploy/nginx/nginx.conf

# 复制配置到 nginx 目录
sudo cp /opt/amazon-ai/deploy/nginx/nginx.conf /etc/nginx/nginx.conf

# 测试配置是否正确
sudo nginx -t

# 重载配置
sudo systemctl reload nginx
```

### 步骤四：申请免费 SSL 证书（Let's Encrypt）

```bash
# 安装 certbot
sudo apt install -y certbot python3-certbot-nginx

# 申请证书（把 your-domain.com 换成你的域名）
sudo certbot --nginx -d your-domain.com

# certbot 会：
# 1. 自动验证域名所有权
# 2. 下载证书到 /etc/letsencrypt/live/your-domain.com/
# 3. 自动修改 nginx 配置
```

证书有效期90天，certbot 会自动续期：
```bash
# 验证自动续期
sudo certbot renew --dry-run
```

### 成功的标志
浏览器访问 `https://your-domain.com/health`，地址栏显示🔒小锁，返回：
```json
{"status": "ok"}
```

---

## 7. 验证系统运行

### 为什么要做这步？
部署完成后，要逐一验证每个功能是否正常，确保没有遗漏。

### 检查一：服务健康状态
```bash
# 方法一：命令行访问
curl http://localhost:8000/health
# 期望返回：{"status": "ok"}

# 方法二：浏览器访问
# 打开 http://你的服务器IP:8000/health 或 https://your-domain.com/health
```

### 检查二：容器运行状态
```bash
# 查看所有容器状态
docker ps

# 期望看到两个容器都在运行，且 STATUS 列显示 (healthy)
# NAME                STATUS
# amazon-ai-app       Up 5 minutes (healthy)
# amazon-ai-postgres  Up 5 minutes (healthy)
```

### 检查三：查看应用日志
```bash
# 实时查看最新50行日志（按 Ctrl+C 退出）
docker logs amazon-ai-app --tail=50 -f
```

### 检查四：飞书机器人响应
在飞书发送测试消息给机器人，验证：
1. 机器人能接收到消息（webhook 配置正确）
2. 机器人能回复（程序运行正常）

### 检查五：数据库连接
```bash
# 进入 postgres 容器验证数据库
docker exec -it amazon-ai-postgres psql -U app_user -d amazon_ai -c "\dt"
# 应该显示数据库中的表列表
```

---

## 8. 日常维护

### 查看服务日志
```bash
# 查看 app 实时日志
docker logs amazon-ai-app -f

# 查看最近100行
docker logs amazon-ai-app --tail=100

# 查看 postgres 日志
docker logs amazon-ai-postgres --tail=50

# 查看 systemd 服务日志
sudo journalctl -u amazon-ai -f
```

### 更新部署新版本
```bash
cd /opt/amazon-ai
bash deploy/scripts/deploy.sh
```
> 📖 脚本会自动 git pull → 重新构建镜像 → 重启服务 → 健康检查 → 飞书通知。

### 手动备份数据库
```bash
bash /opt/amazon-ai/deploy/scripts/backup-db.sh
```

### 设置自动备份（每天凌晨3点）
```bash
# 编辑定时任务
crontab -e

# 添加以下行（每天3:00 AM 备份）
0 3 * * * bash /opt/amazon-ai/deploy/scripts/backup-db.sh >> /opt/amazon-ai/logs/backup.log 2>&1

# 同时添加监控任务（每5分钟检查一次）
*/5 * * * * bash /opt/amazon-ai/deploy/scripts/monitor.sh >> /opt/amazon-ai/logs/monitor.log 2>&1
```

### 查看备份文件
```bash
ls -lh /opt/amazon-ai/backups/
```

### 重启服务
```bash
# 重启所有容器
docker compose -f /opt/amazon-ai/deploy/docker/docker-compose.yml restart

# 仅重启 app
docker compose -f /opt/amazon-ai/deploy/docker/docker-compose.yml restart app
```

### 紧急停止服务
```bash
# 停止所有容器（数据不会丢失）
docker compose -f /opt/amazon-ai/deploy/docker/docker-compose.yml down
```

### 查看资源使用情况
```bash
# 查看 CPU、内存实时使用
docker stats

# 查看磁盘使用
df -h
```

### 释放磁盘空间（Docker 清理）
```bash
# 清理所有停止的容器、未使用的镜像（⚠️ 会删除旧镜像，操作前确认）
docker system prune -a

# 仅清理悬空镜像（更安全）
docker image prune
```

---

## 9. 常见问题排查

### ❓ 问题一：容器一直重启（STATUS 显示 Restarting）

**症状**：`docker ps` 看到容器状态是 `Restarting (1) X seconds ago`

**原因**：程序启动时出错，自动退出，Docker 尝试重启

**排查步骤**：
```bash
# 查看最近的报错日志
docker logs amazon-ai-app --tail=100

# 常见错误和解决方法：

# 错误1：pydantic_settings 报错，说某环境变量缺失
# ERROR: validation error for Settings, DATABASE_URL: Field required
# → 解决：检查 .env 文件，确保所有必填项都填了

# 错误2：数据库连接失败
# ERROR: could not connect to server
# → 解决：等待 postgres 容器完全启动（需要30秒），或检查 DATABASE_URL 格式

# 错误3：模块未找到
# ModuleNotFoundError: No module named 'xxx'
# → 解决：重新构建镜像 docker compose build --no-cache
```

### ❓ 问题二：飞书连不上（消息发不出去）

**症状**：发飞书消息没有回应，日志有报错

**排查步骤**：
```bash
# 查看飞书相关日志
docker logs amazon-ai-app | grep -i feishu

# 验证飞书配置
# 1. 检查 FEISHU_APP_ID 和 FEISHU_APP_SECRET 是否正确
# 2. 检查飞书开放平台中，webhook 回调地址是否填了你的服务器地址
# 3. 验证回调地址能访问（需要是 HTTPS）

# 手动测试飞书 webhook（在服务器上执行）
curl -X POST https://your-domain.com/feishu/webhook \
  -H "Content-Type: application/json" \
  -d '{"type": "url_verification", "challenge": "test123"}'
# 期望返回：{"challenge": "test123"}
```

**飞书 webhook 配置检查**：
1. 登录飞书开放平台 → 你的应用 → 事件与回调
2. 确认"请求网址"填的是 `https://your-domain.com/feishu/webhook`
3. 点"验证"按钮，如果报错则是服务器或网络问题

### ❓ 问题三：内存不足（服务器卡顿）

**症状**：服务器变慢，或容器被 OOM Killer 杀掉

**排查步骤**：
```bash
# 查看内存使用
free -h
docker stats --no-stream

# 查看是否有 OOM 事件
dmesg | grep -i "out of memory"
```

**解决方法**：
1. **短期**：重启容器释放内存泄漏：`docker compose restart`
2. **中期**：降低 AI 并发调用数，减少同时处理的任务
3. **长期**：升级服务器到 4核8G（AWS t3.large 或等效）

### ❓ 问题四：磁盘满了

**症状**：日志报错 `No space left on device`

**排查步骤**：
```bash
# 查看哪里占用磁盘多
df -h
du -sh /var/lib/docker/  # Docker 数据
du -sh /opt/amazon-ai/backups/  # 备份文件
du -sh /var/log/  # 系统日志
```

**解决方法**：
```bash
# 清理 Docker 数据（⚠️ 会删除未使用的镜像）
docker system prune -a

# 清理30天前的备份（手动）
find /opt/amazon-ai/backups/ -name "*.sql.gz" -mtime +30 -delete

# 清理系统日志
sudo journalctl --vacuum-size=500M
```

### ❓ 问题五：健康检查一直不通过

**症状**：`docker ps` 里容器状态是 `(health: starting)` 超过2分钟

**排查步骤**：
```bash
# 查看容器内部健康检查日志
docker inspect amazon-ai-app | grep -A 20 "Health"

# 手动测试健康检查
docker exec amazon-ai-app curl -f http://localhost:8000/health

# 查看应用启动日志
docker logs amazon-ai-app --tail=50
```

**常见原因**：
- `.env` 文件没挂载（应用启动时找不到配置）
- 数据库还没完全启动（`depends_on` 的 postgres healthcheck 还没通过）
- 端口被占用

### ❓ 问题六：SSL 证书过期

**症状**：浏览器显示"您的连接不是私密连接"

**解决方法**：
```bash
# 手动续期（certbot 通常自动续期，但有时需要手动触发）
sudo certbot renew

# 重载 nginx
sudo systemctl reload nginx
```

---

## 附录：常用命令速查

```bash
# 查看所有容器状态
docker ps

# 查看应用日志（实时）
docker logs amazon-ai-app -f

# 重启应用
docker compose -f /opt/amazon-ai/deploy/docker/docker-compose.yml restart app

# 完整重新部署
cd /opt/amazon-ai && bash deploy/scripts/deploy.sh

# 手动备份数据库
bash /opt/amazon-ai/deploy/scripts/backup-db.sh

# 运行监控检查
bash /opt/amazon-ai/deploy/scripts/monitor.sh

# 进入数据库操作
docker exec -it amazon-ai-postgres psql -U app_user -d amazon_ai

# 查看服务器资源使用
docker stats

# 查看磁盘使用
df -h
```

---

*如有问题，请查看日志后在群里反馈。提问时请把日志截图一起发出来，这样能更快帮你解决问题！*
