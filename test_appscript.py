import os
import requests
import json

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

resp = requests.get(APPS_SCRIPT_URL, timeout=30)
data = resp.json()

print("Keys:", list(data.keys()))
print("CI rows:", len(data.get("ci", [])))
print("CI sheet name:", data.get("ciSheetName"))

ci = data.get("ci", [])
if ci:
    print("\n5 dong dau:")
    for i, row in enumerate(ci[:5]):
        print(f"  {i}: {json.dumps(row, ensure_ascii=False)}")
else:
    print("\nCI RONG - kiem tra Apps Script")
    if "error" in data:
        print("Loi:", data["error"])
