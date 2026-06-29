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
print("Status code:", resp.status_code)

result = resp.json()
data = result.get("data", [])

if not data:
    print("KHÔNG có data. Raw response:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
else:
    print("=== unique_actions (toàn bộ) ===")
    unique = data[0].get("unique_actions")
    if unique is None:
        print("Field 'unique_actions' KHÔNG tồn tại trong response.")
    elif len(unique) == 0:
        print("Field 'unique_actions' tồn tại nhưng RỖNG ([]).")
    else:
        print(json.dumps(unique, indent=2, ensure_ascii=False))
