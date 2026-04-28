"""add phase 1 dashboard and ads tables

Revision ID: 007_add_phase1_tables
Revises: 006_add_agent_configs
Create Date: 2026-04-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "007_add_phase1_tables"
down_revision = "006_add_agent_configs"
branch_labels = None
depends_on = None


def _uuid_type():
    if op.get_bind().dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.String(36)


def upgrade() -> None:
    op.create_table(
        "skus",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("product_id", _uuid_type(), nullable=True),
        sa.Column("sku", sa.String(length=128), nullable=False),
        sa.Column("asin", sa.String(length=32), nullable=True),
        sa.Column("marketplace", sa.String(length=32), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku"),
    )
    op.create_index("ix_skus_asin", "skus", ["asin"])
    op.create_index("ix_skus_marketplace", "skus", ["marketplace"])
    op.create_index("ix_skus_product_id", "skus", ["product_id"])
    op.create_index("ix_skus_sku", "skus", ["sku"])

    op.create_table(
        "sales_daily",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("sku", sa.String(length=128), nullable=False),
        sa.Column("asin", sa.String(length=32), nullable=True),
        sa.Column("marketplace", sa.String(length=32), nullable=False),
        sa.Column("sales_amount", sa.Float(), nullable=False),
        sa.Column("order_count", sa.Integer(), nullable=False),
        sa.Column("units_sold", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("snapshot_type", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date", "sku", "marketplace", "snapshot_type", name="uq_sales_daily_date_sku_marketplace_snapshot"),
    )
    op.create_index("ix_sales_daily_asin", "sales_daily", ["asin"])
    op.create_index("ix_sales_daily_date", "sales_daily", ["date"])
    op.create_index("ix_sales_daily_marketplace", "sales_daily", ["marketplace"])
    op.create_index("ix_sales_daily_sku", "sales_daily", ["sku"])

    op.create_table(
        "inventory_daily",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("sku", sa.String(length=128), nullable=False),
        sa.Column("asin", sa.String(length=32), nullable=True),
        sa.Column("fba_available", sa.Integer(), nullable=False),
        sa.Column("inbound_quantity", sa.Integer(), nullable=False),
        sa.Column("reserved_quantity", sa.Integer(), nullable=False),
        sa.Column("estimated_days", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date", "sku", name="uq_inventory_daily_date_sku"),
    )
    op.create_index("ix_inventory_daily_asin", "inventory_daily", ["asin"])
    op.create_index("ix_inventory_daily_date", "inventory_daily", ["date"])
    op.create_index("ix_inventory_daily_sku", "inventory_daily", ["sku"])

    op.create_table(
        "ads_campaigns",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("campaign_id", sa.String(length=64), nullable=False),
        sa.Column("portfolio_id", sa.String(length=64), nullable=True),
        sa.Column("campaign_name", sa.String(length=512), nullable=False),
        sa.Column("ad_type", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("serving_status", sa.String(length=64), nullable=True),
        sa.Column("daily_budget", sa.Float(), nullable=True),
        sa.Column("budget_currency", sa.String(length=8), nullable=False),
        sa.Column("bidding_strategy", sa.String(length=128), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id"),
    )
    op.create_index("ix_ads_campaigns_ad_type", "ads_campaigns", ["ad_type"])
    op.create_index("ix_ads_campaigns_campaign_id", "ads_campaigns", ["campaign_id"])
    op.create_index("ix_ads_campaigns_portfolio_id", "ads_campaigns", ["portfolio_id"])
    op.create_index("ix_ads_campaigns_serving_status", "ads_campaigns", ["serving_status"])
    op.create_index("ix_ads_campaigns_state", "ads_campaigns", ["state"])

    op.create_table(
        "ads_ad_groups",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("ad_group_id", sa.String(length=64), nullable=False),
        sa.Column("campaign_id", sa.String(length=64), nullable=False),
        sa.Column("group_name", sa.String(length=512), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("default_bid", sa.Float(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ad_group_id"),
    )
    op.create_index("ix_ads_ad_groups_ad_group_id", "ads_ad_groups", ["ad_group_id"])
    op.create_index("ix_ads_ad_groups_campaign_id", "ads_ad_groups", ["campaign_id"])
    op.create_index("ix_ads_ad_groups_state", "ads_ad_groups", ["state"])

    op.create_table(
        "ads_targeting",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("targeting_id", sa.String(length=64), nullable=False),
        sa.Column("campaign_id", sa.String(length=64), nullable=False),
        sa.Column("ad_group_id", sa.String(length=64), nullable=True),
        sa.Column("keyword_text", sa.String(length=512), nullable=True),
        sa.Column("match_type", sa.String(length=64), nullable=True),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("bid", sa.Float(), nullable=True),
        sa.Column("suggested_bid", sa.Float(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("targeting_id"),
    )
    op.create_index("ix_ads_targeting_ad_group_id", "ads_targeting", ["ad_group_id"])
    op.create_index("ix_ads_targeting_campaign_id", "ads_targeting", ["campaign_id"])
    op.create_index("ix_ads_targeting_keyword_text", "ads_targeting", ["keyword_text"])
    op.create_index("ix_ads_targeting_state", "ads_targeting", ["state"])
    op.create_index("ix_ads_targeting_targeting_id", "ads_targeting", ["targeting_id"])

    op.create_table(
        "ads_search_terms",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("campaign_id", sa.String(length=64), nullable=False),
        sa.Column("ad_group_id", sa.String(length=64), nullable=True),
        sa.Column("search_term", sa.String(length=512), nullable=False),
        sa.Column("targeting_keyword", sa.String(length=512), nullable=True),
        sa.Column("match_type", sa.String(length=64), nullable=True),
        sa.Column("impressions", sa.Integer(), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False),
        sa.Column("cost", sa.Float(), nullable=False),
        sa.Column("ad_orders", sa.Integer(), nullable=False),
        sa.Column("ad_sales", sa.Float(), nullable=False),
        sa.Column("acos", sa.Float(), nullable=False),
        sa.Column("cvr", sa.Float(), nullable=False),
        sa.Column("suggested_bid", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ads_search_terms_ad_group_id", "ads_search_terms", ["ad_group_id"])
    op.create_index("ix_ads_search_terms_campaign_id", "ads_search_terms", ["campaign_id"])
    op.create_index("ix_ads_search_terms_date", "ads_search_terms", ["date"])
    op.create_index("ix_ads_search_terms_search_term", "ads_search_terms", ["search_term"])

    op.create_table(
        "ads_negative_targeting",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("negative_id", sa.String(length=64), nullable=True),
        sa.Column("campaign_id", sa.String(length=64), nullable=False),
        sa.Column("ad_group_id", sa.String(length=64), nullable=True),
        sa.Column("keyword_text", sa.String(length=512), nullable=False),
        sa.Column("match_type", sa.String(length=64), nullable=True),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("negative_id"),
    )
    op.create_index("ix_ads_negative_targeting_ad_group_id", "ads_negative_targeting", ["ad_group_id"])
    op.create_index("ix_ads_negative_targeting_campaign_id", "ads_negative_targeting", ["campaign_id"])
    op.create_index("ix_ads_negative_targeting_keyword_text", "ads_negative_targeting", ["keyword_text"])
    op.create_index("ix_ads_negative_targeting_negative_id", "ads_negative_targeting", ["negative_id"])
    op.create_index("ix_ads_negative_targeting_state", "ads_negative_targeting", ["state"])

    op.create_table(
        "ads_metrics_daily",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("campaign_id", sa.String(length=64), nullable=False),
        sa.Column("ad_group_id", sa.String(length=64), nullable=True),
        sa.Column("portfolio_id", sa.String(length=64), nullable=True),
        sa.Column("sku", sa.String(length=128), nullable=True),
        sa.Column("impressions", sa.Integer(), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False),
        sa.Column("ctr", sa.Float(), nullable=False),
        sa.Column("cost", sa.Float(), nullable=False),
        sa.Column("cpc", sa.Float(), nullable=False),
        sa.Column("ad_orders", sa.Integer(), nullable=False),
        sa.Column("ad_units", sa.Integer(), nullable=False),
        sa.Column("ad_sales", sa.Float(), nullable=False),
        sa.Column("acos", sa.Float(), nullable=False),
        sa.Column("tacos", sa.Float(), nullable=False),
        sa.Column("cvr", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date", "campaign_id", "ad_group_id", "sku", name="uq_ads_metrics_daily_grain"),
    )
    op.create_index("ix_ads_metrics_daily_ad_group_id", "ads_metrics_daily", ["ad_group_id"])
    op.create_index("ix_ads_metrics_daily_campaign_id", "ads_metrics_daily", ["campaign_id"])
    op.create_index("ix_ads_metrics_daily_date", "ads_metrics_daily", ["date"])
    op.create_index("ix_ads_metrics_daily_portfolio_id", "ads_metrics_daily", ["portfolio_id"])
    op.create_index("ix_ads_metrics_daily_sku", "ads_metrics_daily", ["sku"])

    op.create_table(
        "ads_action_logs",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("action_key", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=False),
        sa.Column("operator_username", sa.String(length=128), nullable=False),
        sa.Column("request_payload", sa.JSON(), nullable=True),
        sa.Column("response_payload", sa.JSON(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ads_action_logs_action_key", "ads_action_logs", ["action_key"])
    op.create_index("ix_ads_action_logs_created_at", "ads_action_logs", ["created_at"])
    op.create_index("ix_ads_action_logs_operator_username", "ads_action_logs", ["operator_username"])
    op.create_index("ix_ads_action_logs_success", "ads_action_logs", ["success"])
    op.create_index("ix_ads_action_logs_target_id", "ads_action_logs", ["target_id"])
    op.create_index("ix_ads_action_logs_target_type", "ads_action_logs", ["target_type"])

    op.create_table(
        "sync_jobs",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("job_name", sa.String(length=128), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("records_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("extra_payload", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sync_jobs_job_name", "sync_jobs", ["job_name"])
    op.create_index("ix_sync_jobs_job_type", "sync_jobs", ["job_type"])
    op.create_index("ix_sync_jobs_status", "sync_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("sync_jobs")
    op.drop_table("ads_action_logs")
    op.drop_table("ads_metrics_daily")
    op.drop_table("ads_negative_targeting")
    op.drop_table("ads_search_terms")
    op.drop_table("ads_targeting")
    op.drop_table("ads_ad_groups")
    op.drop_table("ads_campaigns")
    op.drop_table("inventory_daily")
    op.drop_table("sales_daily")
    op.drop_table("skus")
