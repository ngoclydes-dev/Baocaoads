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


if __name__ == "__main__":
    yesterday = (datetime.now(VN_TZ) - timedelta(days=1)).strftime("%Y-%m-%d")

    for page in PANCAKE_PAGES[:2]:  # chỉ test 2 page đầu cho nhanh
        print(f"\n=== {page['name']} ===")

        spam_convs = get_pancake_conversations(page["id"], tags=f"[{SPAM_TAG_ID}]")
        print("Tổng conversation trả về (tag SPAM):", len(spam_convs))

        ids = [c.get("id") for c in spam_convs]
        print("Số ID trùng lặp:", len(ids) - len(set(ids)))

        if spam_convs:
            sample = spam_convs[0]
            print("Mẫu conversation - tags field:", sample.get("tags"))
            print("Mẫu conversation - inserted_at:", sample.get("inserted_at"))
