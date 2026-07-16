import os
import requests
from datetime import datetime, timedelta, timezone

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
META_API_VERSION = "v21.0"
META_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"
VN_TZ = timezone(timedelta(hours=7))

AD_ACCOUNTS = [
    os.getenv("AD_ACCOUNT_1"),
    os.getenv("AD_ACCOUNT_2"),
    os.getenv("AD_ACCOUNT_3"),
    os.getenv("AD_ACCOUNT_4"),
]

ACCOUNT_THRESHOLDS = [
    53_015_250,
    20_000_000,
    31_667_350,
    0,
]

THRESHOLD_ALERT_AMOUNT = 3_000_000

BILL_DAYS = [
    int(os.getenv("BILL_DAY_1", 0) or 0),
    int(os.getenv("BILL_DAY_2", 0) or 0),
    int(os.getenv("BILL_DAY_3", 0) or 0),
    int(os.getenv("BILL_DAY_4", 0) or 0),
]


def get_short_name(full_name: str, fallback: str = "") -> str:
    import re
    match = re.search(r"Account\s+(\d+)", full_name or "")
    if match:
        return f"TK {match.group(1)}"
    return full_name or fallback


def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=30)
    resp.raise_for_status()


def get_account_billing(account_id: str) -> dict:
    url = f"{META_BASE_URL}/{account_id}"
    params = {"fields": "name,currency,balance", "access_token": META_ACCESS_TOKEN}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    now = datetime.now(VN_TZ)
    alerts = []

    for i, account_id in enumerate(AD_ACCOUNTS, 1):
        if not account_id:
            continue
        try:
            info = get_account_billing(account_id)
            name = get_short_name(info.get("name", ""), fallback=f"Tài khoản {i}")
            balance = float(info.get("balance", 0))
            threshold = ACCOUNT_THRESHOLDS[i-1] if i-1 < len(ACCOUNT_THRESHOLDS) else 0

            if threshold > 0:
                remaining = threshold - balance
                if remaining <= 0:
                    alerts.append(f"🔴 {name} ĐÃ ĐẠT/VƯỢT ngưỡng! Vui lòng kiểm tra thẻ.")
                elif remaining <= THRESHOLD_ALERT_AMOUNT:
                    alerts.append(f"⚠️ {name} còn {remaining:,.0f}đ đến ngưỡng thanh toán.")

            bill_day = BILL_DAYS[i-1] if i-1 < len(BILL_DAYS) else 0
            if bill_day > 0:
                tomorrow = now + timedelta(days=1)
                if tomorrow.day == bill_day:
                    alerts.append(f"📅 {name} còn 1 ngày đến ngày lập hóa đơn, vui lòng nạp tiền/kiểm tra thẻ.")

        except Exception as e:
            print(f"❌ Lỗi TK {i}: {e}")

    if alerts:
        msg = f"🚨 CẢNH BÁO THANH TOÁN ({now.strftime('%H:%M %d/%m')})\n"
        msg += "-" * 32 + "\n"
        msg += "\n".join(alerts)
        send_telegram(msg)
        print("✅ Đã gửi cảnh báo!")
    else:
        print("✅ Tất cả tài khoản an toàn.")
