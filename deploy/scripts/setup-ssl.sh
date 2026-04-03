#!/usr/bin/env bash
# ================================
# PUDIWIND AI System — SSL 证书配置脚本
# 使用 Let's Encrypt (certbot) 获取 SSL 证书
# ================================
set -euo pipefail

DOMAIN="siqiangshangwu.com"
EMAIL="${SSL_EMAIL:-admin@${DOMAIN}}"
COMPOSE_FILE="/opt/amazon-ai/deploy/docker/docker-compose.yml"

echo "=========================================="
echo " PUDIWIND AI — SSL 证书配置"
echo "=========================================="

# ---- 前置检查 ----
echo ""
echo "[1/5] 检查 DNS 记录..."
RESOLVED_IP=$(dig +short "${DOMAIN}" 2>/dev/null || true)
SERVER_IP=$(curl -s https://checkip.amazonaws.com 2>/dev/null || true)

if [ -z "${RESOLVED_IP}" ]; then
    echo "❌ 错误: 域名 ${DOMAIN} 无法解析"
    echo "   请先配置 DNS A 记录指向服务器 IP: ${SERVER_IP}"
    echo "   DNS 配置后通常需要等待 5-30 分钟生效"
    exit 1
fi

echo "   域名解析 IP: ${RESOLVED_IP}"
echo "   服务器 IP:   ${SERVER_IP}"

if [ "${RESOLVED_IP}" != "${SERVER_IP}" ]; then
    echo "⚠️  警告: DNS 解析 IP 与当前服务器 IP 不匹配"
    echo "   这可能导致证书申请失败"
    read -p "   是否继续? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "   ✅ DNS 记录正确"

# ---- 安装 certbot ----
echo ""
echo "[2/5] 检查 certbot..."
if ! command -v certbot &> /dev/null; then
    echo "   正在安装 certbot..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq certbot python3-certbot-nginx
    echo "   ✅ certbot 安装完成"
else
    echo "   ✅ certbot 已安装: $(certbot --version 2>&1)"
fi

# ---- 临时启动 nginx（如果未运行）----
echo ""
echo "[3/5] 准备 Nginx..."

# 确保 certbot 验证目录存在
sudo mkdir -p /var/www/certbot

# 检查 nginx 容器是否运行
if docker ps --filter "name=amazon-ai-nginx" --format '{{.Names}}' | grep -q amazon-ai-nginx; then
    echo "   ✅ Nginx 容器已运行"
else
    echo "   正在启动 Nginx..."
    sudo docker compose -f "${COMPOSE_FILE}" up -d nginx
    sleep 3
    echo "   ✅ Nginx 已启动"
fi

# ---- 获取证书 ----
echo ""
echo "[4/5] 申请 SSL 证书..."
echo "   域名: ${DOMAIN}"
echo "   邮箱: ${EMAIL}"
echo ""

sudo certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    -d "${DOMAIN}" \
    -d "www.${DOMAIN}" \
    --email "${EMAIL}" \
    --agree-tos \
    --non-interactive \
    --keep-until-expiring

echo ""
echo "   ✅ SSL 证书获取成功"

# ---- 配置自动续期 ----
echo ""
echo "[5/5] 配置自动续期..."

# certbot 安装时通常已配置 systemd timer，验证一下
if systemctl is-enabled certbot.timer &>/dev/null 2>&1; then
    echo "   ✅ certbot 自动续期已启用 (systemd timer)"
else
    # 添加 cron job 作为备选
    CRON_LINE="0 3 * * * certbot renew --quiet --deploy-hook 'docker exec amazon-ai-nginx nginx -s reload'"
    if ! crontab -l 2>/dev/null | grep -q "certbot renew"; then
        (crontab -l 2>/dev/null; echo "${CRON_LINE}") | crontab -
        echo "   ✅ 已添加 cron 任务: 每天凌晨 3 点自动续期"
    else
        echo "   ✅ certbot 续期 cron 已存在"
    fi
fi

# ---- 重启服务 ----
echo ""
echo "=========================================="
echo " 🎉 SSL 配置完成！"
echo "=========================================="
echo ""
echo " 正在重启 Nginx 加载新证书..."
sudo docker compose -f "${COMPOSE_FILE}" restart nginx
echo ""
echo " 验证："
echo "   curl -I https://${DOMAIN}"
echo "   curl -I http://${DOMAIN}  (应重定向到 HTTPS)"
echo ""
echo " 证书路径："
echo "   /etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
echo "   /etc/letsencrypt/live/${DOMAIN}/privkey.pem"
echo ""
echo " 证书有效期："
sudo certbot certificates --domain "${DOMAIN}" 2>/dev/null || echo "   (运行 certbot certificates 查看)"
