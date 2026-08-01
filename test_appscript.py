import os
import requests

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

resp = requests.get(APPS_SCRIPT_URL, timeout=30)
data = resp.json()

print("DATA sheet:", data.get("dataSheetName"), "| rows:", len(data.get("data", [])))
print("LIVECHAT sheet:", data.get("livechatSheetName"), "| rows:", len(data.get("livechat", [])))
print("CI sheet:", data.get("ciSheetName"), "| rows:", len(data.get("ci", [])))
