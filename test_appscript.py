import os
import requests
import json
from datetime import datetime, timedelta, timezone

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")
VN_TZ = timezone(timedelta(hours=7))

resp = requests.get(APPS_SCRIPT_URL, timeout=30)
data = resp.json()

ci = data.get("ci", [])
print(f"Tổng CI rows: {len(ci)}")
print()

# In 5 dòng đầu để xem format ngày
print("=== 5 DONG DAU ===")
for i, row in enumerate(ci[:5]):
    print(f"Dong {i+1}: ngay='{row.get('ngay')}' | checked={row.get('checked')}")

print()

# Thử parse ngày của từng dòng
print("=== KIEM TRA PARSE NGAY ===")
yesterday = (datetime.now(VN_TZ) - timedelta(days=1)).strftime("%Y-%m-%d")
print(f"Hôm qua: {yesterday}")

count = 0
for row in ci:
    ngay_raw = str(row.get("ngay", "") or "").strip()
    if not ngay_raw:
        continue
    try:
        dt = datetime.strptime(ngay_raw, "%d/%m/%Y")
        vn_date = dt.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Parse lỗi: '{ngay_raw}' → {e}")
        continue
    if vn_date == yesterday and row.get("checked") is True:
        count += 1
        print(f"Tìm thấy: ngay='{ngay_raw}' → '{vn_date}' | checked=True")

print(f"\nTổng khách đến hôm qua ({yesterday}): {count}")
