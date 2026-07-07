import os
import requests
from datetime import datetime, timedelta, timezone

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

resp = requests.get(APPS_SCRIPT_URL, timeout=30)
data = resp.json()

ci = data.get("ci", [])
print(f"Tong CI rows: {len(ci)}")

# In 10 dong cuoi cung
print("\n=== 10 DONG CUOI ===")
for row in ci[-10:]:
    print(f"ngay='{row.get('ngay')}' | ten='{row.get('ten')}' | checked={row.get('checked')}")
