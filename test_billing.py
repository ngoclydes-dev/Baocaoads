import os
import requests

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
META_API_VERSION = "v21.0"
META_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"

account_id = os.getenv("AD_ACCOUNT_1")
url = f"{META_BASE_URL}/{account_id}"
params = {
    "fields": "name,currency,spend_cap,amount_spent,balance,funding_source_details",
    "access_token": META_ACCESS_TOKEN,
}
resp = requests.get(url, params=params, timeout=30)
print(resp.json())
