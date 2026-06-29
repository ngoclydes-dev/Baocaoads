import os
import json
import requests

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
META_API_VERSION = "v21.0"
META_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"

account_id = os.getenv("AD_ACCOUNT_1")
date_check = "2026-06-27"  # đổi thành ngày bạn muốn so sánh với Ads Manager

url = f"{META_BASE_URL}/{account_id}/insights"
params = {
    "fields": "spend,actions",
    "time_range": f'{{"since":"{date_check}","until":"{date_check}"}}',
    "level": "account",
    "action_attribution_windows": "1d_click,7d_click,1d_view,28d_click",
    "access_token": META_ACCESS_TOKEN,
}
resp = requests.get(url, params=params, timeout=30)
data = resp.json().get("data", [])
if data:
    print(json.dumps(data[0], indent=2, ensure_ascii=False))
else:
    print("Không có data cho ngày này, raw response:")
    print(resp.json())
