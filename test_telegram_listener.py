import re
import sys

# ============================================================
# Copy nguyên hàm parse_command từ telegram_listener.py
# ============================================================

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

    # Format YYYY-MM-DD
    match = re.match(r"/ngay\s+(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        y, m, d = match.groups()
        return ("custom_date", f"{y}-{m}-{d}")

    # Format DD/MM/YYYY
    match = re.match(r"/ngay\s+(\d{2})/(\d{2})/(\d{4})", text)
    if match:
        d, m, y = match.groups()
        return ("custom_date", f"{y}-{m}-{d}")

    # Format DD.MM.YYYY
    match = re.match(r"/ngay\s+(\d{2})\.(\d{2})\.(\d{4})", text)
    if match:
        d, m, y = match.groups()
        return ("custom_date", f"{y}-{m}-{d}")

    return (None, None)


# ============================================================
# Danh sách test cases: (input, expected_output)
# ============================================================

TEST_CASES = [
    # --- Lệnh cơ bản ---
    ("/baocao",              ("daily", None)),
    ("/hom_qua",             ("daily", None)),
    ("báo cáo",              ("daily", None)),
    ("báo cáo hôm qua",      ("daily", None)),
    ("/7ngay",               ("period_7", None)),
    ("/7_ngay",              ("period_7", None)),
    ("7 ngày",               ("period_7", None)),
    ("/14ngay",              ("period_14", None)),
    ("/14_ngay",             ("period_14", None)),
    ("14 ngày",              ("period_14", None)),
    ("/thang",               ("period_month", None)),
    ("trong tháng",          ("period_month", None)),

    # --- /ngay format YYYY-MM-DD ---
    ("/ngay 2026-06-22",     ("custom_date", "2026-06-22")),
    ("/ngay 2026-01-01",     ("custom_date", "2026-01-01")),

    # --- /ngay format DD/MM/YYYY ---
    ("/ngay 22/06/2026",     ("custom_date", "2026-06-22")),
    ("/ngay 01/01/2026",     ("custom_date", "2026-01-01")),

    # --- /ngay format DD.MM.YYYY (vừa fix) ---
    ("/ngay 22.06.2026",     ("custom_date", "2026-06-22")),
    ("/ngay 01.01.2026",     ("custom_date", "2026-01-01")),

    # --- Khoảng trắng thừa ---
    ("  /baocao  ",          ("daily", None)),
    ("  /ngay 22.06.2026  ", ("custom_date", "2026-06-22")),

    # --- Lệnh không hợp lệ → (None, None) ---
    ("/ngay abc",            (None, None)),
    ("/ngay 22-06-2026",     (None, None)),   # sai thứ tự ngày/năm
    ("/unknown",             (None, None)),
    ("hello",                (None, None)),
    ("",                     (None, None)),
]


# ============================================================
# Chạy test
# ============================================================

def run_tests():
    passed = 0
    failed = 0

    print("=" * 60)
    print("  TELEGRAM LISTENER — PARSE COMMAND TEST")
    print("=" * 60)

    for text, expected in TEST_CASES:
        result = parse_command(text)
        ok = result == expected

        if ok:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1

        print(f"{status}  input={repr(text)}")
        if not ok:
            print(f"         expected : {expected}")
            print(f"         got      : {result}")

    print("=" * 60)
    print(f"  Kết quả: {passed} passed, {failed} failed / {len(TEST_CASES)} tests")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)   # GitHub Actions đánh dấu step là FAILED


if __name__ == "__main__":
    run_tests()
