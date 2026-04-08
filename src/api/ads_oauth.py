"""Amazon Ads OAuth 回调端点。

临时工具：帮助用户通过 OAuth 授权码流程获取 Amazon Advertising API 的 refresh_token。
获取到 refresh_token 后，将其配置到 .env 中即可。

流程：
1. GET /api/ads-oauth/authorize → 跳转到 Amazon 授权页
2. GET /api/ads-oauth/callback  → 接收授权码，自动换取 refresh_token 并显示
"""
from __future__ import annotations

import logging
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ads-oauth", tags=["ads-oauth"])

# Amazon LWA 端点
AMAZON_AUTH_URL = "https://www.amazon.com/ap/oa"
AMAZON_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
ADS_SCOPE = "advertising::campaign_management"

# 简单的 state 存储（内存，单次使用）
_pending_states: set[str] = set()


def _get_ads_config() -> tuple[str, str]:
    """从配置获取 client_id 和 client_secret。"""
    from src.config import settings
    client_id = settings.AMAZON_ADS_CLIENT_ID
    client_secret = settings.AMAZON_ADS_CLIENT_SECRET
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=500,
            detail="AMAZON_ADS_CLIENT_ID / AMAZON_ADS_CLIENT_SECRET 未配置",
        )
    return client_id, client_secret


# 硬编码回调地址 — 必须与 Amazon Developer Console 的 Allowed Return URLs 精确一致
REDIRECT_URI = "https://siqiangshangwu.com/api/ads-oauth/callback"


def _get_redirect_uri(_request: Request | None = None) -> str:
    """返回固定的回调 URI（已在 Amazon LwA Security Profile 注册）。"""
    return REDIRECT_URI


@router.get("/authorize")
async def ads_oauth_authorize(request: Request):
    """发起 Amazon Ads OAuth 授权。跳转到 Amazon 登录页。"""
    client_id, _ = _get_ads_config()
    redirect_uri = _get_redirect_uri(request)

    state = secrets.token_urlsafe(32)
    _pending_states.add(state)

    params = {
        "client_id": client_id,
        "scope": ADS_SCOPE,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": state,
    }
    auth_url = f"{AMAZON_AUTH_URL}?{urlencode(params)}"
    logger.info("Ads OAuth: 跳转授权 redirect_uri=%s", redirect_uri)
    return RedirectResponse(url=auth_url)


@router.get("/callback", response_class=HTMLResponse)
async def ads_oauth_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    """接收 Amazon 授权回调，用 code 换取 refresh_token。"""
    if error:
        return HTMLResponse(
            content=f"<h1>授权失败</h1><p>Error: {error}</p>",
            status_code=400,
        )

    if not code:
        return HTMLResponse(
            content="<h1>授权失败</h1><p>未收到授权码 (code)</p>",
            status_code=400,
        )

    # 验证 state
    if state not in _pending_states:
        logger.warning("Ads OAuth: state 不匹配 (可能是重复请求)")
        # 不阻断，但记录警告
    else:
        _pending_states.discard(state)

    client_id, client_secret = _get_ads_config()
    redirect_uri = _get_redirect_uri(request)

    # 用 code 换取 token
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                AMAZON_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            token_data = resp.json()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text
        logger.error("Ads OAuth token 请求失败: %s %s", exc.response.status_code, body)
        return HTMLResponse(
            content=f"<h1>Token 换取失败</h1><pre>{body}</pre>",
            status_code=502,
        )
    except Exception as exc:
        logger.error("Ads OAuth token 请求异常: %s", exc)
        return HTMLResponse(
            content=f"<h1>Token 换取异常</h1><pre>{exc}</pre>",
            status_code=500,
        )

    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", "")

    # 用 access_token 获取 profile ID
    profiles_html = ""
    if access_token:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                prof_resp = await client.get(
                    "https://advertising-api.amazon.com/v2/profiles",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Amazon-Advertising-API-ClientId": client_id,
                    },
                )
                if prof_resp.status_code == 200:
                    profiles = prof_resp.json()
                    if profiles:
                        lines = ["<h3>你的 Ads Profile ID（请选择你店铺对应的）：</h3><ul>"]
                        for p in profiles:
                            pid = p.get("profileId", "")
                            name = p.get("accountInfo", {}).get("name", "")
                            mkt = p.get("accountInfo", {}).get("marketplaceStringId", "")
                            lines.append(
                                f"<li><strong>{pid}</strong> — {name} ({mkt})</li>"
                            )
                        lines.append("</ul>")
                        profiles_html = "\n".join(lines)
                    else:
                        profiles_html = "<p>⚠️ 未找到任何 Ads Profile。请确认该账号已开通 Amazon Advertising。</p>"
                else:
                    profiles_html = f"<p>获取 Profile 列表失败: HTTP {prof_resp.status_code}</p>"
        except Exception as exc:
            profiles_html = f"<p>获取 Profile 列表异常: {exc}</p>"

    logger.info("Ads OAuth: 成功获取 token, refresh_token 长度=%d", len(refresh_token))

    # 展示结果页面
    html = f"""<!DOCTYPE html>
<html>
<head><title>Amazon Ads OAuth 成功</title>
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
.token-box {{ background: #f0f0f0; padding: 15px; border-radius: 8px; word-break: break-all; margin: 10px 0; }}
.success {{ color: #16a34a; }}
.warning {{ color: #d97706; }}
</style>
</head>
<body>
<h1 class="success">✅ Amazon Ads OAuth 授权成功！</h1>

<h2>Refresh Token：</h2>
<div class="token-box"><code>{refresh_token}</code></div>
<p>⬆️ 请复制这个值，配置到服务器 .env 的 <code>AMAZON_ADS_REFRESH_TOKEN</code></p>

{profiles_html}

<h3>其他信息：</h3>
<ul>
<li>Access Token 有效期: {expires_in} 秒</li>
<li>Access Token（临时）: <span style="font-size:11px">{access_token[:20]}...</span></li>
</ul>

<p class="warning">⚠️ 此页面仅显示一次。请立即复制 refresh_token！</p>
</body>
</html>"""
    return HTMLResponse(content=html)
