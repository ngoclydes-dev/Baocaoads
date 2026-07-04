import os
import requests
import json

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

resp = requests.get(APPS_SCRIPT_URL, timeout=30)
data = resp.json()

print("Keys:", list(data.keys()))
print("DATA rows:", len(data.get("data", [])))
print("LIVECHAT rows:", len(data.get("livechat", [])))
print("CI rows:", len(data.get("ci", [])))

ci = data.get("ci", [])
print("\n=== 10 DONG CI DAU TIEN ===")
for i, row in enumerate(ci[:10]):
    print(f"Dong {i+1}:", json.dumps(row, ensure_ascii=False))

print("\n=== DONG CO CHECKED=TRUE ===")
checked = [r for r in ci if r.get("checked") == True]
print(f"Tong checked: {len(checked)}")
for r in checked[:5]:
    print(json.dumps(r, ensure_ascii=False))
