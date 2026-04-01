"""临时调试脚本：测试飞书 API 发送消息，打印详细响应。"""
import os
import sys
import json
import requests

sys.path.insert(0, '/app')

from src.config import settings
from src.feishu.bot_handler import FeishuBot

bot = FeishuBot(settings.FEISHU_APP_ID, settings.FEISHU_APP_SECRET)

# 1. 获取 token
token = bot.get_tenant_access_token()
print(f"[1] Token OK: {token[:20]}...")

# 2. 打印 .env 里的关键配置（隐藏敏感部分）
print(f"[2] APP_ID: {settings.FEISHU_APP_ID}")
chat_id = getattr(settings, 'FEISHU_CHAT_ID', '') or getattr(settings, 'FEISHU_TEST_CHAT_ID', '')
print(f"[2] CHAT_ID from settings: '{chat_id}'")

# 3. 用 text 消息测试（最简单）
url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
payload = {
    "receive_id": chat_id,
    "msg_type": "text",
    "content": json.dumps({"text": "🧪 测试消息，可忽略"}, ensure_ascii=False),
}
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json; charset=utf-8",
}
print(f"[3] 发送到 chat_id: '{chat_id}'")
resp = requests.post(url, headers=headers, json=payload, timeout=10)
print(f"[3] HTTP Status: {resp.status_code}")
print(f"[3] Response Body: {resp.text}")

# 4. 如果 chat_id 为空，用 open_id 方式再试
if not chat_id:
    print("[4] chat_id 为空！尝试 open_id 方式...")
    open_id = getattr(settings, 'FEISHU_OPEN_ID', '')
    print(f"[4] OPEN_ID: '{open_id}'")
    if open_id:
        url2 = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
        payload2 = {
            "receive_id": open_id,
            "msg_type": "text",
            "content": json.dumps({"text": "🧪 open_id 测试消息"}, ensure_ascii=False),
        }
        resp2 = requests.post(url2, headers=headers, json=payload2, timeout=10)
        print(f"[4] open_id 方式 HTTP Status: {resp2.status_code}")
        print(f"[4] open_id 方式 Response: {resp2.text}")
