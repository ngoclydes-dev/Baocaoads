import os
import requests
import json

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

resp = requests.get(APPS_SCRIPT_URL, timeout=30)
data = resp.json()

print("CI sheet name đang tìm:", data.get("ciSheetName"))
print("CI rows:", len(data.get("ci", [])))
print("Debug rows:", len(data.get("debug", [])))
print("\nRaw response (500 ky tu dau):")
print(resp.text[:500])
