#!/usr/bin/env bash
# =============================================================================
# init-demo.sh — PUDIWIND Demo 一键初始化脚本
#
# 功能:
#   1. 检查运行环境（Python 版本、依赖包）
#   2. 复制 .env.example → .env（如不存在）
#   3. 创建 Mock 数据目录（幂等操作）
#   4. 运行 data/mock/seed_database.py 初始化 DB（支持 --clean 和 --dry-run）
#   5. 打印初始化完成信息
#
# 使用:
#   bash scripts/init-demo.sh             # 正常初始化
#   bash scripts/init-demo.sh --dry-run   # 仅检查，不写 DB
#   bash scripts/init-demo.sh --clean     # 清空后重新初始化
#   bash scripts/init-demo.sh --help      # 帮助信息
#
# 注意:
#   - 不使用 mkdir -p（PowerShell 不兼容），改用 Python 调用
#   - 不使用 export VAR=val（跨 shell 兼容性问题）
#   - 支持 bash / zsh 运行
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MOCK_DIR="${PROJECT_ROOT}/data/mock"
SEED_SCRIPT="${MOCK_DIR}/seed_database.py"

# ---------------------------------------------------------------------------
# 颜色输出
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ---------------------------------------------------------------------------
# 参数解析
# ---------------------------------------------------------------------------
DRY_RUN=false
CLEAN=false

for arg in "$@"; do
    case $arg in
        --dry-run)  DRY_RUN=true ;;
        --clean)    CLEAN=true ;;
        --help|-h)
            echo "用法: bash scripts/init-demo.sh [--dry-run] [--clean] [--help]"
            echo ""
            echo "选项:"
            echo "  --dry-run   仅检查环境和打印操作，不实际写入数据库"
            echo "  --clean     初始化前先清空现有 Demo 数据"
            echo "  --help      显示帮助信息"
            exit 0
            ;;
        *)
            warn "未知参数: $arg（已忽略）"
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
echo "  PUDIWIND Amazon AI Demo 初始化"
echo "  日期: $(date '+%Y-%m-%d %H:%M:%S')"
echo "  模式: $([ "${DRY_RUN}" = true ] && echo 'dry-run' || echo '正常写入')"
echo "  清理: $([ "${CLEAN}" = true ] && echo '是' || echo '否')"
echo "============================================================"
echo ""

# ---------------------------------------------------------------------------
# 步骤 1: 检查 Python 环境
# ---------------------------------------------------------------------------
info "步骤 1/5 — 检查 Python 环境"

if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    error "未找到 Python，请安装 Python 3.10+ 后重试"
    exit 1
fi

PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
info "Python 版本: ${PYTHON_VERSION}"

PYTHON_MAJOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.minor)")

if [ "${PYTHON_MAJOR}" -lt 3 ] || ([ "${PYTHON_MAJOR}" -eq 3 ] && [ "${PYTHON_MINOR}" -lt 10 ]); then
    error "需要 Python 3.10+，当前版本: ${PYTHON_VERSION}"
    exit 1
fi

success "Python 版本检查通过"

# ---------------------------------------------------------------------------
# 步骤 2: 检查项目目录结构
# ---------------------------------------------------------------------------
info "步骤 2/5 — 检查项目目录结构"

cd "${PROJECT_ROOT}"

if [ ! -f "pyproject.toml" ] && [ ! -f "requirements.txt" ] && [ ! -f "setup.py" ]; then
    warn "未找到 pyproject.toml / requirements.txt，请确认当前目录是项目根目录"
fi

success "项目目录: ${PROJECT_ROOT}"

# ---------------------------------------------------------------------------
# 步骤 3: 设置环境变量（.env 文件）
# ---------------------------------------------------------------------------
info "步骤 3/5 — 配置环境变量"

if [ ! -f "${PROJECT_ROOT}/.env" ]; then
    if [ -f "${PROJECT_ROOT}/.env.example" ]; then
        cp "${PROJECT_ROOT}/.env.example" "${PROJECT_ROOT}/.env"
        success "已从 .env.example 创建 .env"
    else
        warn ".env 和 .env.example 均不存在，使用系统默认环境变量"
    fi
else
    success ".env 文件已存在"
fi

# 设置 Mock 模式环境变量（避免需要真实 API）
SELLER_SPRITE_USE_MOCK="${SELLER_SPRITE_USE_MOCK:-true}"
SP_API_USE_MOCK="${SP_API_USE_MOCK:-true}"
info "SELLER_SPRITE_USE_MOCK=${SELLER_SPRITE_USE_MOCK}"
info "SP_API_USE_MOCK=${SP_API_USE_MOCK}"

# ---------------------------------------------------------------------------
# 步骤 4: 创建 Mock 数据目录
# ---------------------------------------------------------------------------
info "步骤 4/5 — 确保 Mock 数据目录存在"

$PYTHON_CMD -c "
import os
dirs = [
    'data/mock/knowledge_base/sample_docs',
    'data/mock/seller_sprite',
    'data/mock/amazon_sp_api',
    '.sisyphus/evidence',
]
for d in dirs:
    os.makedirs(d, exist_ok=True)
    print(f'  [DIR] {d}')
"

success "Mock 数据目录已就绪"

# ---------------------------------------------------------------------------
# 步骤 5: 运行 seed_database.py
# ---------------------------------------------------------------------------
info "步骤 5/5 — 运行数据库初始化脚本"

SEED_ARGS=""
if [ "${CLEAN}" = true ]; then
    SEED_ARGS="${SEED_ARGS} --clean"
fi
if [ "${DRY_RUN}" = true ]; then
    SEED_ARGS="${SEED_ARGS} --dry-run"
fi

if [ ! -f "${SEED_SCRIPT}" ]; then
    error "seed_database.py 不存在: ${SEED_SCRIPT}"
    exit 1
fi

# shellcheck disable=SC2086
SELLER_SPRITE_USE_MOCK="${SELLER_SPRITE_USE_MOCK}" \
SP_API_USE_MOCK="${SP_API_USE_MOCK}" \
$PYTHON_CMD "${SEED_SCRIPT}" ${SEED_ARGS}

SEED_EXIT_CODE=$?

if [ $SEED_EXIT_CODE -ne 0 ]; then
    warn "seed_database.py 退出码: ${SEED_EXIT_CODE}（可能有部分错误，查看上方日志）"
else
    success "数据库初始化完成"
fi

# ---------------------------------------------------------------------------
# 完成信息
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
echo "  初始化完成！"
echo ""
if [ "${DRY_RUN}" = true ]; then
    echo "  [dry-run 模式] 以上为预览，实际未写入数据库"
    echo "  运行正式初始化: bash scripts/init-demo.sh"
else
    echo "  下一步:"
    echo "    1. 启动应用:  uvicorn src.main:app --reload"
    echo "    2. 打开文档:  http://localhost:8000/docs"
    echo "    3. 查看 Demo 数据已通过 seed_database.py 导入"
fi
echo "============================================================"

exit $SEED_EXIT_CODE
