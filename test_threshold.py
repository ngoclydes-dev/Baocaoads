import os
import requests
from datetime import datetime, timedelta, timezone

VN_TZ = timezone(timedelta(hours=7))
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
META_API_VERSION = "v21.0"
META_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"

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

THRESHOLD_ALERT_AMOUNT = 1_000_000


def get_account_billing(account_id):
    url = f"{META_BASE_URL}/{account_id}"
    params = {
        "fields": "name,currency,balance",
        "access_token": META_ACCESS_TOKEN,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    now = datetime.now(VN_TZ)
    print(f"=== KIỂM TRA CẢNH BÁO NGƯỠNG THANH TOÁN ===")
    print(f"Thời gian: {now.strftime('%d/%m/%Y %H:%M')}")
    print(f"Ngưỡng cảnh báo: còn ≤ {THRESHOLD_ALERT_AMOUNT:,.0f}đ\n")

    alerts = []

    for i, account_id in enumerate(AD_ACCOUNTS, 1):
        if not account_id:
            print(f"TK {i}: ⚪ Chưa set AD_ACCOUNT_{i}, bỏ qua\n")
            continue

        threshold = ACCOUNT_THRESHOLDS[i-1] if i-1 < len(ACCOUNT_THRESHOLDS) else 0

        try:
            info = get_account_billing(account_id)
            name = info.get("name", f"Tài khoản {i}")
            currency = info.get("currency", "VND")
            balance = float(info.get("balance", 0))

            print(f"--- {name} ---")
            print(f"  Balance hiện tại : {balance:,.0f} {currency}")
            print(f"  Ngưỡng thanh toán: {threshold:,.0f} {currency}")

            if threshold == 0:
                print(f"  → ⚪ Chưa set ngưỡng (ACCOUNT_THRESHOLDS[{i-1}] = 0), bỏ qua")
            else:
                remaining = threshold - balance
                print(f"  Còn lại đến ngưỡng: {remaining:,.0f} {currency}")

                if remaining <= 0:
                    msg = f"🔴 TK {i} ĐÃ ĐẠT/VƯỢT ngưỡng thanh toán! Vui lòng kiểm tra thẻ."
                    alerts.append(msg)
                    print(f"  → 🔴 ĐÃ ĐẠT/VƯỢT NGƯỠNG → SẼ CÓ CẢNH BÁO ĐỎ")
                elif remaining <= THRESHOLD_ALERT_AMOUNT:
                    msg = f"⚠️ TK {i} còn {remaining:,.0f}đ đến ngưỡng thanh toán."
                    alerts.append(msg)
                    print(f"  → ⚠️ SẮP ĐẠT NGƯỠNG (còn {remaining:,.0f}đ ≤ {THRESHOLD_ALERT_AMOUNT:,.0f}đ) → SẼ CÓ CẢNH BÁO")
                else:
                    print(f"  → ✅ An toàn (còn {remaining:,.0f}đ mới tới ngưỡng, > {THRESHOLD_ALERT_AMOUNT:,.0f}đ)")
            print()

        except Exception as e:
            print(f"  → ❌ Lỗi gọi API: {e}\n")

    print("=" * 40)
    if alerts:
        print("🚨 KẾT LUẬN: CÓ CẢNH BÁO - nội dung sẽ gửi lên Telegram:")
        print("-" * 32)
        for a in alerts:
            print(a)
    else:
        print("✅ KẾT LUẬN: Tất cả tài khoản còn an toàn, không có cảnh báo nào.")
        print()
        print("Nếu bạn muốn test cảnh báo, có thể tạm thời:")
        print("  1. Tăng THRESHOLD_ALERT_AMOUNT trong file test (ví dụ đặt = 99_999_999)")
        print("  2. Hoặc giảm tạm ACCOUNT_THRESHOLDS[0] xuống gần với balance hiện tại")
