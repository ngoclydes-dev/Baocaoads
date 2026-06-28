import os
import requests

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
META_API_VERSION = "v21.0"
META_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"

for env_name in ["AD_ACCOUNT_1", "AD_ACCOUNT_2", "AD_ACCOUNT_3", "AD_ACCOUNT_4"]:
    account_id = os.getenv(env_name)
    if not account_id:
        print(env_name, "→ KHÔNG có giá trị (secret chưa set hoặc rỗng)")
        continue

    url = f"{META_BASE_URL}/{account_id}"
    params = {
        "fields": "name,account_status,disable_reason,balance",
        "access_token": META_ACCESS_TOKEN,
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        print(env_name, "→", resp.json())
    except Exception as e:
        print(env_name, "→ LỖI:", e)
