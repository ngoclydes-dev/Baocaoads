import os
import re
import subprocess
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OFFSET_FILE = "telegram_offset.txt"


def load_offset():
    if os.path.exists(OFFSET_FILE):
        with open(OFFSET_FILE, "r") as f:
            content = f.read().strip()
            if content.isdigit():
                return int(content)
    return None


def save_offset(offset):
    with open(OFFSET_FILE, "w") as f:
        f.write(str(offset))


def get_updates(offset):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {"timeout": 0, "allowed_updates": ["message"]}
    if offset:
        params["offset"] = offset
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("result", [])


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def run_bot_with_period(period, custom_date=None):
    """Gọi meta_ads_bot.py với PERIOD tương ứng (tái dùng toàn bộ logic báo cáo có sẵn)"""
    env = os.environ.copy()
    env["PERIOD"] = period
    if custom_date:
        env["CUSTOM_DATE"] = custom_date
    subprocess.run(["python", "meta_ads_bot.py"], env=env, check=True)


def parse_command(text):
    text = text.strip().lower()

    if text in ["/baocao", "/hom_qua", "báo cáo", "báo cáo hôm qua"]:
        return ("daily", None)
    if text in ["/7ngay", "/7_ngay", "7 ngày"]:
        return ("period_7", None)
    if text in ["/14ngay", "/14_ngay", "14 ngày"]:
        return ("period_14", None)
    if text in ["/thang", "trong tháng"]:
        return ("period_month", None)

    # Format YYYY-MM-DD (dấu gạch ngang)
    match = re.match(r"/ngay\s+(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        y, m, d = match.groups()
        return ("custom_date", f"{y}-{m}-{d}")

    # Format DD/MM/YYYY (dấu gạch chéo)
    match = re.match(r"/ngay\s+(\d{2})/(\d{2})/(\d{4})", text)
    if match:
        d, m, y = match.groups()
        return ("custom_date", f"{y}-{m}-{d}")

    # Format DD.MM.YYYY (dấu chấm) ← FIX: thêm mới
    match = re.match(r"/ngay\s+(\d{2})\.(\d{2})\.(\d{4})", text)
    if match:
        d, m, y = match.groups()
        return ("custom_date", f"{y}-{m}-{d}")

    return (None, None)


if __name__ == "__main__":
    offset = load_offset()
    updates = get_updates(offset)

    if not updates:
        print("Không có tin nhắn mới.")
    else:
        for update in updates:
            update_id = update["update_id"]

            # FIX: Save offset NGAY sau mỗi update để tránh xử lý lặp khi lỗi
            save_offset(update_id + 1)

            message = update.get("message")
            if not message:
                continue

            text = message.get("text", "")
            chat_id = str(message.get("chat", {}).get("id", ""))

            if chat_id != str(TELEGRAM_CHAT_ID):
                print(f"Bỏ qua tin nhắn từ chat khác: {chat_id}")
                continue

            period, custom_date = parse_command(text)
            print(f"Nhận lệnh: '{text}' → period={period}, custom_date={custom_date}")

            if period:
                try:
                    run_bot_with_period(period, custom_date)
                except Exception as e:
                    send_telegram(f"⚠️ Lỗi khi xử lý lệnh: {e}")
            elif text.startswith("/"):
                send_telegram(
                    "❓ Lệnh không hợp lệ. Các lệnh hỗ trợ:\n"
                    "/baocao - Báo cáo hôm qua\n"
                    "/7ngay - Báo cáo 7 ngày\n"
                    "/14ngay - Báo cáo 14 ngày\n"
                    "/thang - Báo cáo trong tháng\n"
                    "/ngay YYYY-MM-DD - Báo cáo theo ngày cụ thể"
                )
