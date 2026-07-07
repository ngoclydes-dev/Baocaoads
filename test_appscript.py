import os
import requests
import json

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

resp = requests.get(APPS_SCRIPT_URL, timeout=30)
data = resp.json()

ci = data.get("ci", [])
print(f"Tong CI rows: {len(ci)}")

# Tim dong co checked=True
checked_rows = [r for r in ci if r.get("checked") is True]
print(f"So dong checked=True: {len(checked_rows)}")

# In tat ca dong ngay 06/07
print("\n=== DONG NGAY 06/07 ===")
for r in ci:
    if r.get("ngay") == "06/07/2026":
        print(json.dumps(r, ensure_ascii=False))
