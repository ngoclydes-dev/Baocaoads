import os
import json
import requests

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
META_API_VERSION = "v21.0"
META_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"

account_id = os.getenv("AD_ACCOUNT_1")
date_check = "2026-06-27"

url = f"{META_BASE_URL}/{account_id}/insights"
params = {
    "fields": "spend,actions,unique_actions",
    "time_range": f'{{"since":"{date_check}","until":"{date_check}"}}',
    "level": "account",
    "access_token": META_ACCESS_TOKEN,
}
resp = requests.get(url, params=params, timeout=30)
data = resp.json().get("data", [])
if data:
    unique = data[0].get("unique_actions", [])
    for u in unique:
        if "messag" in u.get("action_type", ""):
            print(u)
else:
    print(resp.json())
