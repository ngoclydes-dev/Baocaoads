import os
import requests

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

resp = requests.get(APPS_SCRIPT_URL, timeout=30)
data = resp.json()

print("Livechat sheet:", data.get("livechatSheetName"))
print("Livechat rows:", len(data.get("livechat", [])))

livechat = data.get("livechat", [])
if livechat:
    print("\nMau dong dau:")
    import json
    print(json.dumps(livechat[0], ensure_ascii=False, indent=2))
else:
    print("LIVECHAT RONG")
