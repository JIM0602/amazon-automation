#!/bin/bash
# -*- coding: utf-8 -*-
# ================================
# PUDIWIND AI System — 系统监控脚本
# 功能：检查容器状态 + 磁盘/内存使用率 + 飞书告警
# 使用方法：bash monitor.sh
# 建议：crontab 每5分钟执行一次
# crontab 配置：*/5 * * * * bash /opt/amazon-ai/deploy/scripts/monitor.sh
# ================================

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[$(date '+%H:%M:%S')] [INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[$(date '+%H:%M:%S')] [WARN]${NC}  $1"; }
log_alert() { echo -e "${RED}[$(date '+%H:%M:%S')] [ALERT]${NC} $1"; }

# 告警阈值配置
DISK_THRESHOLD=80    # 磁盘使用率超过 80% 告警
MEMORY_THRESHOLD=80  # 内存使用率超过 80% 告警

# 容器名称
APP_CONTAINER="amazon-ai-app"
DB_CONTAINER="amazon-ai-postgres"

# 告警状态（避免重复告警）
ALERT_SENT=false

# 发送飞书告警
send_feishu_alert() {
    local title="$1"
    local message="$2"
    local level="$3"  # warning / critical

    # 检查是否配置了飞书 Webhook
    if [ -z "$FEISHU_WEBHOOK_URL" ]; then
        log_warn "未配置 FEISHU_WEBHOOK_URL，无法发送告警通知"
        return
    fi

    # 根据级别选择 emoji
    local emoji="⚠️"
    if [ "$level" = "critical" ]; then
        emoji="🚨"
    fi

    local hostname
    hostname=$(hostname)

    # 发送飞书消息
    local response
    response=$(curl -s -w "\n%{http_code}" -X POST "$FEISHU_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{
            \"msg_type\": \"post\",
            \"content\": {
                \"post\": {
                    \"zh_cn\": {
                        \"title\": \"$emoji 系统监控告警 — $title\",
                        \"content\": [[
                            {\"tag\": \"text\", \"text\": \"$message\"},
                            {\"tag\": \"text\", \"text\": \"\n服务器: $hostname\"},
                            {\"tag\": \"text\", \"text\": \"\n时间: $(date '+%Y-%m-%d %H:%M:%S')\"}
                        ]]
                    }
                }
            }
        }" 2>&1)

    local http_code
    http_code=$(echo "$response" | tail -n1)

    if [ "$http_code" = "200" ]; then
        log_info "飞书告警已发送：$title"
        ALERT_SENT=true
    else
        log_warn "飞书告警发送失败（HTTP $http_code）"
    fi
}

# 检查 Docker 容器运行状态
check_containers() {
    log_info "检查容器运行状态..."

    # 检查 app 容器
    if docker inspect "$APP_CONTAINER" --format='{{.State.Running}}' 2>/dev/null | grep -q "true"; then
        # 检查健康状态
        local health
        health=$(docker inspect "$APP_CONTAINER" --format='{{.State.Health.Status}}' 2>/dev/null)
        if [ "$health" = "healthy" ]; then
            log_info "✅ app 容器运行正常（健康状态：healthy）"
        elif [ "$health" = "unhealthy" ]; then
            log_alert "❌ app 容器运行但不健康（Health: unhealthy）"
            send_feishu_alert "应用容器不健康" "app 容器正在运行，但健康检查失败！\n请检查：docker logs $APP_CONTAINER" "critical"
        else
            log_info "✅ app 容器运行中（健康状态：$health）"
        fi
    else
        log_alert "❌ app 容器未运行！"
        send_feishu_alert "应用容器停止" "amazon-ai-app 容器已停止运行！\n请检查并重启：docker compose up -d" "critical"
    fi

    # 检查 postgres 容器
    if docker inspect "$DB_CONTAINER" --format='{{.State.Running}}' 2>/dev/null | grep -q "true"; then
        log_info "✅ postgres 容器运行正常"
    else
        log_alert "❌ postgres 容器未运行！"
        send_feishu_alert "数据库容器停止" "amazon-ai-postgres 容器已停止运行！\n这将导致应用无法工作！\n请立即检查：docker compose up -d" "critical"
    fi
}

