import os
from datetime import datetime, timedelta, timezone

VN_TZ = timezone(timedelta(hours=7))

BILL_DAYS = [
    int(os.getenv("BILL_DAY_1", 0) or 0),
    int(os.getenv("BILL_DAY_2", 0) or 0),
    int(os.getenv("BILL_DAY_3", 0) or 0),
    int(os.getenv("BILL_DAY_4", 0) or 0),
]

AD_ACCOUNT_NAMES = [
    "TK 1650",
    "TK 3742",
    "TK 5186",
    "TK 4 (chưa set)",
]

if __name__ == "__main__":
    now = datetime.now(VN_TZ)
    tomorrow = now + timedelta(days=1)

    print(f"=== KIỂM TRA CẢNH BÁO NGÀY THANH TOÁN ===")
    print(f"Hôm nay: {now.strftime('%d/%m/%Y')}")
    print(f"Ngày mai: {tomorrow.strftime('%d/%m/%Y')} (ngày {tomorrow.day})")
    print()

    print("=== GIÁ TRỊ BILL_DAY TỪNG TÀI KHOẢN ===")
    for i, (bill_day, name) in enumerate(zip(BILL_DAYS, AD_ACCOUNT_NAMES), 1):
        print(f"  BILL_DAY_{i} ({name}): {bill_day}")
    print()

    print("=== KẾT QUẢ KIỂM TRA ===")
    alerts = []
    for i, (bill_day, name) in enumerate(zip(BILL_DAYS, AD_ACCOUNT_NAMES), 1):
        if bill_day == 0:
            print(f"  {name}: ⚪ Chưa set BILL_DAY_{i}, bỏ qua")
            continue
        if tomorrow.day == bill_day:
            msg = f"📅 {name} còn 1 ngày nữa đến ngày lập hóa đơn (ngày {bill_day}), vui lòng nạp tiền/kiểm tra thẻ."
            alerts.append(msg)
            print(f"  {name}: 🔔 MATCH - ngày mai ({tomorrow.day}) = bill_day ({bill_day}) → SẼ CÓ CẢNH BÁO")
        else:
            print(f"  {name}: ✅ Chưa đến ngày - ngày mai ({tomorrow.day}) ≠ bill_day ({bill_day})")
    print()

    if alerts:
        print("=== NỘI DUNG CẢNH BÁO SẼ GỬI LÊN TELEGRAM ===")
        print("🚨 CẢNH BÁO THANH TOÁN")
        print("-" * 32)
        for a in alerts:
            print(a)
    else:
        print("=== KẾT LUẬN: Không có cảnh báo nào được kích hoạt hôm nay ===")
        print("Nếu bạn muốn test cảnh báo, hãy set BILL_DAY_X bằng đúng ngày mai:")
        print(f"  → Ngày mai là ngày {tomorrow.day}, cần set BILL_DAY_X={tomorrow.day} để test")
