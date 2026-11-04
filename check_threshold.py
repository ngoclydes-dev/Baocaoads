import os
import re
import requests
from datetime import datetime, timedelta, timezone

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
META_API_VERSION = "v21.0"
META_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"
VN_TZ = timezone(timedelta(hours=7))

def normalize_account_id(account_id):
    """Meta Graph API cần dạng act_<số>. Tự thêm tiền tố nếu secret chỉ có số."""
    if not account_id:
        return account_id
    account_id = account_id.strip()
    return account_id if account_id.startswith("act_") else f"act_{account_id}"


AD_ACCOUNTS = [
    normalize_account_id(os.getenv("AD_ACCOUNT_1")),
    normalize_account_id(os.getenv("AD_ACCOUNT_2")),
    normalize_account_id(os.getenv("AD_ACCOUNT_3")),
    normalize_account_id(os.getenv("AD_ACCOUNT_4")),
    normalize_account_id(os.getenv("AD_ACCOUNT_5")),  # TK 4985
]

# Vị trí tài khoản (từ 1) không cảnh báo ngưỡng thanh toán
THRESHOLD_SKIP = {2, 4}  # 2 = TK 3742, 4 = TK 8132

ACCOUNT_THRESHOLDS = [
    53_015_250,
    20_000_000,
    31_667_350,
    13_678_063,
    0,  # TK 4985: chưa có ngưỡng thanh toán, 0 = không cảnh báo ngưỡng
]

THRESHOLD_ALERT_AMOUNT = 3_000_000

# Mức cảnh báo riêng theo vị trí tài khoản (từ 1): báo khi còn <= số này đến ngưỡng
THRESHOLD_ALERT_OVERRIDES = {
    1: 5_000_000,  # TK 1650
    3: 5_000_000,  # TK 5186
}

BILL_DAYS = [
    int(os.getenv("BILL_DAY_1", 0) or 0),
    int(os.getenv("BILL_DAY_2", 0) or 0),
    int(os.getenv("BILL_DAY_3", 0) or 0),
    int(os.getenv("BILL_DAY_4", 0) or 0),
    int(os.getenv("BILL_DAY_5", 0) or 0),
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
        if not account_id or i in THRESHOLD_SKIP:
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
                elif remaining <= THRESHOLD_ALERT_OVERRIDES.get(i, THRESHOLD_ALERT_AMOUNT):
                    alerts.append(f"⚠️ {name} còn {remaining:,.0f}đ đến ngưỡng thanh toán.")

            bill_day = BILL_DAYS[i-1] if i-1 < len(BILL_DAYS) else 0
            if bill_day > 0:
                tomorrow = now + timedelta(days=1)
                if tomorrow.day == bill_day:
                    alerts.append(f"📅 {name} còn 1 ngày đến ngày lập hóa đơn, vui lòng nạp tiền/kiểm tra thẻ.")

        except Exception as e:
            err_msg = re.sub(r"access_token=[^&\s]+", "access_token=***", str(e))
            print(f"❌ Lỗi TK {i}: {err_msg}")

    if alerts:
        msg = f"🚨 CẢNH BÁO THANH TOÁN ({now.strftime('%H:%M %d/%m')})\n"
        msg += "-" * 32 + "\n"
        msg += "\n".join(alerts)
        send_telegram(msg)
        print("✅ Đã gửi cảnh báo!")
    else:
        print("✅ Tất cả tài khoản an toàn.")