# 检查磁盘使用率
check_disk_usage() {
    log_info "检查磁盘使用率..."

    # 获取根分区使用率
    local usage
    usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')

    log_info "根分区磁盘使用率：${usage}%"

    if [ "$usage" -ge "$DISK_THRESHOLD" ]; then
        local free_space
        free_space=$(df -h / | awk 'NR==2 {print $4}')

        log_alert "⚠️ 磁盘使用率告警：${usage}% (阈值 ${DISK_THRESHOLD}%，剩余空间 ${free_space})"
        send_feishu_alert "磁盘空间不足" "根分区使用率已达 ${usage}%，超过告警阈值 ${DISK_THRESHOLD}%！\n剩余可用空间：${free_space}\n\n建议：\n- 清理旧 Docker 镜像：docker system prune -a\n- 清理旧备份文件" "warning"
    else
        log_info "✅ 磁盘使用率正常（${usage}% / 阈值 ${DISK_THRESHOLD}%）"
    fi

    # 额外检查备份目录大小
    if [ -d "/opt/amazon-ai/backups" ]; then
        local backup_size
        backup_size=$(du -sh /opt/amazon-ai/backups 2>/dev/null | cut -f1)
        log_info "备份目录大小：${backup_size}"
    fi
}

# 检查内存使用率
check_memory_usage() {
    log_info "检查内存使用率..."

    # 计算内存使用率
    local mem_total mem_available mem_used mem_percent
    mem_total=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    mem_available=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
    mem_used=$((mem_total - mem_available))
    mem_percent=$((mem_used * 100 / mem_total))

    # 人类可读格式
    local mem_total_gb mem_used_gb
    mem_total_gb=$(echo "scale=1; $mem_total / 1024 / 1024" | bc)
    mem_used_gb=$(echo "scale=1; $mem_used / 1024 / 1024" | bc)

    log_info "内存使用率：${mem_percent}% (已用 ${mem_used_gb}GB / 总共 ${mem_total_gb}GB)"

    if [ "$mem_percent" -ge "$MEMORY_THRESHOLD" ]; then
        log_alert "⚠️ 内存使用率告警：${mem_percent}% (阈值 ${MEMORY_THRESHOLD}%)"
        send_feishu_alert "内存使用率过高" "服务器内存使用率已达 ${mem_percent}%，超过告警阈值 ${MEMORY_THRESHOLD}%！\n已用：${mem_used_gb}GB / 总共：${mem_total_gb}GB\n\n建议：\n- 检查是否有内存泄漏\n- 考虑升级服务器配置" "warning"
    else
        log_info "✅ 内存使用率正常（${mem_percent}% / 阈值 ${MEMORY_THRESHOLD}%）"
    fi
}

# 检查应用健康端点
check_app_health() {
    log_info "检查应用健康端点..."

    if curl -sf "http://localhost:8000/health" > /dev/null 2>&1; then
        log_info "✅ 应用健康端点响应正常"
    else
        log_alert "❌ 应用健康端点无响应（http://localhost:8000/health）"
        # 避免重复发送容器告警（如果容器已停止，上面已发过告警）
        if [ "$ALERT_SENT" = "false" ]; then
            send_feishu_alert "应用健康检查失败" "应用健康端点 /health 无响应！\n容器状态看起来正常，但应用可能出现内部错误。\n请检查日志：docker logs $APP_CONTAINER --tail=50" "warning"
        fi
    fi
}

# 输出系统概要信息
print_system_summary() {
    log_info "=========================================="
    log_info "  系统概要信息"
    log_info "  时间：$(date '+%Y-%m-%d %H:%M:%S')"
    log_info "  主机：$(hostname)"
    log_info "=========================================="

    # 显示 Docker 容器状态
    log_info "Docker 容器状态："
    docker ps --format "  {{.Names}}: {{.Status}}" 2>/dev/null || log_warn "无法获取 Docker 容器状态"
}

# 主执行流程
main() {
    # 加载环境变量（用于飞书通知 URL）
    if [ -f "/opt/amazon-ai/.env" ]; then
        set -a
        source "/opt/amazon-ai/.env"
        set +a
    fi

    print_system_summary
    check_containers
    check_disk_usage
    check_memory_usage
    check_app_health

    if [ "$ALERT_SENT" = "true" ]; then
        log_warn "本次监控检测到异常，告警已发送至飞书"
    else
        log_info "✅ 所有监控项正常，无需告警"
    fi
}

main "$@"
