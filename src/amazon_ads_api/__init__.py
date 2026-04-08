"""Amazon Ads API 客户端包。"""
from .auth import AmazonAdsAuth, AmazonAdsAuthError
from .client import AmazonAdsClient, AmazonAdsClientError, AmazonAdsHttpError
from .campaigns import CampaignsApi, CampaignsApiError
from .reports import ReportsApi, ReportsApiError

__all__ = [
    "AmazonAdsAuth",
    "AmazonAdsAuthError",
    "AmazonAdsClient",
    "AmazonAdsClientError",
    "AmazonAdsHttpError",
    "CampaignsApi",
    "CampaignsApiError",
    "ReportsApi",
    "ReportsApiError",
]
