# PUDIWIND AI 运营系统 — 凭证配置指南

本指南详细说明了 PUDIWIND AI 运营系统所需的各项凭证配置。所有配置项均应在项目根目录的 `.env` 文件中设置。你可以参考 `.env.example` 文件进行配置。

## 1. Web 管理控制台配置

Web 控制台使用基于 JWT 的身份验证，并支持多角色访问。

### WEB_USERS 环境变量
该变量用于定义访问控制台的用户及其角色。
- **格式**: `username:bcrypt_hash:role,username2:bcrypt_hash2:role2`
- **角色说明**:
    - `boss`: 管理员权限，可以访问所有功能和设置。
    - `operator`: 运营人员权限，仅限日常业务操作。

### 如何生成 bcrypt 密码哈希
系统不存储明文密码。请使用以下 Python 命令生成安全的密码哈希：
```bash
python -c "from passlib.hash import bcrypt; print(bcrypt.hash('你的密码'))"
```

### 示例配置
```env
WEB_USERS=admin:$2b$12$ExampleHash...:boss,staff1:$2b$12$AnotherHash...:operator
```

### JWT 安全设置
- **JWT_SECRET**: 用于签署令牌的安全密钥。生产环境必须设置一个固定的随机字符串。
    - 生成方式:
      ```bash
      python -c "import secrets; print(secrets.token_hex(32))"
      ```
- **JWT_ACCESS_EXPIRE_MINUTES**: 访问令牌有效期，默认 `480` (8 小时)。
- **JWT_REFRESH_EXPIRE_DAYS**: 刷新令牌有效期，默认 `7` 天。

---

## 2. 亚马逊 SP-API 配置

用于同步亚马逊后台的订单、库存和财务数据。

### 环境变量列表
- `AMAZON_SP_API_ACCESS_KEY`: AWS IAM 用户的访问密钥 ID。
- `AMAZON_SP_API_SECRET_KEY`: AWS IAM 用户的私有访问密钥。
- `AMAZON_SP_API_REFRESH_TOKEN`: LWA 刷新令牌。
- `AMAZON_MARKETPLACE_ID`: 站点 ID（默认 `ATVPDKIKX0DER` 代表美国站）。

### 获取步骤
1. 登录 [Amazon Seller Central](https://sellercentral.amazon.com/)。
2. 进入 **开发者中心 (Developer Central)**。
3. 创建新的 IAM 策略和用户，获取 Access Key 和 Secret Key。
4. 在开发者中心注册应用，授权并获取 LWA Refresh Token。

---

## 3. 亚马逊广告 API 配置

> **说明**: 此部分为 Phase 3b 预留。当前阶段请保持留空，待广告模块上线后补充具体配置要求。

---

## 4. OpenAI API 配置

系统使用 LLM 进行数据分析和策略生成。

### 环境变量列表
- `OPENAI_API_KEY`: 你的 OpenAI API 密钥。
- `OPENAI_MODEL`: 调用的模型名称。
    - 推荐 `gpt-4o-mini`: 性价比极高，适合大部分自动化任务。
    - 推荐 `gpt-4o`: 逻辑推理能力更强，适合复杂分析。

### 获取方式
访问 [OpenAI Platform API Keys](https://platform.openai.com/api-keys) 创建并获取密钥。

---

## 5. 飞书配置

系统通过飞书机器人进行告警、报告推送和交互控制。

### 环境变量列表
- `FEISHU_APP_ID`: 应用凭证 ID。
- `FEISHU_APP_SECRET`: 应用凭证 Secret。
- `FEISHU_VERIFY_TOKEN`: 事件订阅校验令牌。
- `FEISHU_ENCRYPT_KEY`: 消息解密密钥。
- `FEISHU_TEST_CHAT_ID`: 用于接收测试消息的群聊 ID。

### 获取方式
1. 登录 [飞书开放平台](https://open.feishu.cn/)。
2. 创建“企业自建应用”，进入“凭证与基础信息”查看 ID 和 Secret。
3. 在“事件订阅”页面获取校验令牌和加密密钥。

---

## 6. 数据库配置

系统使用 PostgreSQL 存储核心业务数据。

### 环境变量列表
- `DATABASE_URL`: 数据库连接字符串。
    - 格式: `postgresql://user:password@host:port/dbname`
- `POSTGRES_PASSWORD`: 数据库管理员密码（用于容器初始化）。

---

## 7. 配置验证步骤

完成 `.env` 文件配置后，请按以下步骤验证：

1. **验证数据库连接**: 启动系统，检查日志中是否有 `Database connected` 成功信息。
2. **验证 API 认证**: 尝试运行一个简单的 SP-API 或 OpenAI 调用任务，确认无 401/403 错误。
3. **验证飞书机器人**: 调用系统内置的测试指令，确认飞书群能否收到消息。
4. **验证 Web 控制台登录**: 访问控制台 URL，使用生成的账号和原始密码尝试登录。

---

## 8. 安全注意事项

- **严禁提交**: 绝对不要将 `.env` 文件提交到 Git 仓库中。
- **生产密码**: 在生产环境中部署时，必须修改所有默认密码。
- **JWT 稳定性**: `JWT_SECRET` 一旦设定不要随意更改，否则所有已登录用户将被迫下线。
- **定期轮换**: 建议每 90 天轮换一次 API 密钥，尤其是关键的亚马逊和 OpenAI 凭证。
