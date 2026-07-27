import os
import requests
from datetime import datetime, timedelta, timezone

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")
VN_TZ = timezone(timedelta(hours=7))

resp = requests.get(APPS_SCRIPT_URL, timeout=30)
data = resp.json()

ci = data.get("ci", [])
print(f"Tong CI rows: {len(ci)}")

yesterday = (datetime.now(VN_TZ) - timedelta(days=1)).strftime("%Y-%m-%d")
print(f"Hom qua: {yesterday}")

# In tat ca ngay co trong CI
from collections import Counter
dates = Counter(r.get("ngay") for r in ci)
print("\n=== PHAN BO NGAY ===")
for d, cnt in sorted(dates.items()):
    print(f"  {d}: {cnt} dong")

# Dem checked=True hom qua
count = sum(1 for r in ci
            if r.get("checked") is True
            and r.get("ngay", "") != ""
            and datetime.strptime(r.get("ngay"), "%d/%m/%Y").strftime("%Y-%m-%d") == yesterday)
print(f"\nKhach den hom qua ({yesterday}): {count}")
