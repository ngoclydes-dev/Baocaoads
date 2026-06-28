import os
import requests
from datetime import datetime, timedelta, timezone

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
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
    53_015_250,   # Tài khoản 1650
    20_000_000,   # Tài khoản 3742
    31_667_350,   # Tài khoản 5186
    0,            # Tài khoản 4 - chưa có ngưỡng
]


def get_account_billing(account_id: str) -> dict:
    url = f"{META_BASE_URL}/{account_id}"
    params = {
        "fields": "name,currency,balance",
        "access_token": META_ACCESS_TOKEN,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_insights(account_id: str, date_start: str, date_stop: str):
    url = f"{META_BASE_URL}/{account_id}/insights"
    params = {
        "fields": "spend",
        "time_range": f'{{"since":"{date_start}","until":"{date_stop}"}}',
        "level": "account",
        "access_token": META_ACCESS_TOKEN,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return data[0] if data else {}


def get_dates(days: int):
    now = datetime.now(VN_TZ)
    date_stop = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    date_start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    return date_start, date_stop


if __name__ == "__main__":
    yesterday_start, yesterday_stop = get_dates(1)
    print(f"Khoảng ngày kiểm tra chi tiêu: {yesterday_start} → {yesterday_stop}\n")

    for i, account_id in enumerate(AD_ACCOUNTS, 1):
        if not account_id:
            print(f"--- Tài khoản {i}: KHÔNG có giá trị, bỏ qua ---\n")
            continue

        threshold = ACCOUNT_THRESHOLDS[i-1] if i-1 < len(ACCOUNT_THRESHOLDS) else 0

        try:
            info = get_account_billing(account_id)
            name = info.get("name", f"Tài khoản {i}")
            currency = info.get("currency", "VND")
            balance = float(info.get("balance", 0))

            insight = get_insights(account_id, yesterday_start, yesterday_stop)
            yesterday_spend = float(insight.get("spend", 0))

            projected_balance = balance + yesterday_spend

            print(f"--- {name} ---")
            print(f"  Ngưỡng cài đặt:      {threshold:,.0f} {currency}")
            print(f"  Balance hiện tại:    {balance:,.0f} {currency}")
            print(f"  Chi tiêu hôm qua:    {yesterday_spend:,.0f} {currency}")
            print(f"  Dự kiến (balance+chi tiêu hôm qua): {projected_balance:,.0f} {currency}")

            if threshold <= 0:
                print("  → Chưa cài ngưỡng, không kiểm tra.")
            elif balance >= threshold:
                print("  → 🔴 ĐÃ ĐẠT/VƯỢT NGƯỠNG (sẽ cảnh báo mức ĐỎ)")
            elif projected_balance >= threshold:
                remaining = threshold - balance
                print(f"  → ⚠️ SẮP ĐẠT NGƯỚNG (còn {remaining:,.0f} {currency}) (sẽ cảnh báo mức VÀNG)")
            else:
                remaining = threshold - balance
                print(f"  → ✅ An toàn (còn {remaining:,.0f} {currency} mới tới ngưỡng)")

            print()
        except Exception as e:
            print(f"--- Tài khoản {i}: LỖI - {e} ---\n")
