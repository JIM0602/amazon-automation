# Phase 1 deployment runbook

This runbook covers the minimum server deployment path for the Phase 1 operator trial: sales dashboard, ads dashboard, ads management, Amazon Ads sync, SP-API sales sync, and ads action logs.

## Required environment variables

Backend:

```bash
DATABASE_URL=postgresql://app_user:strong_password@127.0.0.1:5432/amazon_ai
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
DRY_RUN=false
JWT_SECRET=replace-with-long-random-secret
JWT_ACCESS_EXPIRE_MINUTES=480
JWT_REFRESH_EXPIRE_DAYS=7
```

Amazon Ads API, required for ads sync and real write actions:

```bash
AMAZON_ADS_CLIENT_ID=
AMAZON_ADS_CLIENT_SECRET=
AMAZON_ADS_REFRESH_TOKEN=
AMAZON_ADS_PROFILE_ID=
AMAZON_ADS_REGION=NA
```

Amazon SP-API, required for sales sync:

```bash
AMAZON_SP_API_CLIENT_ID=
AMAZON_SP_API_CLIENT_SECRET=
AMAZON_SP_API_APP_ID=
AMAZON_SP_API_REFRESH_TOKEN=
AMAZON_MARKETPLACE_ID=ATVPDKIKX0DER
```

Optional Phase 1 values:

```bash
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
SELLER_SPRITE_API_KEY=
FEISHU_APP_ID=
FEISHU_APP_SECRET=
```

## Production layout

The current production server uses Docker Compose rather than a bare `uvicorn` process:

```text
Host: ubuntu@52.221.207.30
Domain: https://siqiangshangwu.com
Project path: /opt/amazon-ai
Compose path: /opt/amazon-ai/deploy/docker/docker-compose.yml
Containers:
  amazon-ai-app       FastAPI backend, runs alembic upgrade head on startup
  amazon-ai-nginx     Nginx reverse proxy and frontend static files
  amazon-ai-postgres  PostgreSQL + pgvector
Volumes:
  amazon-ai-postgres-data
  amazon-ai-frontend-dist
  amazon-ai-app-logs
```

The Docker image builds the frontend during `docker compose build app` and copies the built assets into the `amazon-ai-frontend-dist` volume for Nginx.

## Database migration

Install backend dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run migrations:

```bash
export DATABASE_URL=postgresql://app_user:strong_password@127.0.0.1:5432/amazon_ai
alembic heads
alembic upgrade head
alembic current
```

Expected head:

```text
007_add_phase1_tables (head)
```

Phase 1 tables created by the latest migration:

```text
skus
sales_daily
inventory_daily
ads_campaigns
ads_ad_groups
ads_targeting
ads_search_terms
ads_negative_targeting
ads_metrics_daily
ads_action_logs
sync_jobs
```

## Docker deployment

```bash
ssh -i /path/to/Pudiwind.pem ubuntu@52.221.207.30
cd /opt/amazon-ai
git fetch origin
git checkout main
git pull --ff-only origin main
```

Configure `/opt/amazon-ai/.env` with the required variables from the first section. Then deploy:

```bash
cd /opt/amazon-ai/deploy/docker
sudo docker compose down
sudo docker volume rm amazon-ai-frontend-dist 2>/dev/null || true
sudo docker compose build app
sudo docker compose up -d
```

The `amazon-ai-app` container startup command runs:

```bash
python -m alembic upgrade head
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 2
```

Health checks:

```bash
sudo docker compose ps
sudo docker compose logs --tail=120 app
curl -fsS http://127.0.0.1:8000/health
curl -fsS https://siqiangshangwu.com/health
```

## Nginx routing

Nginx runs in `amazon-ai-nginx`, reads `deploy/nginx/nginx.conf`, serves `/usr/share/nginx/html` from the `amazon-ai-frontend-dist` volume, and proxies `/api/` to `app:8000`.

Minimum route shape:

