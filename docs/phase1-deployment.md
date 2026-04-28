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

## Backend startup

```bash
source .venv/bin/activate
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Frontend build

```bash
cd src/frontend
npm install
npm run build
```

The static output is:

```text
src/frontend/dist
```

## Nginx routing

Use one server block with the frontend as static root and `/api/` proxied to FastAPI:

```nginx
location / {
    root /opt/amazon-automation/src/frontend/dist;
    try_files $uri $uri/ /index.html;
}

location /api/ {
    proxy_pass http://127.0.0.1:8000/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## First sync and validation

After credentials are configured and migrations are complete:

```bash
curl -X POST "http://127.0.0.1:8000/api/sync/sales?start_date=2026-04-01&end_date=2026-04-02" -H "Authorization: Bearer <token>"
curl -X POST "http://127.0.0.1:8000/api/sync/ads?start_date=2026-04-01&end_date=2026-04-02" -H "Authorization: Bearer <token>"
```

The first ads sync can take several minutes because Phase 1 pulls campaigns, ad groups, targets, negative targets, campaign performance, and search term reports. Keep the backend process running until the sync endpoint returns and then check `sync_jobs` for status and record count.

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

## Credential notes

Phase 1 requires real Amazon Ads and SP-API credentials in the backend environment. Do not commit real secrets. Keep `DRY_RUN=false` for operator trial only after credentials are configured and the account/profile has been confirmed.

## Rollback

Before production deployment, take a database backup. If Phase 1 migration must be rolled back:

```bash
alembic downgrade 006_add_agent_configs
```

Then redeploy the previous backend and frontend build.
