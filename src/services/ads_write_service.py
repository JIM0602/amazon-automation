"""Phase-1 Amazon Ads write service with mandatory audit logs."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.amazon_ads_api.auth import AmazonAdsAuth
from src.config import settings
from src.db.models import AdsActionLog, AdsAdGroup, AdsCampaign, AdsNegativeTargeting, AdsTargeting
from src.services.phase1_common import safe_float


class AdsWriteError(Exception):
    """Raised when a supported ads write action cannot be executed."""


def execute_ads_action(
    db: Session,
    action_key: str,
    target_type: str,
    target_ids: list[str],
    payload: dict[str, Any],
    operator_username: str,
) -> dict[str, Any]:
    if not target_ids:
        raise AdsWriteError("target_ids is required")

    normalized_action_key = _normalize_action_key(action_key, target_type, payload)

    has_credentials = all([
        settings.AMAZON_ADS_CLIENT_ID,
        settings.AMAZON_ADS_CLIENT_SECRET,
        settings.AMAZON_ADS_REFRESH_TOKEN,
        settings.AMAZON_ADS_PROFILE_ID,
    ])
    dry_run = settings.DRY_RUN or not has_credentials
    responses: list[dict[str, Any]] = []
    success = True
    error_message = ""

    for target_id in target_ids:
        try:
            response = _execute_one(action_key, target_type, target_id, payload, dry_run)
            if _ads_response_has_errors(response):
                raise AdsWriteError(f"Amazon Ads returned item errors: {response}")
            responses.append(response)
            if not dry_run:
                _apply_successful_local_cache(db, normalized_action_key, target_type, target_id, payload, response)
            _record_log(db, normalized_action_key, target_type, target_id, operator_username, payload, response, True, None)
        except Exception as exc:
            success = False
            error_message = str(exc)
            response = {"error": error_message}
            responses.append(response)
            _record_log(db, normalized_action_key, target_type, target_id, operator_username, payload, response, False, error_message)
            if not dry_run:
                break

    return {
        "result": "success" if success else "failed",
        "action_key": normalized_action_key,
        "target_type": target_type,
        "target_ids": target_ids,
        "level": "low_risk",
        "committed": success,
        "is_real_write": not dry_run,
        "should_reload": True,
        "message": _message(normalized_action_key, success, dry_run, error_message),
        "payload": {
            "request": payload,
            "responses": responses,
            "missing_credentials": not has_credentials,
            "dry_run": dry_run,
        },
    }


def _execute_one(
    action_key: str,
    target_type: str,
    target_id: str,
    payload: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any]:
    action_key = _normalize_action_key(action_key, target_type, payload)
    if action_key in {"pause_campaign", "resume_campaign"}:
        state = "PAUSED" if action_key == "pause_campaign" else "ENABLED"
        body = {"campaigns": [{"campaignId": target_id, "state": state}]}
        return _ads_request("PUT", "/sp/campaigns", body, dry_run, "application/vnd.spcampaign.v3+json")

    if action_key in {"pause_ad_group", "resume_ad_group"}:
        state = "PAUSED" if action_key == "pause_ad_group" else "ENABLED"
        body = {"adGroups": [{"adGroupId": target_id, "state": state}]}
        return _ads_request("PUT", "/sp/adGroups", body, dry_run, "application/vnd.spadgroup.v3+json")

    if action_key == "update_campaign_budget":
        budget = payload.get("daily_budget", payload.get("budget", payload.get("budgetValue")))
        if budget is None:
            raise AdsWriteError("daily_budget is required")
        body = {"campaigns": [{"campaignId": target_id, "budget": {"budget": safe_float(budget), "budgetType": "DAILY"}}]}
        return _ads_request("PUT", "/sp/campaigns", body, dry_run, "application/vnd.spcampaign.v3+json")

    if action_key == "update_keyword_bid":
        bid = payload.get("bid", payload.get("bidValue"))
        if bid is None:
            raise AdsWriteError("bid is required")
        body = {"targetingClauses": [{"targetId": target_id, "bid": safe_float(bid)}]}
        return _ads_request("PUT", "/sp/targets", body, dry_run, "application/vnd.sptargetingClause.v3+json")

    if action_key == "add_negative_keyword":
        keyword = payload.get("keyword") or payload.get("keyword_text") or payload.get("keywordText")
        if not keyword:
            raise AdsWriteError("keyword is required")
        campaign_id = payload.get("campaign_id") or (target_id if target_type == "campaign" else None)
        ad_group_id = payload.get("ad_group_id") or (target_id if target_type == "ad_group" else None)
        if not campaign_id:
            raise AdsWriteError("campaign_id is required")
        if not ad_group_id:
            raise AdsWriteError("ad_group_id is required")
        match_type = _normalize_negative_match_type(str(payload.get("match_type") or payload.get("matchType") or "negativeExact"))
        body = {
            "negativeKeywords": [{
            "campaignId": str(campaign_id),
            "adGroupId": str(ad_group_id),
            "state": "ENABLED",
            "keywordText": str(keyword),
            "matchType": match_type,
        }]
        }
        return _ads_request("POST", "/sp/negativeKeywords", body, dry_run, "application/vnd.spnegativekeyword.v3+json")

    raise AdsWriteError(f"Unsupported action_key: {action_key}")


def _normalize_action_key(action_key: str, target_type: str | None, payload: dict[str, Any]) -> str:
    if action_key == "edit_budget":
        return "update_campaign_budget"
    if action_key == "edit_bid":
        return "update_keyword_bid"
    if action_key == "change_status":
        next_status = str(payload.get("nextStatus") or payload.get("state") or "").lower()
        if target_type == "ad_group":
            return "resume_ad_group" if next_status == "enabled" else "pause_ad_group"
        return "resume_campaign" if next_status == "enabled" else "pause_campaign"
    return action_key


def _normalize_negative_match_type(match_type: str) -> str:
    values = {
        "negative_exact": "NEGATIVE_EXACT",
        "negative_phrase": "NEGATIVE_PHRASE",
        "negativeexact": "NEGATIVE_EXACT",
        "negativephrase": "NEGATIVE_PHRASE",
        "negativeExact": "NEGATIVE_EXACT",
        "negativePhrase": "NEGATIVE_PHRASE",
    }
    return values.get(match_type, match_type)


def _created_negative_keyword_id(response: dict[str, Any]) -> str | None:
    negative_keywords = response.get("negativeKeywords")
    if isinstance(negative_keywords, dict):
        success = negative_keywords.get("success")
        if isinstance(success, list) and success:
            value = success[0]
            if isinstance(value, dict):
                return str(value.get("negativeKeywordId") or "") or None
    return None


def _apply_successful_local_cache(
    db: Session,
    action_key: str,
    target_type: str,
    target_id: str,
    payload: dict[str, Any],
    response: dict[str, Any],
) -> None:
    if action_key in {"pause_campaign", "resume_campaign"}:
        state = "PAUSED" if action_key == "pause_campaign" else "ENABLED"
        _update_campaign_state(db, target_id, state)
        return

    if action_key in {"pause_ad_group", "resume_ad_group"}:
        state = "PAUSED" if action_key == "pause_ad_group" else "ENABLED"
        _update_ad_group_state(db, target_id, state)
        return

    if action_key == "update_campaign_budget":
        budget = payload.get("daily_budget", payload.get("budget", payload.get("budgetValue")))
        campaign = db.execute(select(AdsCampaign).where(AdsCampaign.campaign_id == target_id)).scalar_one_or_none()
        if campaign is not None and budget is not None:
            campaign.daily_budget = safe_float(budget)
        return

    if action_key == "update_keyword_bid":
        bid = payload.get("bid", payload.get("bidValue"))
        targeting = db.execute(select(AdsTargeting).where(AdsTargeting.targeting_id == target_id)).scalar_one_or_none()
        if targeting is not None and bid is not None:
            targeting.bid = safe_float(bid)
        return

    if action_key == "add_negative_keyword":
        keyword = payload.get("keyword") or payload.get("keyword_text") or payload.get("keywordText")
        campaign_id = payload.get("campaign_id") or (target_id if target_type == "campaign" else None)
        ad_group_id = payload.get("ad_group_id") or (target_id if target_type == "ad_group" else None)
        match_type = _normalize_negative_match_type(str(payload.get("match_type") or payload.get("matchType") or "negativeExact"))
        negative_id = _created_negative_keyword_id(response)
        db.add(AdsNegativeTargeting(
            negative_id=str(negative_id or f"amazon-confirmed:{campaign_id}:{ad_group_id}:{keyword}"),
            campaign_id=str(campaign_id),
            ad_group_id=str(ad_group_id) if ad_group_id else None,
            keyword_text=str(keyword),
            match_type=match_type,
            state="enabled",
            last_synced_at=datetime.now(timezone.utc),
            raw_payload=response,
        ))


def _ads_request(method: str, path: str, body: dict[str, Any], dry_run: bool, content_type: str) -> dict[str, Any]:
    if dry_run:
        return {"_dry_run": True, "method": method, "path": path, "body": body}

    auth = AmazonAdsAuth(
        client_id=settings.AMAZON_ADS_CLIENT_ID or "",
        client_secret=settings.AMAZON_ADS_CLIENT_SECRET or "",
        refresh_token=settings.AMAZON_ADS_REFRESH_TOKEN or "",
        region=settings.AMAZON_ADS_REGION,
        dry_run=False,
    )
    base_url = {
        "NA": "https://advertising-api.amazon.com",
        "EU": "https://advertising-api-eu.amazon.com",
        "FE": "https://advertising-api-fe.amazon.com",
    }.get(settings.AMAZON_ADS_REGION, "https://advertising-api.amazon.com")
    req = urllib.request.Request(
        base_url + path,
        data=json.dumps(body).encode("utf-8"),
        method=method,
        headers={
            "Amazon-Advertising-API-ClientId": settings.AMAZON_ADS_CLIENT_ID or "",
            "Amazon-Advertising-API-Scope": settings.AMAZON_ADS_PROFILE_ID or "",
            "Authorization": f"Bearer {auth.get_access_token()}",
            "Content-Type": content_type,
            "Accept": content_type,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw_error = exc.read().decode("utf-8", errors="replace")
        raise AdsWriteError(f"HTTP {exc.code}: {raw_error}") from exc
    return json.loads(raw) if raw else {"status": "ok"}


def _ads_response_has_errors(response: dict[str, Any]) -> bool:
    def has_error(value: Any) -> bool:
        if isinstance(value, dict):
            for key, child in value.items():
                if key.lower() in {"error", "errors"} and bool(child):
                    return True
                if has_error(child):
                    return True
        if isinstance(value, list):
            return any(has_error(item) for item in value)
        return False

    if has_error(response):
        return True
    for value in response.values():
        if isinstance(value, dict) and value.get("error"):
            return True
    return bool(response.get("error"))


def _update_campaign_state(db: Session, campaign_id: str, state: str) -> None:
    campaign = db.execute(select(AdsCampaign).where(AdsCampaign.campaign_id == campaign_id)).scalar_one_or_none()
    if campaign is not None:
        campaign.state = state


def _update_ad_group_state(db: Session, ad_group_id: str, state: str) -> None:
    ad_group = db.execute(select(AdsAdGroup).where(AdsAdGroup.ad_group_id == ad_group_id)).scalar_one_or_none()
    if ad_group is not None:
        ad_group.state = state


def _record_log(
    db: Session,
    action_key: str,
    target_type: str,
    target_id: str,
    operator_username: str,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any],
    success: bool,
    error_message: str | None,
) -> None:
    db.add(AdsActionLog(
        action_key=action_key,
        target_type=target_type,
        target_id=target_id,
        operator_username=operator_username,
        request_payload=request_payload,
        response_payload=response_payload,
        success=success,
        error_message=error_message,
        created_at=datetime.now(timezone.utc),
    ))


def _message(action_key: str, success: bool, dry_run: bool, error: str) -> str:
    if not success:
        return f"{action_key} failed: {error}"
    suffix = " (dry-run/local cache)" if dry_run else ""
    return f"{action_key} completed{suffix}"
