import os
import requests

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

resp = requests.get(APPS_SCRIPT_URL, timeout=30)
data = resp.json()

ci = data.get("ci", [])
print(f"CI rows: {len(ci)}")
print(f"CI sheet: {data.get('ciSheetName')}")

checked = [r for r in ci if r.get("checked") is True]
print(f"Checked=True: {len(checked)}")

if ci:
    print("\n5 dong dau:")
    import json
    for r in ci[:5]:
        print(json.dumps(r, ensure_ascii=False))
