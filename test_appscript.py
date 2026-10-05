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
    
    # Tim dong co PH2L
    for row in livechat[:20]:
        for key, val in row.items():
            if str(val).strip() == "PH2L":
                print(f"\nTim thay PH2L: key='{key}' | NGAY='{row.get('NGÀY', '')}'")
                break
