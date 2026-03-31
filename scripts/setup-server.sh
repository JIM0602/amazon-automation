#!/bin/bash
# 一键初始化 Ubuntu 22.04 服务器
# 功能：
# - 系统更新
# - 安装 Python 3.11
# - 安装 PostgreSQL 16
# - 安装 Nginx
# - 安装 Docker 和 Docker Compose
# - 配置 UFW 防火墙（开放 22/80/443，关闭其他）
# - 创建非 root 部署用户 appuser
# - 设置项目目录 /opt/amazon-ai/
# - 打印安装完成总结

set -Eeuo pipefail

trap 'echo "[错误] 第 ${LINENO} 行执行失败：${BASH_COMMAND}" >&2' ERR

log() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*"; }
die() { echo "[ERROR] $*" >&2; exit 1; }

require_root() {
  if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    die "请使用 root 或 sudo 运行此脚本"
  fi
}

check_os() {
  if [[ ! -f /etc/os-release ]]; then
    die "无法识别操作系统"
  fi
  # shellcheck disable=SC1091
  source /etc/os-release
  case "${ID:-}" in
    ubuntu|debian)
      log "检测到系统：${PRETTY_NAME:-未知}"
      ;;
    *)
      die "仅支持 Ubuntu / Debian 系列系统"
      ;;
  esac
}

ensure_apt_https() {
  apt-get update
  apt-get install -y ca-certificates curl gnupg lsb-release software-properties-common apt-transport-https
}

setup_python311() {
  log "安装 Python 3.11"
  if command -v python3.11 >/dev/null 2>&1; then
    log "Python 3.11 已存在，跳过"
    return
  fi

  if [[ "${ID:-}" == "ubuntu" ]]; then
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update
  fi

  apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip
}

setup_postgresql16() {
  log "安装 PostgreSQL 16"
  if ! command -v psql >/dev/null 2>&1; then
    install -d /etc/apt/keyrings
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/keyrings/postgresql.gpg
    echo "deb [signed-by=/etc/apt/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt ${VERSION_CODENAME:-$(lsb_release -cs)}-pgdg main" > /etc/apt/sources.list.d/pgdg.list
    apt-get update
    apt-get install -y postgresql-16 postgresql-client-16
  else
    warn "系统里已经有 psql，仍会确保 PostgreSQL 相关服务可用"
    apt-get install -y postgresql-16 postgresql-client-16 || true
  fi

  systemctl enable postgresql
  systemctl restart postgresql
}

setup_nginx() {
  log "安装 Nginx"
  apt-get install -y nginx
  systemctl enable nginx
  systemctl restart nginx
}

setup_docker() {
  log "安装 Docker 和 Docker Compose"
  if ! command -v docker >/dev/null 2>&1; then
    apt-get install -y docker.io docker-compose-plugin
  else
    apt-get install -y docker.io docker-compose-plugin || true
  fi
  systemctl enable docker
  systemctl restart docker
}

setup_firewall() {
  log "配置 UFW 防火墙"
  apt-get install -y ufw
  ufw default deny incoming
  ufw default allow outgoing
  ufw allow OpenSSH
  ufw allow 80/tcp
  ufw allow 443/tcp
  ufw --force enable
}

setup_user_and_dir() {
  log "创建部署用户和项目目录"
  if ! id appuser >/dev/null 2>&1; then
    useradd -m -s /bin/bash appuser
  fi
  install -d -o appuser -g appuser /opt/amazon-ai
}

print_summary() {
  log "安装完成，开始输出版本验证信息"
  echo "--- 版本验证 ---"
  python3 --version || true
  python3.11 --version || true
  psql --version || true
  nginx -v 2>&1 || true
  docker --version || true
  docker compose version || true
  echo "--- 防火墙状态 ---"
  ufw status verbose || true
  echo "--- 用户与目录 ---"
  id appuser || true
  ls -ld /opt/amazon-ai/ || true
  echo "--- 完成总结 ---"
  echo "1. Python 3.11 已准备好"
  echo "2. PostgreSQL 16 已准备好（数据库端口不要暴露到公网）"
  echo "3. Nginx 已准备好"
  echo "4. Docker / Docker Compose 已准备好"
  echo "5. UFW 已只放行 22/80/443"
  echo "6. appuser 与 /opt/amazon-ai/ 已创建"
}

main() {
  require_root
  check_os
  ensure_apt_https
  setup_python311
  setup_postgresql16
  setup_nginx
  setup_docker
  setup_firewall
  setup_user_and_dir
  print_summary
}

main "$@"
