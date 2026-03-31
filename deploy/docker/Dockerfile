# ================================
# PUDIWIND AI System — 多阶段构建 Dockerfile
# 第一阶段：builder（安装依赖）
# 第二阶段：runtime（最小化运行镜像）
# ================================

# ---------- 第一阶段：builder ----------
FROM python:3.11-slim AS builder

# 设置工作目录
WORKDIR /build

# 安装系统构建依赖（psycopg2 需要 libpq-dev，编译型包需要 gcc）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 先复制 requirements.txt，利用 Docker 层缓存
COPY requirements.txt .

# 安装 Python 依赖到指定目录（不安装到系统 Python）
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --target=/build/packages -r requirements.txt


# ---------- 第二阶段：runtime ----------
FROM python:3.11-slim AS runtime

# 安装运行时系统依赖（libpq5 = psycopg2 运行时，curl = 健康检查）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户（安全最佳实践：不以 root 身份运行服务）
RUN useradd -r -s /bin/false -m -d /home/appuser appuser

# 设置工作目录
WORKDIR /app

# 从 builder 阶段复制安装好的 Python 包
COPY --from=builder /build/packages /usr/local/lib/python3.11/site-packages

# 复制应用代码（仅复制必要的源码目录）
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# 设置目录所有权给 appuser
RUN chown -R appuser:appuser /app

# 切换到非 root 用户
USER appuser

# 声明服务端口
EXPOSE 8000

# 健康检查：每 30 秒检查一次，失败 3 次认为不健康
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令：使用 uvicorn 启动 FastAPI 应用
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
