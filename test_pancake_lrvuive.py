import os
import requests
from datetime import datetime, timedelta, timezone

PANCAKE_TOKEN = os.getenv("PANCAKE_TOKEN")
VN_TZ = timezone(timedelta(hours=7))
yesterday = (datetime.now(VN_TZ) - timedelta(days=1)).strftime("%Y-%m-%d")

page_id = "103905658090177"  # Skin Center
url = f"https://pancake.vn/api/v1/pages/{page_id}/conversations"
params = {"access_token": PANCAKE_TOKEN, "limit": 10}
resp = requests.get(url, params=params, timeout=30)

print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:300]}")