```nginx
location / {
    root /usr/share/nginx/html;
    try_files $uri $uri/ /index.html;
}

location /api/ {
    proxy_pass http://api;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Keep a dedicated `/api/sync/` location with longer timeouts. The first real Amazon Ads sync can take several minutes while waiting for Ads reporting jobs; if it uses the generic `/api/` 120-second timeout, Nginx can return `504` even though the backend job continues and eventually writes `sync_jobs=success`.

```nginx
location /api/sync/ {
    proxy_pass http://api;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 10s;
    proxy_send_timeout    900s;
    proxy_read_timeout    900s;
}
```

## First sync and validation

After credentials are configured and migrations are complete:

```bash
curl -X POST "http://127.0.0.1:8000/api/sync/sales?start_date=2026-04-01&end_date=2026-04-02" -H "Authorization: Bearer <token>"
curl -X POST "http://127.0.0.1:8000/api/sync/ads?start_date=2026-04-01&end_date=2026-04-02" -H "Authorization: Bearer <token>"
```

The first ads sync can take several minutes because Phase 1 pulls campaigns, ad groups, targets, negative targets, campaign performance, and search term reports. Keep the backend process running until the sync endpoint returns and then check `sync_jobs` for status, record count, and `extra_payload.list_diagnostics`.

If the public domain returns a proxy timeout during Ads sync, verify whether the backend completed the job before retrying:

```sql
select job_type, status, records_count, error_message, started_at, finished_at
from sync_jobs
order by started_at desc
limit 5;
```

Ads v3 list pagination now continues until `nextToken` is exhausted. A safety limit is still present to avoid an infinite loop; if that limit is reached, the sync job is marked `failed` and `sync_jobs.extra_payload` records the endpoint, pages read, items read, and incomplete status.

Minimum DB checks after the first sync:

```sql
select count(*) from sales_daily;
select count(*) from ads_campaigns;
select count(*) from ads_ad_groups;
select count(*) from ads_targeting;
select count(*) from ads_search_terms;
select count(*) from ads_negative_targeting;
select count(*) from ads_metrics_daily;
select count(*) from ads_action_logs;
```

Minimum API smoke checks:

```bash
curl "http://127.0.0.1:8000/api/dashboard/metrics?time_range=this_month" -H "Authorization: Bearer <token>"
curl "http://127.0.0.1:8000/api/dashboard/trend?time_range=this_month" -H "Authorization: Bearer <token>"
curl "http://127.0.0.1:8000/api/dashboard/sku_ranking?time_range=this_month" -H "Authorization: Bearer <token>"
curl "http://127.0.0.1:8000/api/ads/dashboard/metrics?time_range=this_month" -H "Authorization: Bearer <token>"
curl "http://127.0.0.1:8000/api/ads/dashboard/trend?time_range=this_month" -H "Authorization: Bearer <token>"
curl "http://127.0.0.1:8000/api/ads/dashboard/campaign_ranking?time_range=this_month" -H "Authorization: Bearer <token>"
curl "http://127.0.0.1:8000/api/ads/campaigns?page_size=5" -H "Authorization: Bearer <token>"
curl "http://127.0.0.1:8000/api/ads/ad_groups?page_size=5" -H "Authorization: Bearer <token>"
curl "http://127.0.0.1:8000/api/ads/targeting?page_size=5" -H "Authorization: Bearer <token>"
curl "http://127.0.0.1:8000/api/ads/search_terms?page_size=5" -H "Authorization: Bearer <token>"
curl "http://127.0.0.1:8000/api/ads/negative_targeting?page_size=5" -H "Authorization: Bearer <token>"
curl "http://127.0.0.1:8000/api/ads/logs?page_size=5" -H "Authorization: Bearer <token>"
```

Operator-trial checklist:

```text
1. Login succeeds.
2. Sales dashboard loads real DB aggregates.
3. Ads dashboard loads real DB aggregates.
4. Campaign list loads.
5. Ad group list loads.
6. Targeting, search terms, and negative targeting load.
7. Pause and resume actions submit.
8. Campaign budget update submits.
9. Keyword bid update submits.
10. Negative keyword creation submits.
11. ads_action_logs shows every write action.
```

SKU ranking behavior for the current Phase 1 sync:

```text
sales/v1/orderMetrics provides store-level sales totals, not SKU-level sales rows.
The backend stores that aggregate as __store_total__ for dashboard metric cards, but SKU ranking explicitly excludes it.
If no real SKU-level sales rows exist in sales_daily, /api/dashboard/sku_ranking returns an empty items list plus data_quality.is_degraded=true and an explanatory message for the frontend.
```

## Credential notes

Phase 1 requires real Amazon Ads and SP-API credentials in the backend environment. Do not commit real secrets. Keep `DRY_RUN=false` for operator trial only after credentials are configured and the account/profile has been confirmed.

## Rollback

Before production deployment, take a database backup. If Phase 1 migration must be rolled back:

```bash
alembic downgrade 006_add_agent_configs
```

Then redeploy the previous backend and frontend build.
