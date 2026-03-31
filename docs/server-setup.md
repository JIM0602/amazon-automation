# 云服务器搭建指南（PUDIWIND AI运营系统）

## 推荐配置
- 云服务商：AWS Lightsail 或 阿里云 ECS
- 节点：新加坡（兼顾国内访问速度和美国亚马逊 API 延迟）
- 配置：2 核 4G 内存，50G SSD，Ubuntu 22.04 LTS
- 预算：约 $20-40/月（AWS Lightsail）

## 购买步骤（AWS Lightsail）
1. 登录 AWS 控制台，进入 Lightsail。
2. 点击“创建实例”。
3. 区域选择新加坡（ap-southeast-1）。
4. 操作系统选择 Ubuntu 22.04 LTS。
5. 选择 2 核 4G 的套餐。
6. 生成并下载 SSH 密钥。
7. 创建实例并等待启动完成。
8. 绑定静态公网 IP。
9. 记录服务器公网 IP、用户名和密钥位置。

[截图占位: 选择区域与系统]
[截图占位: 选择 2核4G 套餐]
[截图占位: 下载 SSH 密钥]
[截图占位: 绑定静态 IP]

## 首次登录
1. 使用 SSH 登录服务器。
2. 先确认系统版本：`lsb_release -a`
3. 确认当前用户不是 root，后续应用也不要用 root 跑。

示例：
```bash
ssh -i ~/.ssh/your-key.pem ubuntu@your-server-ip
```

## 基础软件安装
服务器上需要这些基础软件：
- Python 3.11+
- PostgreSQL 16
- Nginx
- Docker 和 Docker Compose

建议直接执行仓库里的初始化脚本：
```bash
chmod +x scripts/setup-server.sh
sudo ./scripts/setup-server.sh
```

## 安全配置
- 安全组：仅开放 80/443/22（22 只允许你的固定 IP）
- SSH 密钥登录，禁用密码登录
- UFW 防火墙规则：只放行 22、80、443
- **重要：不开放数据库端口到公网**
- 不使用 root 账户运行应用
- 项目文件放在 `/opt/amazon-ai/`，由非 root 用户 `appuser` 管理

### SSH 加固建议
1. 编辑 `/etc/ssh/sshd_config`
2. 确保下面配置开启：
```conf
PasswordAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
```
3. 重启 SSH：`sudo systemctl restart ssh`

### UFW 建议规则
```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 域名和 SSL 证书
- 先把域名 A 记录指向服务器公网 IP
- Nginx 负责对外提供 HTTPS
- 使用 Let's Encrypt 免费 SSL 证书
- 飞书回调必须 HTTPS，所以证书是必须的

### 申请证书示例
```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

## 验证清单
按下面顺序检查是否成功：

### 1）系统基础信息
```bash
lsb_release -a
python3 --version
```
预期：Ubuntu 22.04；Python 3.11+

### 2）PostgreSQL
```bash
sudo systemctl status postgresql
sudo -u postgres psql -c "select version();"
```
预期：PostgreSQL 16 正常运行。

### 3）Nginx
```bash
sudo systemctl status nginx
curl -I http://127.0.0.1
```
预期：Nginx 服务运行，HTTP 返回 200/301。

### 4）Docker
```bash
docker --version
docker compose version
```
预期：Docker 与 Compose 都可用。

### 5）防火墙
```bash
sudo ufw status
```
预期：只看到 22、80、443。

### 6）HTTPS
```bash
curl -I https://your-domain.com
```
预期：能正常返回证书后的 HTTPS 响应。

### 7）部署目录与用户
```bash
id appuser
ls -ld /opt/amazon-ai/
```
预期：存在 appuser，目录归 appuser 管理。

## 备注
- 数据库只允许本机或 Docker 内网访问，绝不直接暴露公网端口。
- 后续上线时，应用进程用 `appuser` 启动，不要用 root。
- 如果飞书回调地址改了，记得同步更新 HTTPS 域名和证书。
