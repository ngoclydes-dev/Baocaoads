import os
import requests
import json

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

resp = requests.get(APPS_SCRIPT_URL, timeout=30)
data = resp.json()

ci = data.get("ci", [])

print("=== TAT CA DONG NGAY 06/07 ===")
count = 0
for r in ci:
    if r.get("ngay") == "06/07/2026":
        print(json.dumps(r, ensure_ascii=False))
        if r.get("checked") is True:
            count += 1

print(f"\nTong checked=True ngay 06/07: {count}")
print(f"\nThuc te trong sheet la bao nhieu khach den ngay 06/07?")
