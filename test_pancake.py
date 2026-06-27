import os
import requests
from datetime import datetime, timedelta, timezone

PANCAKE_TOKEN = os.getenv("PANCAKE_TOKEN")
SPAM_TAG_ID = 17
VN_TZ = timezone(timedelta(hours=7))

PANCAKE_PAGES = [
    {"id": "103905658090177", "name": "Love + Rosa Skin Center"},
    {"id": "108481465282735", "name": "Love + Rosa Quang Trung Gò Vấp"},
    {"id": "105124961775914", "name": "Love + Rosa Chăm Sóc Da Mụn"},
    {"id": "101059842189274", "name": "Love + Rosa Kỳ Đồng Quận 3"},
]

def get_pancake_conversations(page_id: str, tags: str = "[]", except_tags: str = "[]", limit: int = 100) -> list:
    url = f"https://pancake.vn/api/v1/pages/{page_id}/conversations"
    all_conversations = []
    page_number = 1

    while True:
        params = {
            "tags": tags,
            "except_tags": except_tags,
            "mode": "NONE",
            "access_token": PANCAKE_TOKEN,
            "limit": limit,
            "page_number": page_number,
        }
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        conversations = data.get("conversations", [])

        if not conversations:
            break

        all_conversations.extend(conversations)

        if len(conversations) < limit:
            break
        page_number += 1

        if page_number > 20:
            break

    return all_conversations


def get_pancake_spam_and_phones(page_id: str, date_str: str) -> dict:
    spam_conversations = get_pancake_conversations(page_id, tags=f"[{SPAM_TAG_ID}]")
    spam_count = sum(
        1 for conv in spam_conversations
        if conv.get("inserted_at", "")[:10] == date_str
    )

    all_conversations = get_pancake_conversations(page_id, tags="[]", except_tags="[]")

    seen_phones = set()
    phones = []

    for conv in all_conversations:
        inserted = conv.get("inserted_at", "")[:10]
        if inserted != date_str:
            continue

        for phone_info in conv.get("recent_phone_numbers", []):
            phone = phone_info.get("phone_number", "")
            if phone and phone not in seen_phones:
                seen_phones.add(phone)
                phones.append({
                    "phone": phone,
                    "name": conv.get("customers", [{}])[0].get("name", ""),
                })

    return {"spam": spam_count, "phones": phones}


# ... các hàm get_pancake_conversations, get_pancake_spam_and_phones giữ nguyên ở trên ...


def get_page_tags(page_id: str):
    url = f"https://pancake.vn/api/v1/pages/{page_id}/tags"
    params = {"access_token": PANCAKE_TOKEN}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    import json

    # 1. Kiểm tra danh sách tag thật của page
    print("=== DANH SÁCH TAG ===")
    try:
        tags_data = get_page_tags(PANCAKE_PAGES[0]["id"])
        print(json.dumps(tags_data, indent=2, ensure_ascii=False))
    except Exception as e:
        print("Lỗi lấy tags:", e)

    # 2. Kiểm tra cấu trúc response để tìm cơ chế phân trang
    print("\n=== CẤU TRÚC RESPONSE CONVERSATIONS ===")
    url = f"https://pancake.vn/api/v1/pages/{PANCAKE_PAGES[0]['id']}/conversations"
    params = {
        "access_token": PANCAKE_TOKEN,
        "limit": 100,
    }
    resp = requests.get(url, params=params, timeout=30)
    data = resp.json()
    print("Các key ở cấp cao nhất:", list(data.keys()))
