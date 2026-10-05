import os
import requests
import json

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

resp = requests.get(APPS_SCRIPT_URL, timeout=60)
data = resp.json()

livechat = data.get("livechat", [])
print(f"Livechat sheet: {data.get('livechatSheetName')}")
print(f"Livechat rows: {len(livechat)}")

if livechat:
    print("\nKeys dong dau:")
    print(list(livechat[0].keys()))
    print("\nMau dong dau:")
    print(json.dumps(livechat[0], ensure_ascii=False, indent=2))
