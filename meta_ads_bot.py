"""
Meta Ads → Telegram Daily Report Bot v2
- Báo cáo hằng ngày tự động
- Có dòng tổng cộng
- Có nút bấm: 7 ngày, 14 ngày, trong tháng
- Cảnh báo sắp đạt ngưỡng thanh toán (còn ≤ 1.000.000đ)
- Cảnh báo trước 1 ngày đến ngày lập hóa đơn
- Hỗ trợ xem báo cáo theo ngày cụ thể (custom_date)
- Thống kê Lịch hẹn & SĐT mới từ Google Sheet (DATA tháng/năm)
"""

import os
import re
import requests
import schedule
import time
import threading
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIG ────────────────────────────────────────────────
META_ACCESS_TOKEN  = os.getenv("META_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")
REPORT_TIME        = os.getenv("REPORT_TIME", "07:30")
APPS_SCRIPT_URL    = os.getenv("APPS_SCRIPT_URL")

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

BILL_DAYS = [
    int(os.getenv("BILL_DAY_1", 0) or 0),
    int(os.getenv("BILL_DAY_2", 0) or 0),
    int(os.getenv("BILL_DAY_3", 0) or 0),
    int(os.getenv("BILL_DAY_4", 0) or 0),
]

META_API_VERSION = "v21.0"
META_BASE_URL    = f"https://graph.facebook.com/{META_API_VERSION}"
VN_TZ            = timezone(timedelta(hours=7))
AD_ACCOUNT_ID    = None


def get_short_name(full_name: str, fallback: str = "") -> str:
    """Tách 'TK 1650' từ tên dạng 'Ad Account 1650 - CÔNG TY TNHH...'"""
    match = re.search(r"Account\s+(\d+)", full_name or "")
    if match:
        return f"TK {match.group(1)}"
    return full_name or fallback

# ─── META ADS API ───────────────────────────────────────────

