import os
import requests
import json

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

resp = requests.get(APPS_SCRIPT_URL, timeout=30)
data = resp.json()

print("=== KEYS TRONG RESPONSE ===")
print(list(data.keys()))

print("\n=== DATA rows:", len(data.get("data", [])))
print("=== LIVECHAT rows:", len(data.get("livechat", [])))

livechat = data.get("livechat", [])
if livechat:
    print("\n=== MAU LIVECHAT DONG DAU ===")
    print(json.dumps(livechat[0], indent=2, ensure_ascii=False))
else:
    print("\n=== LIVECHAT RONG - Apps Script chua tra ve livechat ===")
