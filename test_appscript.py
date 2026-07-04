import os
import requests

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

resp = requests.get(APPS_SCRIPT_URL, timeout=30)
data = resp.json()
ci = data.get("ci", [])

print("=== TAT CA DONG NGAY 03/07 ===")
for i, row in enumerate(ci):
    if row.get("ngay") == "03/07/2026":
        print(f"Index {i}: ten='{row.get('ten')}' | checked={row.get('checked')}")

print(f"\nTong: {sum(1 for r in ci if r.get('ngay') == '03/07/2026')}")