def get_account_info():
    url = f"{META_BASE_URL}/{AD_ACCOUNT_ID}"
    params = {
        "fields": "name,currency",
        "access_token": META_ACCESS_TOKEN,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_account_billing(account_id: str) -> dict:
    global AD_ACCOUNT_ID
    AD_ACCOUNT_ID = account_id
    url = f"{META_BASE_URL}/{AD_ACCOUNT_ID}"
    params = {
        "fields": "name,currency,balance",
        "access_token": META_ACCESS_TOKEN,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_insights(date_start: str, date_stop: str):
    url = f"{META_BASE_URL}/{AD_ACCOUNT_ID}/insights"
    params = {
        "fields": "account_name,spend,actions,cost_per_action_type",
        "time_range": f'{{"since":"{date_start}","until":"{date_stop}"}}',
        "level": "account",
        "access_token": META_ACCESS_TOKEN,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return data[0] if data else {}


def extract_action(actions: list, action_type: str) -> int:
    for a in actions or []:
        if a.get("action_type") == action_type:
            return int(float(a.get("value", 0)))
    return 0


def extract_cost_per_action(cost_list: list, action_type: str) -> float:
    for c in cost_list or []:
        if c.get("action_type") == action_type:
            return float(c.get("value", 0))
    return 0.0


def get_account_stats(account_id: str, date_start: str, date_stop: str) -> dict:
    global AD_ACCOUNT_ID
    AD_ACCOUNT_ID = account_id
    insights     = get_insights(date_start, date_stop)
    account_info = get_account_info()
    spend        = float(insights.get("spend", 0))
    actions      = insights.get("actions", [])
    cost_per_act = insights.get("cost_per_action_type", [])
    currency     = account_info.get("currency", "VND")

    messages = extract_action(actions, "onsite_conversion.messaging_first_reply")

    cost_per_msg = extract_cost_per_action(cost_per_act, "onsite_conversion.messaging_first_reply")
    if cost_per_msg == 0:
        cost_per_msg = (spend / messages) if messages > 0 else 0

    purchases = extract_action(actions, "onsite_conversion.purchase")

    return {
        "name":         account_info.get("name", account_id),
        "currency":     currency,
        "spend":        spend,
        "messages":     messages,
        "cost_per_msg": cost_per_msg,
        "purchases":    purchases,
    }

# ─── GOOGLE SHEET - LỊCH HẸN & SĐT MỚI ───────────────────────

def vn_date_from_iso(iso_str: str) -> str:
    """
    Chuyển chuỗi ISO UTC từ Apps Script (luôn dạng '...T17:00:00.000Z')
    sang ngày VN (YYYY-MM-DD). Giờ 17:00 UTC = 00:00 VN ngày hôm sau.
    """
    try:
        dt_utc = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        dt_vn = dt_utc + timedelta(hours=7)
        return dt_vn.strftime("%Y-%m-%d")
    except Exception:
        return ""


def normalize_phone(raw_phone) -> str:
    """
    Chuẩn hóa SĐT về dạng chuỗi, thêm lại số 0 đầu nếu bị mất do Sheet lưu dạng số.
    Ví dụ: 937040104 (number) -> "0937040104"
    """
    if raw_phone is None:
        return ""
    s = str(raw_phone).strip()
    if not s:
        return ""
    if s.endswith(".0"):
        s = s[:-2]
    if s.isdigit() and len(s) == 9:
        s = "0" + s
    return s


def fetch_sheet_data() -> list:
    """Gọi Apps Script Web App, trả về list các dòng dữ liệu thô."""
    if not APPS_SCRIPT_URL:
        print("❌ Thiếu APPS_SCRIPT_URL")
        return []

    resp = requests.get(APPS_SCRIPT_URL, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    return payload.get("data", [])


def get_appointment_count(rows: list, date_start: str, date_stop: str) -> int:
    """
    Đếm số dòng có TÌNH TRẠNG CHỐT = "Chốt lịch hẹn" HOẶC bắt đầu bằng "Đã chuyển đổi"
    (khách đến trong ngày cũng tính là lịch hẹn trong ngày đó)
    trong khoảng [date_start, date_stop] (YYYY-MM-DD, theo giờ VN).
    """
    lich_hen = 0

    for row in rows:
        ngay_raw = row.get("NGÀY", "")
        if not ngay_raw:
            continue

        vn_date = vn_date_from_iso(ngay_raw)
        if not vn_date or vn_date < date_start or vn_date > date_stop:
            continue

        status = (row.get("TÌNH TRẠNG CHỐT", "") or "").strip()
        if status == "Chốt lịch hẹn" or status.startswith("Đã chuyển đổi"):
            lich_hen += 1

    return lich_hen


def get_new_phone_count(rows: list, date_start: str, date_stop: str) -> int:
    """
    Đếm số SĐT mới (khử trùng) có TÌNH TRẠNG SĐT = "Hợp lệ"
    trong khoảng [date_start, date_stop] (YYYY-MM-DD, theo giờ VN).
    """
    seen_phones = set()

    for row in rows:
        ngay_raw = row.get("NGÀY", "")
        if not ngay_raw:
            continue

        vn_date = vn_date_from_iso(ngay_raw)
        if not vn_date or vn_date < date_start or vn_date > date_stop:
            continue

        status = (row.get("TÌNH TRẠNG SĐT", "") or "").strip()
        if status != "Hợp lệ":
            continue

        phone = normalize_phone(row.get("SĐT", ""))
        if phone:
            seen_phones.add(phone)

    return len(seen_phones)

# ─── BUILD REPORT ───────────────────────────────────────────

def build_report(date_start: str, date_stop: str, period_label: str, new_phone_count=None, appointment_count=None) -> str:
    now = datetime.now(VN_TZ)

    if date_start == date_stop:
        date_display = datetime.strptime(date_stop, "%Y-%m-%d").strftime("%d/%m/%Y")
        date_line = f"📅 Ngày {date_display}"
    else:
