import os
import requests
from datetime import datetime, timedelta, timezone

PANCAKE_TOKEN = os.getenv("PANCAKE_TOKEN")
VN_TZ = timezone(timedelta(hours=7))

yesterday = (datetime.now(VN_TZ) - timedelta(days=1)).strftime("%Y-%m-%d")
print(f"Hom qua: {yesterday}")

page_id = "1118351541362302"
url = f"https://pancake.vn/api/v1/pages/{page_id}/conversations"
params = {"access_token": PANCAKE_TOKEN, "limit": 500}
resp = requests.get(url, params=params, timeout=30)
data = resp.json()

conversations = data.get("conversations", [])
print(f"Tong conversations: {len(conversations)}")

count = 0
for conv in conversations:
    inserted = conv.get("inserted_at", "")[:10]
    if inserted == yesterday:
        phones = conv.get("recent_phone_numbers", [])
        if phones:
            count += 1
            print(f"  Co SDT: {phones[0].get('phone_number')} | inserted: {inserted}")

print(f"\nTong SDT moi hom qua: {count}")
