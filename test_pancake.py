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
    conversations = get_pancake_conversations(page_id, limit=200)

    spam_count = 0
    seen_phones = set()
    phones = []

    for conv in conversations:
        if conv.get("inserted_at", "")[:10] != date_str:
            continue

        # Lọc SPAM thủ công bằng cách kiểm tra tag ID có trong list không
        if SPAM_TAG_ID in conv.get("tags", []):
            spam_count += 1

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
    page_id = "108481465282735"  # Quang Trung Gò Vấp - đúng page trong network request bạn chụp
    url = f"https://pancake.vn/api/v1/pages/{page_id}/conversations"

    # Gọi giống y hệt request thật trên browser
    params = {
        "unread_first": "true",
        "mode": "NONE",
        "tags": "[17]",
        "except_tags": "[]",
        "access_token": PANCAKE_TOKEN,
        "limit": 50,
    }
    resp = requests.get(url, params=params, timeout=30)
    print("Status code:", resp.status_code)
    print("Request URL thực tế:", resp.url)

    data = resp.json()
    convs = data.get("conversations", [])
    print("Tổng conversation trả về:", len(convs))

    # Kiểm tra từng conversation có thật chứa tag 17 không
    has_17 = [c.get("id") for c in convs if 17 in c.get("tags", [])]
    no_17 = [c.get("id") for c in convs if 17 not in c.get("tags", [])]
    print("Số conversation CÓ tag 17:", len(has_17))
    print("Số conversation KHÔNG có tag 17:", len(no_17))

    if no_17:
        # In thử 1 mẫu không có tag 17 để xem nó thật ra có tag gì
        sample = next(c for c in convs if 17 not in c.get("tags", []))
        print("Mẫu KHÔNG có tag 17 - tags thật:", sample.get("tags"))
