#!/bin/bash
# -*- coding: utf-8 -*-
# ================================
# PUDIWIND AI System — 一键部署脚本
# 流程：git pull → docker build → up -d → 等待健康 → 飞书通知
# 使用方法：bash deploy.sh
# ================================

set -e  # 遇到错误立即停止

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置变量
APP_DIR="/opt/amazon-ai"                          # 应用目录
COMPOSE_FILE="$APP_DIR/deploy/docker/docker-compose.yml"  # compose 文件路径
HEALTH_URL="http://localhost:8000/health"          # 健康检查地址
MAX_WAIT=120                                       # 最长等待秒数

log_info()  { echo -e "${GREEN}[$(date '+%H:%M:%S')] [INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[$(date '+%H:%M:%S')] [WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[$(date '+%H:%M:%S')] [ERROR]${NC} $1"; }
log_step()  { echo -e "${BLUE}[$(date '+%H:%M:%S')] [STEP]${NC}  ====> $1"; }

# 发送飞书通知（通过 Webhook URL 环境变量）
notify_feishu() {
    local message="$1"
    local color="$2"  # red / green / orange

    # 如果没有配置飞书 Webhook，跳过通知
    if [ -z "$FEISHU_WEBHOOK_URL" ]; then
        log_warn "未配置 FEISHU_WEBHOOK_URL，跳过飞书通知"
        return
    fi

    local hostname
    hostname=$(hostname)

    # 发送飞书消息卡片
    curl -s -X POST "$FEISHU_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{
            \"msg_type\": \"post\",
            \"content\": {
                \"post\": {
                    \"zh_cn\": {
                        \"title\": \"🚀 PUDIWIND AI 部署通知\",
                        \"content\": [[
                            {\"tag\": \"text\", \"text\": \"$message\n服务器: $hostname\n时间: $(date '+%Y-%m-%d %H:%M:%S')\"}
                        ]]
                    }
                }
            }
        }" > /dev/null 2>&1 || log_warn "飞书通知发送失败（不影响部署）"

    log_info "飞书通知已发送"
}

# 步骤一：拉取最新代码
step_git_pull() {
    log_step "步骤 1/4：拉取最新代码"

    if [ ! -d "$APP_DIR/.git" ]; then
        log_warn "未检测到 git 仓库，跳过 git pull"
        return
    fi

    cd "$APP_DIR"
    git pull origin main 2>&1 | while read -r line; do
        log_info "  $line"
    done

    log_info "代码更新完成"
}

# 步骤二：构建 Docker 镜像
step_docker_build() {
    log_step "步骤 2/4：构建 Docker 镜像（--no-cache 确保使用最新代码）"

    docker compose -f "$COMPOSE_FILE" build --no-cache 2>&1 | while read -r line; do
        log_info "  $line"
    done

    log_info "镜像构建完成"
}

# 步骤三：启动服务
step_docker_up() {
    log_step "步骤 3/4：启动所有服务"

    # -d 后台运行，--remove-orphans 清理旧容器
    docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

    log_info "容器已启动（后台运行）"
}

# 步骤四：等待健康检查通过
step_wait_healthy() {
    log_step "步骤 4/4：等待服务健康检查通过（最长等待 ${MAX_WAIT} 秒）"

    local waited=0
    local interval=5

    while [ $waited -lt $MAX_WAIT ]; do
        # 尝试访问健康检查端点
        if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
            log_info "✅ 健康检查通过！服务已成功启动"
            return 0
        fi

        log_warn "服务还未就绪，等待 ${interval} 秒... (已等待 ${waited}s / ${MAX_WAIT}s)"
        sleep $interval
        waited=$((waited + interval))
    done

    # 超时失败处理
    log_error "❌ 健康检查超时！服务可能启动失败"
    log_error "查看容器日志：docker compose -f $COMPOSE_FILE logs --tail=50"
    return 1
}

# 主执行流程
main() {
    log_info "=========================================="
    log_info "  PUDIWIND AI System 部署开始"
    log_info "  时间：$(date '+%Y-%m-%d %H:%M:%S')"
    log_info "=========================================="

    # 加载 .env 中的环境变量（用于飞书通知等）
    if [ -f "$APP_DIR/.env" ]; then
        set -a  # 自动导出所有变量
        source "$APP_DIR/.env"
        set +a
    fi

    # 发送部署开始通知
    notify_feishu "🔄 开始部署新版本..." "orange"

    # 执行部署步骤
    if step_git_pull && step_docker_build && step_docker_up && step_wait_healthy; then
        log_info "=========================================="
        log_info "  ✅ 部署成功！"
        log_info "  访问地址：http://your-domain.com/health"
        log_info "=========================================="
        notify_feishu "✅ 部署成功！服务已正常运行" "green"
    else
        log_error "=========================================="
        log_error "  ❌ 部署失败！请查看上方错误信息"
        log_error "=========================================="
        notify_feishu "❌ 部署失败！请立即检查服务器" "red"
        exit 1
    fi
}

main "$@"
