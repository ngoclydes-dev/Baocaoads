import os
import re
import requests

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
META_API_VERSION = "v21.0"
META_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"

AD_ACCOUNTS = [
    os.getenv("AD_ACCOUNT_1"),
    os.getenv("AD_ACCOUNT_2"),
    os.getenv("AD_ACCOUNT_3"),
    os.getenv("AD_ACCOUNT_4"),
]

ACCOUNT_THRESHOLDS = [53_015_250, 20_000_000, 31_667_350, 0]
THRESHOLD_ALERT_AMOUNT = 1_000_000
BILL_DAYS = [
    int(os.getenv("BILL_DAY_1", 0) or 0),
    int(os.getenv("BILL_DAY_2", 0) or 0),
    int(os.getenv("BILL_DAY_3", 0) or 0),
    int(os.getenv("BILL_DAY_4", 0) or 0),
]


def get_short_name(full_name, fallback=""):
    match = re.search(r"Account\s+(\d+)", full_name or "")
    return f"TK {match.group(1)}" if match else (full_name or fallback)


def get_account_billing(account_id):
    url = f"{META_BASE_URL}/{account_id}"
    params = {"fields": "name,currency,balance", "access_token": META_ACCESS_TOKEN}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    for i, account_id in enumerate(AD_ACCOUNTS, 1):
        if not account_id:
            continue
        threshold = ACCOUNT_THRESHOLDS[i-1] if i-1 < len(ACCOUNT_THRESHOLDS) else 0
        bill_day = BILL_DAYS[i-1] if i-1 < len(BILL_DAYS) else 0

        info = get_account_billing(account_id)
        name = get_short_name(info.get("name", ""), fallback=f"Tài khoản {i}")
        balance = float(info.get("balance", 0))

        print(f"--- {name} ---")
        print(f"  Ngưỡng: {threshold:,.0f} | Balance: {balance:,.0f} | Bill day: {bill_day}")

        if threshold > 0:
            remaining = threshold - balance
            if remaining <= 0:
                print(f"  → 🔴 {name} ĐÃ ĐẠT/VƯỢT ngưỡng thanh toán! Vui lòng kiểm tra thẻ.")
            elif remaining <= THRESHOLD_ALERT_AMOUNT:
                print(f"  → ⚠️ {name} còn {remaining:,.0f}đ đến ngưỡng thanh toán.")
            else:
                print(f"  → ✅ An toàn, còn {remaining:,.0f}đ mới tới ngưỡng.")
        print()
