import os
import requests
import json

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

resp = requests.get(APPS_SCRIPT_URL, timeout=30)
data = resp.json()

print("CI rows:", len(data.get("ci", [])))
print("\n=== DEBUG 10 DONG DAU RAW ===")
for row in data.get("debug", []):
    print(json.dumps(row, ensure_ascii=False))
