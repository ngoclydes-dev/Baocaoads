import os
import requests
from datetime import datetime, timezone, timedelta

PANCAKE_TOKEN = os.getenv("PANCAKE_TOKEN")
VN_TZ = timezone(timedelta(hours=7))

page_id = "103905658090177"  # Love + Rosa Skin Center
date_check = "2026-06-29"  # đổi thành ngày bạn đang đối chiếu

url = f"https://pancake.vn/api/v1/pages/{page_id}/conversations"
params = {"access_token": PANCAKE_TOKEN, "limit": 500}
resp = requests.get(url, params=params, timeout=30)
conversations = resp.json().get("conversations", [])

print(f"Tổng conversation lấy được: {len(conversations)}\n")

count_conv = 0
count_phone = 0

for conv in conversations:
    inserted = conv.get("inserted_at", "")[:10]
    if inserted != date_check:
        continue

    phones = conv.get("recent_phone_numbers", [])
    if not phones:
        continue

    count_conv += 1
    count_phone += len(phones)

    name = conv.get("customers", [{}])[0].get("name", "")
    print(f"Conversation: {name} | inserted_at: {conv.get('inserted_at')}")
    for p in phones:
        print(f"  → SĐT: {p.get('phone_number')}")
    print()

print(f"=== Tổng số CUỘC HỘI THOẠI có SĐT: {count_conv} ===")
print(f"=== Tổng số SĐT (đếm theo entries): {count_phone} ===")
