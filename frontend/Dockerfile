# ================================
# PUDIWIND AI Console — Next.js 前端 Dockerfile
# 多阶段构建：deps → builder → runner
# ================================

# ---------- 阶段 1：安装依赖 ----------
FROM node:20-alpine AS deps
WORKDIR /app

# 复制 package 文件，利用 Docker 层缓存
COPY package.json package-lock.json* ./
RUN npm ci --only=production

# ---------- 阶段 2：构建 ----------
FROM node:20-alpine AS builder
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# 构建时 API URL 设为空 → 浏览器请求走相对路径 /api/* → nginx 反代到 FastAPI
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_API_URL=
RUN npm run build

# ---------- 阶段 3：运行 ----------
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# 创建非 root 用户
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 复制 standalone 输出（由 next.config.mjs output: "standalone" 生成）
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
