#!/bin/bash
# -*- coding: utf-8 -*-
# ================================
# PUDIWIND AI System — 服务器初始化脚本
# 支持 Ubuntu 20.04/22.04 和 CentOS 7/8
# 使用方法：sudo bash setup-server.sh
# ================================

set -e  # 遇到错误立即停止

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# 检测操作系统类型
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
    else
        log_error "无法检测操作系统类型，请确认使用 Ubuntu 或 CentOS"
    fi

    log_info "检测到操作系统: $OS $OS_VERSION"
}

# 安装 Docker（Ubuntu 版本）
install_docker_ubuntu() {
    log_info "开始安装 Docker（Ubuntu）..."

    # 更新包索引
    apt-get update -y

    # 安装必要的依赖包
    apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        ufw \
        unzip

    # 添加 Docker 官方 GPG 密钥
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
        gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    # 添加 Docker 软件源
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
        tee /etc/apt/sources.list.d/docker.list > /dev/null

    # 安装 Docker Engine 和 Docker Compose v2
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

    log_info "Docker 安装完成"
}

# 安装 Docker（CentOS 版本）
install_docker_centos() {
    log_info "开始安装 Docker（CentOS）..."

    # 安装必要工具
    yum install -y yum-utils ufw

    # 添加 Docker 软件源
    yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

    # 安装 Docker Engine 和 Docker Compose v2
    yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

    log_info "Docker 安装完成"
}

# 启动并配置 Docker 自启动
configure_docker() {
    log_info "配置 Docker 自动启动..."

    systemctl start docker
    systemctl enable docker

    # 验证 Docker 安装是否成功
    if docker --version && docker compose version; then
        log_info "Docker 安装验证成功"
    else
        log_error "Docker 安装失败，请检查错误信息"
    fi
}

# 创建应用目录
create_app_directory() {
    log_info "创建应用目录 /opt/amazon-ai/ ..."

    mkdir -p /opt/amazon-ai
    mkdir -p /opt/amazon-ai/logs
    mkdir -p /opt/amazon-ai/backups
    mkdir -p /opt/amazon-ai/ssl

    log_info "应用目录创建完成"
}

# 配置防火墙（仅开放必要端口）
configure_firewall() {
    log_info "配置防火墙规则..."

    # 检查 UFW 是否可用
    if command -v ufw &> /dev/null; then
        # 先允许 SSH（避免把自己锁在门外！）
        ufw allow 22/tcp comment 'SSH 远程连接'

        # 允许 HTTP（80 端口，用于 Let's Encrypt 验证和 HTTP→HTTPS 重定向）
        ufw allow 80/tcp comment 'HTTP'

        # 允许 HTTPS（443 端口，正式流量）
        ufw allow 443/tcp comment 'HTTPS'

        # ⚠️ 注意：不开放 8000 端口！应用只通过 nginx 代理访问
        # ⚠️ 注意：不开放 5432 端口！数据库只在 Docker 内部网络

        # 启用防火墙（--force 避免交互确认）
        ufw --force enable

        log_info "防火墙配置完成（已开放：22, 80, 443）"
    else
        # CentOS 使用 firewalld
        log_warn "UFW 未找到，尝试使用 firewalld..."
        if command -v firewall-cmd &> /dev/null; then
            systemctl start firewalld
            systemctl enable firewalld
            firewall-cmd --permanent --add-service=ssh
            firewall-cmd --permanent --add-service=http
            firewall-cmd --permanent --add-service=https
            firewall-cmd --reload
            log_info "firewalld 防火墙配置完成"
        else
            log_warn "未找到防火墙工具，请手动配置防火墙"
        fi
    fi
}

# 创建非 root 应用用户
create_app_user() {
    log_info "创建应用用户 appuser ..."

    # 检查用户是否已存在
    if id "appuser" &>/dev/null; then
        log_warn "用户 appuser 已存在，跳过创建"
    else
        # 创建系统用户（无登录 shell，无家目录登录）
        useradd -r -s /bin/false -d /opt/amazon-ai appuser
        log_info "用户 appuser 创建成功"
    fi

    # 将 appuser 加入 docker 组（允许运行 docker 命令）
    usermod -aG docker appuser

    # 设置应用目录所有权
    chown -R appuser:appuser /opt/amazon-ai

    log_info "用户配置完成"
}

# 安装 Nginx（可选，用于反向代理）
install_nginx() {
    log_info "安装 Nginx..."

    if [ "$OS" = "ubuntu" ]; then
        apt-get install -y nginx
    elif [ "$OS" = "centos" ]; then
        yum install -y nginx
    fi

    systemctl start nginx
    systemctl enable nginx

    log_info "Nginx 安装完成"
}

# 系统优化配置
optimize_system() {
    log_info "优化系统配置..."

    # 增加文件描述符上限（高并发场景需要）
    cat >> /etc/security/limits.conf << 'EOF'
* soft nofile 65536
* hard nofile 65536
appuser soft nofile 65536
appuser hard nofile 65536
EOF

    # 优化 TCP 参数
    cat >> /etc/sysctl.conf << 'EOF'
# 优化网络性能
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65535
EOF
    sysctl -p

    log_info "系统优化完成"
}

# 主执行流程
main() {
    log_info "=========================================="
    log_info "  PUDIWIND AI System 服务器初始化开始"
    log_info "=========================================="

    # 检查是否以 root 身份运行
    if [ "$EUID" -ne 0 ]; then
        log_error "请以 root 身份运行此脚本：sudo bash setup-server.sh"
    fi

    # 检测操作系统
    detect_os

    # 根据系统类型安装 Docker
    if [ "$OS" = "ubuntu" ]; then
        install_docker_ubuntu
    elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
        install_docker_centos
    else
        log_error "不支持的操作系统：$OS。请使用 Ubuntu 20.04/22.04 或 CentOS 7/8"
    fi

    # 通用配置步骤
    configure_docker
    create_app_directory
    create_app_user
    configure_firewall
    install_nginx
    optimize_system

    log_info "=========================================="
    log_info "  服务器初始化完成！"
    log_info ""
    log_info "  下一步操作："
    log_info "  1. 上传项目代码到 /opt/amazon-ai/"
    log_info "  2. 创建并配置 .env 文件"
    log_info "  3. 运行 bash deploy.sh 启动服务"
    log_info "=========================================="
}

main "$@"
