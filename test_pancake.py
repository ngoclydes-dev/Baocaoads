def get_pancake_conversations(page_id: str, tags: str = "[]", except_tags: str = "[]", limit: int = 100) -> list:
    """Lấy toàn bộ conversation theo filter, có phân trang"""
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

        # Nếu trả về ít hơn limit => hết trang
        if len(conversations) < limit:
            break
        page_number += 1

        # Chặn an toàn tránh loop vô hạn
        if page_number > 20:
            break

    return all_conversations


def get_pancake_spam_and_phones(page_id: str, date_str: str) -> dict:
    """
    Đếm SPAM mới và SĐT mới trong ngày date_str (YYYY-MM-DD).
    - SPAM: conversation có tag SPAM, tạo trong ngày date_str
    - SĐT mới: lấy từ TẤT CẢ conversation (không lọc theo tag SPAM),
      tạo trong ngày date_str, có số điện thoại
    """
    # --- Đếm SPAM: chỉ lấy conversation có tag SPAM ---
    spam_conversations = get_pancake_conversations(page_id, tags=f"[{SPAM_TAG_ID}]")
    spam_count = sum(
        1 for conv in spam_conversations
        if conv.get("inserted_at", "")[:10] == date_str
    )

    # --- Đếm SĐT mới: lấy TẤT CẢ conversation, KHÔNG lọc theo SPAM ---
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
