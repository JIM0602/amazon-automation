#!/bin/bash
# -*- coding: utf-8 -*-
# ================================
# PUDIWIND AI System — 数据库备份脚本
# 功能：pg_dump 导出 + gzip 压缩 + 保留最近7天
# 使用方法：bash backup-db.sh
# 建议：通过 crontab 每天凌晨3点自动执行
# crontab 配置：0 3 * * * bash /opt/amazon-ai/deploy/scripts/backup-db.sh
# ================================

set -e  # 遇到错误立即停止

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[$(date '+%H:%M:%S')] [INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[$(date '+%H:%M:%S')] [WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[$(date '+%H:%M:%S')] [ERROR]${NC} $1"; }

# 配置变量
BACKUP_DIR="/opt/amazon-ai/backups"           # 备份存储目录
BACKUP_KEEP_DAYS=7                            # 保留最近几天的备份
DB_CONTAINER="amazon-ai-postgres"            # postgres 容器名称
DB_USER="app_user"                           # 数据库用户名
DB_NAME="amazon_ai"                          # 数据库名
COMPOSE_FILE="/opt/amazon-ai/deploy/docker/docker-compose.yml"  # compose 文件

# 生成带时间戳的备份文件名
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILE="$BACKUP_DIR/backup_${DB_NAME}_${TIMESTAMP}.sql.gz"
LOG_FILE="$BACKUP_DIR/backup.log"

# 发送飞书通知（备份失败时）
notify_feishu_error() {
    local message="$1"
    if [ -n "$FEISHU_WEBHOOK_URL" ]; then
        curl -s -X POST "$FEISHU_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{
                \"msg_type\": \"text\",
                \"content\": {
                    \"text\": \"⚠️ 数据库备份失败！\n$message\n时间: $(date '+%Y-%m-%d %H:%M:%S')\"
                }
            }" > /dev/null 2>&1
    fi
}

# 执行备份
do_backup() {
    log_info "开始数据库备份..."
    log_info "备份文件：$BACKUP_FILE"

    # 确保备份目录存在
    mkdir -p "$BACKUP_DIR"

    # 检查 postgres 容器是否运行
    if ! docker inspect "$DB_CONTAINER" --format='{{.State.Running}}' 2>/dev/null | grep -q "true"; then
        log_error "postgres 容器未运行，备份失败！"
        notify_feishu_error "postgres 容器 ($DB_CONTAINER) 未运行"
        exit 1
    fi

    # 执行 pg_dump 并通过管道 gzip 压缩
    # docker exec 在容器内执行 pg_dump，输出通过管道压缩后写入备份文件
    if docker exec "$DB_CONTAINER" \
        pg_dump -U "$DB_USER" -d "$DB_NAME" \
        --no-password \
        --verbose \
        --format=plain | \
        gzip > "$BACKUP_FILE"; then

        # 计算备份文件大小
        BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
        log_info "✅ 备份成功！文件大小：$BACKUP_SIZE"
    else
        log_error "pg_dump 执行失败！"
        notify_feishu_error "pg_dump 执行失败"
        # 删除不完整的备份文件
        rm -f "$BACKUP_FILE"
        exit 1
    fi
}

# 清理超过7天的旧备份
cleanup_old_backups() {
    log_info "清理 $BACKUP_KEEP_DAYS 天前的旧备份..."

    # 查找并删除超过7天的备份文件
    DELETED_COUNT=$(find "$BACKUP_DIR" -name "backup_${DB_NAME}_*.sql.gz" \
        -mtime "+$BACKUP_KEEP_DAYS" \
        -exec rm -f {} \; \
        -print | wc -l)

    if [ "$DELETED_COUNT" -gt 0 ]; then
        log_info "已删除 $DELETED_COUNT 个过期备份文件"
    else
        log_info "没有需要删除的过期备份"
    fi
}

# 列出当前所有备份
list_backups() {
    log_info "当前备份文件列表："
    if ls -lh "$BACKUP_DIR"/backup_*.sql.gz 2>/dev/null; then
        local total
        total=$(find "$BACKUP_DIR" -name "backup_*.sql.gz" | wc -l)
        log_info "共 $total 个备份文件"
    else
        log_warn "备份目录中没有备份文件"
    fi
}

# 记录操作日志
write_log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# 主执行流程
main() {
    log_info "=========================================="
    log_info "  数据库备份任务开始"
    log_info "  时间：$(date '+%Y-%m-%d %H:%M:%S')"
    log_info "=========================================="

    # 加载环境变量（用于飞书通知）
    if [ -f "/opt/amazon-ai/.env" ]; then
        set -a
        source "/opt/amazon-ai/.env"
        set +a
    fi

    # 执行备份
    do_backup
    write_log "备份成功：$BACKUP_FILE"

    # 清理旧备份
    cleanup_old_backups

    # 列出当前备份
    list_backups

    log_info "=========================================="
    log_info "  ✅ 备份任务完成"
    log_info "=========================================="
}

main "$@"
