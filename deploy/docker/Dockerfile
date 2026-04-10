# ================================
# PUDIWIND AI System — 多阶段构建 Dockerfile
# 第一阶段：frontend-builder（构建前端 SPA）
# 第二阶段：builder（安装 Python 依赖）
# 第三阶段：runtime（最小化运行镜像）
# ================================

# ---------- Stage 1: Frontend Build ----------
FROM node:20-slim AS frontend-builder
WORKDIR /frontend
COPY src/frontend/package.json src/frontend/package-lock.json* ./
RUN npm ci --ignore-scripts || npm install
COPY src/frontend/ ./
RUN npm run build
# Output: /frontend/dist/

# ---------- Stage 2: Python Builder ----------
FROM python:3.12-slim AS builder

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


# ---------- Stage 3: Runtime ----------
FROM python:3.12-slim AS runtime

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
COPY --from=builder /build/packages /usr/local/lib/python3.12/site-packages

# 复制应用代码（仅复制必要的源码目录）
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Copy frontend build output to a directory Nginx will serve
COPY --from=frontend-builder /frontend/dist /app/frontend_dist

# 设置目录所有权给 appuser
RUN chown -R appuser:appuser /app

# 切换到非 root 用户
USER appuser

# 声明服务端口
EXPOSE 8000

# 健康检查：每 30 秒检查一次，失败 3 次认为不健康
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令：先运行 Alembic 数据库迁移，再启动 uvicorn
CMD ["sh", "-c", "python -m alembic upgrade head && python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 2"]
