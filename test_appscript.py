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

count = 0
for row in ci:
    ngay_raw = str(row.get("ngay", "") or "").strip()
    try:
        from datetime import datetime as dt
        vn_date = dt.strptime(ngay_raw, "%d/%m/%Y").strftime("%Y-%m-%d")
    except:
        vn_date = ""
    if vn_date == yesterday and row.get("checked") is True:
        count += 1
        print(f"Tim thay: {row.get('ten')} | {ngay_raw} | checked=True")

print(f"\nTong khach den hom qua: {count}")
