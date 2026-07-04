"""
Meta Ads → Telegram Daily Report Bot v2
- Báo cáo hằng ngày tự động
- Có dòng tổng cộng
- Có nút bấm: 7 ngày, 14 ngày, trong tháng
- Cảnh báo sắp đạt ngưỡng thanh toán (còn ≤ 2.000.000đ)
- Cảnh báo trước 1 ngày đến ngày lập hóa đơn
- Hỗ trợ xem báo cáo theo ngày cụ thể (custom_date)
- Hỗ trợ xem báo cáo theo khoảng ngày (date_range)
- SĐT mới từ Pancake (theo từng page)
- Lịch hẹn & SĐT hợp lệ từ Google Sheet DATA
- PH2L từ Google Sheet Livechat
- Khách đến từ Google Sheet CI
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
PANCAKE_TOKEN      = os.getenv("PANCAKE_TOKEN")
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

THRESHOLD_ALERT_AMOUNT = 2_000_000

PANCAKE_PAGES = [
    {"id": "103905658090177", "name": "Love + Rosa Skin Center"},
    {"id": "108481465282735", "name": "Love + Rosa Quang Trung Gò Vấp"},
    {"id": "105124961775914", "name": "Love + Rosa Chăm Sóc Da Mụn"},
    {"id": "101059842189274", "name": "Love + Rosa Kỳ Đồng Quận 3"},
]

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
    match = re.search(r"Account\s+(\d+)", full_name or "")
    if match:
        return f"TK {match.group(1)}"
    return full_name or fallback

# ─── META ADS API ───────────────────────────────────────────

def get_account_info():
    url = f"{META_BASE_URL}/{AD_ACCOUNT_ID}"
    params = {"fields": "name,currency", "access_token": META_ACCESS_TOKEN}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_account_billing(account_id: str) -> dict:
    global AD_ACCOUNT_ID
    AD_ACCOUNT_ID = account_id
    url = f"{META_BASE_URL}/{AD_ACCOUNT_ID}"
    params = {"fields": "name,currency,balance", "access_token": META_ACCESS_TOKEN}
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

# ─── PANCAKE API ────────────────────────────────────────────

def get_pancake_conversations(page_id: str, limit: int = 500) -> list:
    url = f"https://pancake.vn/api/v1/pages/{page_id}/conversations"
    params = {"access_token": PANCAKE_TOKEN, "limit": limit}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("conversations", [])


def get_pancake_new_phones(page_id: str, date_start: str, date_stop: str) -> list:
    conversations = get_pancake_conversations(page_id, limit=500)
    seen_phones = set()
    phones = []

    for conv in conversations:
        inserted = conv.get("inserted_at", "")[:10]
        if not inserted or inserted < date_start or inserted > date_stop:
            continue
        phone_list = conv.get("recent_phone_numbers", [])
        if not phone_list:
            continue
        latest_phone = phone_list[0].get("phone_number", "")
        if latest_phone and latest_phone not in seen_phones:
            seen_phones.add(latest_phone)
            phones.append({
                "phone": latest_phone,
                "name": conv.get("customers", [{}])[0].get("name", ""),
            })

    return phones


def get_pancake_pages_data(date_start: str, date_stop: str) -> list:
    pancake_pages_data = []
    for page in PANCAKE_PAGES:
        try:
            phones = get_pancake_new_phones(page["id"], date_start, date_stop)
            pancake_pages_data.append((page["name"], len(phones)))
        except Exception as e:
            pancake_pages_data.append((page["name"], 0))
            print(f"❌ Lỗi Pancake {page['name']}: {e}")
    return pancake_pages_data

# ─── GOOGLE SHEET ─────────────────────────────────────────────

def vn_date_from_iso(iso_str: str) -> str:
    try:
        dt_utc = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        dt_vn = dt_utc + timedelta(hours=7)
        return dt_vn.strftime("%Y-%m-%d")
    except Exception:
        return ""


def vn_date_from_ddmmyyyy(date_str: str) -> str:
    try:
        dt = datetime.strptime(str(date_str).strip(), "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return ""


def normalize_phone(raw_phone) -> str:
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


def fetch_sheet_data() -> dict:
    if not APPS_SCRIPT_URL:
        print("❌ Thiếu APPS_SCRIPT_URL")
        return {"data": [], "livechat": [], "ci": []}

    resp = requests.get(APPS_SCRIPT_URL, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    return {
        "data": payload.get("data", []),
        "livechat": payload.get("livechat", []),
        "ci": payload.get("ci", []),
    }


def get_appointment_count(rows: list, date_start: str, date_stop: str) -> int:
    lich_hen = 0
    for row in rows:
        ngay_raw = row.get("NGÀY", "") or row.get("NGAY", "")
        if not ngay_raw:
            continue
        vn_date = vn_date_from_iso(str(ngay_raw))
        if not vn_date or vn_date < date_start or vn_date > date_stop:
            continue
        status = (row.get("TÌNH TRẠNG CHỐT", "") or row.get("TINH TRANG CHOT", "") or "").strip()
        if status == "Chốt lịch hẹn" or status.startswith("Đã chuyển đổi"):
            lich_hen += 1
    return lich_hen


def get_new_phone_count_sheet(rows: list, date_start: str, date_stop: str) -> int:
    seen_phones = set()
    for row in rows:
        ngay_raw = row.get("NGÀY", "") or row.get("NGAY", "")
        if not ngay_raw:
            continue
        vn_date = vn_date_from_iso(str(ngay_raw))
        if not vn_date or vn_date < date_start or vn_date > date_stop:
            continue
        status = (row.get("TÌNH TRẠNG SĐT", "") or row.get("TINH TRANG SDT", "") or "").strip()
        if status != "Hợp lệ":
            continue
        phone = normalize_phone(row.get("SĐT", "") or row.get("SDT", ""))
        if phone:
            seen_phones.add(phone)
    return len(seen_phones)


def get_ph2l_count(livechat_rows: list, date_start: str, date_stop: str) -> int:
    count = 0
    for row in livechat_rows:
        ngay_raw = str(row.get("NGÀY", "") or row.get("NGAY", "") or "").strip()
        if not ngay_raw:
            continue
        vn_date = vn_date_from_ddmmyyyy(ngay_raw)
        if not vn_date:
            vn_date = vn_date_from_iso(ngay_raw)
        if not vn_date or vn_date < date_start or vn_date > date_stop:
            continue
        ghi_chu = (row.get("Ghi chú", "") or row.get("Ghi chu", "") or "").strip()
        if ghi_chu == "PH2L":
            count += 1
    return count


def get_checkin_count(ci_rows: list, date_start: str, date_stop: str) -> int:
    """
    Đếm số khách đã check-in (checked=True) trong khoảng [date_start, date_stop].
    Ngày dạng dd/MM/yyyy từ Apps Script.
    """
    count = 0
    for row in ci_rows:
        ngay_raw = str(row.get("ngay", "") or "").strip()
        if not ngay_raw:
            continue
        vn_date = vn_date_from_ddmmyyyy(ngay_raw)
        if not vn_date or vn_date < date_start or vn_date > date_stop:
            continue
        if row.get("checked") is True:
            count += 1
    return count

# ─── BUILD REPORT ───────────────────────────────────────────

def build_report(
    date_start: str,
    date_stop: str,
    period_label: str,
    pancake_pages_data=None,
    sheet_phone_count=None,
    appointment_count=None,
    ph2l_count=None,
    checkin_count=None,
) -> str:
    now = datetime.now(VN_TZ)

    if date_start == date_stop:
        date_display = datetime.strptime(date_stop, "%Y-%m-%d").strftime("%d/%m/%Y")
        date_line = f"📅 Ngày {date_display}"
    else:
        display_start = datetime.strptime(date_start, "%Y-%m-%d").strftime("%d/%m")
        display_stop  = datetime.strptime(date_stop,  "%Y-%m-%d").strftime("%d/%m/%Y")
        date_line = f"📅 {display_start} – {display_stop}"

    lines = [
        f"📊 BÁO CÁO META ADS – {period_label.upper()}",
        date_line,
        f"🕐 Cập nhật lúc {now.strftime('%H:%M')}",
        "=" * 32,
    ]

    total_spend = 0.0
    total_msgs  = 0
    total_buys  = 0
    currency    = "VND"

    account_count = 0
    for i, account_id in enumerate(AD_ACCOUNTS, 1):
        if not account_id:
            continue
        account_count += 1
        if account_count > 1:
            lines.append("-" * 32)
        try:
            s = get_account_stats(account_id, date_start, date_stop)
            currency = s["currency"]
            total_spend += s["spend"]
            total_msgs  += s["messages"]
            total_buys  += s["purchases"]
            lines.extend([
                f"🏷️ {s['name']}",
                f"💸 Chi tiêu: {s['spend']:,.0f} {s['currency']}",
                f"💬 Tin nhắn mới: {s['messages']:,}",
                f"💰 Giá/tin nhắn: {s['cost_per_msg']:,.0f} {s['currency']}",
                f"🛒 Lượt mua: {s['purchases']:,}",
            ])
        except Exception as e:
            lines.append(f"❌ Tài khoản {i} lỗi: {e}")

    # Pancake
    total_pancake_phones = 0
    if pancake_pages_data is not None:
        lines.append("-" * 32)
        lines.append("📱 PANCAKE - SĐT MỚI")
        for page_name, count in pancake_pages_data:
            total_pancake_phones += count
            lines.append(f"🏷️ {page_name}: {count}")

    # Sheet
    if any(x is not None for x in [sheet_phone_count, appointment_count, checkin_count, ph2l_count]):
        lines.append("-" * 32)
        lines.append("📋 DỮ LIỆU TỪ SHEET")
        if sheet_phone_count is not None:
            lines.append(f"📞 SĐT mới hợp lệ: {sheet_phone_count}")
        if appointment_count is not None:
            lines.append(f"📅 Lịch hẹn mới: {appointment_count}")
        if checkin_count is not None:
            lines.append(f"✅ Khách đến: {checkin_count}")
        if ph2l_count is not None:
            lines.append(f"💬 PH2L: {ph2l_count}")

    # Tổng cộng
    lines.append("-" * 32)
    avg_cost = (total_spend / total_msgs) if total_msgs > 0 else 0
    lines.append("📌 TỔNG CỘNG")
    lines.append(f"💸 Chi tiêu: {total_spend:,.0f} {currency}")
    lines.append(f"💬 Tin nhắn mới: {total_msgs:,}")
    lines.append(f"💰 Giá/tin nhắn: {avg_cost:,.0f} {currency}")
    if pancake_pages_data is not None:
        lines.append(f"📞 Tổng SĐT mới (Pancake): {total_pancake_phones}")
    if sheet_phone_count is not None:
        cost_per_sheet = (total_spend / sheet_phone_count) if sheet_phone_count > 0 else 0
        lines.append(f"📞 Tổng SĐT hợp lệ (Sheet): {sheet_phone_count}")
        lines.append(f"💵 Chi phí/SĐT hợp lệ: {cost_per_sheet:,.0f} {currency}")
    if ph2l_count is not None:
        ph2l_ratio = (ph2l_count / total_msgs * 100) if total_msgs > 0 else 0
        cost_per_ph2l = (total_spend / ph2l_count) if ph2l_count > 0 else 0
        lines.append(f"💬 Tổng PH2L: {ph2l_count}")
        lines.append(f"📊 Tỷ lệ PH2L/Tin nhắn: {ph2l_ratio:.1f}%")
        lines.append(f"💰 Chi phí/tin PH2L: {cost_per_ph2l:,.0f} {currency}")
    if appointment_count is not None:
        cost_per_appt = (total_spend / appointment_count) if appointment_count > 0 else 0
        lines.append(f"📅 Lịch hẹn mới: {appointment_count}")
        lines.append(f"📆 Chi phí/Lịch hẹn: {cost_per_appt:,.0f} {currency}")
    if checkin_count is not None:
        cost_per_checkin = (total_spend / checkin_count) if checkin_count > 0 else 0
        lines.append(f"✅ Khách đến: {checkin_count}")
        lines.append(f"💰 Chi phí/Khách đến: {cost_per_checkin:,.0f} {currency}")
        lines.append(f"💰 Chi phí/Khách đến: {cost_per_checkin:,.0f} {currency}")

    lines.append(f"🛒 Lượt mua: {total_buys:,}")

    return "\n".join(lines)


def build_report_with_all_data(date_start: str, date_stop: str, period_label: str) -> str:
    # Pancake
    try:
        pancake_pages_data = get_pancake_pages_data(date_start, date_stop)
    except Exception as e:
        print(f"❌ Lỗi Pancake: {e}")
        pancake_pages_data = None

    # Sheet DATA + Livechat + CI
    try:
        sheet_data = fetch_sheet_data()
        rows = sheet_data["data"]
        livechat_rows = sheet_data["livechat"]
        ci_rows = sheet_data["ci"]
        sheet_phone_count = get_new_phone_count_sheet(rows, date_start, date_stop)
        appointment_count = get_appointment_count(rows, date_start, date_stop)
        ph2l_count = get_ph2l_count(livechat_rows, date_start, date_stop)
        checkin_count = get_checkin_count(ci_rows, date_start, date_stop)
    except Exception as e:
        print(f"❌ Lỗi Sheet: {e}")
        sheet_phone_count = None
        appointment_count = None
        ph2l_count = None
        checkin_count = None

    return build_report(
        date_start, date_stop, period_label,
        pancake_pages_data=pancake_pages_data,
        sheet_phone_count=sheet_phone_count,
        appointment_count=appointment_count,
        ph2l_count=ph2l_count,
        checkin_count=checkin_count,
    )


def get_dates(days: int):
    now = datetime.now(VN_TZ)
    date_stop = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    if days == 0:
        date_start = now.replace(day=1).strftime("%Y-%m-%d")
    else:
        date_start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    return date_start, date_stop


# ─── TELEGRAM ───────────────────────────────────────────────

def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def send_telegram_with_buttons(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text":    message,
        "reply_markup": {
            "inline_keyboard": [[
                {"text": "📅 7 ngày",      "callback_data": "period_7"},
                {"text": "📅 14 ngày",     "callback_data": "period_14"},
                {"text": "📅 Trong tháng", "callback_data": "period_month"},
            ]]
        }
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def answer_callback(callback_query_id: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    requests.post(url, json={"callback_query_id": callback_query_id}, timeout=10)


# ─── JOB ────────────────────────────────────────────────────

def check_spending_alert():
    alerts = []

    for i, account_id in enumerate(AD_ACCOUNTS, 1):
        if not account_id:
            continue
        try:
            info     = get_account_billing(account_id)
            name     = get_short_name(info.get("name", ""), fallback=f"Tài khoản {i}")
            currency = info.get("currency", "VND")
            balance  = float(info.get("balance", 0))

            threshold = ACCOUNT_THRESHOLDS[i-1] if i-1 < len(ACCOUNT_THRESHOLDS) else 0

            if threshold > 0:
                remaining = threshold - balance
                if remaining <= THRESHOLD_ALERT_AMOUNT:
                    if remaining <= 0:
                        alerts.append(f"🔴 {name} ĐÃ ĐẠT/VƯỢT ngưỡng thanh toán! Vui lòng kiểm tra thẻ.")
                    else:
                        alerts.append(f"⚠️ {name} còn {remaining:,.0f}đ đến ngưỡng thanh toán.")

            bill_day = BILL_DAYS[i-1] if i-1 < len(BILL_DAYS) else 0
            if bill_day > 0:
                now      = datetime.now(VN_TZ)
                tomorrow = now + timedelta(days=1)
                if tomorrow.day == bill_day:
                    alerts.append(f"📅 {name} còn 1 ngày nữa đến ngày lập hóa đơn, vui lòng nạp tiền/kiểm tra thẻ.")
        except Exception as e:
            print(f"❌ Lỗi kiểm tra billing tài khoản {i}: {e}")

    if alerts:
        msg  = "🚨 CẢNH BÁO THANH TOÁN\n"
        msg += "-" * 32 + "\n"
        msg += "\n".join(alerts)
        send_telegram(msg)
        print("✅ Đã gửi cảnh báo!")
    else:
        print("✅ Tất cả tài khoản còn an toàn.")


def daily_job():
    print(f"[{datetime.now(VN_TZ).strftime('%H:%M:%S')}] Đang lấy dữ liệu Meta Ads...")

    try:
        date_start, date_stop = get_dates(1)
        report = build_report_with_all_data(date_start, date_stop, "Hôm qua")
        print("=== NỘI DUNG TIN NHẮN ===")
        print(repr(report))
        send_telegram_with_buttons(report)
        print("✅ Đã gửi báo cáo lên Telegram.")
    except Exception as e:
        print(f"❌ Lỗi gửi báo cáo: {e}")
        send_telegram(f"⚠️ Meta Ads Bot lỗi\n{e}")

    try:
        check_spending_alert()
    except Exception as e:
        print(f"❌ Lỗi check spending alert: {e}")


# ─── LẮNG NGHE NÚT BẤM ─────────────────────────────────────

def listen_callbacks():
    print("👂 Đang lắng nghe nút bấm...")
    url    = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    offset = None

    while True:
        try:
            params = {"timeout": 30, "allowed_updates": ["callback_query"]}
            if offset:
                params["offset"] = offset
            resp = requests.get(url, params=params, timeout=35)
            data = resp.json()

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                cb = update.get("callback_query")
                if not cb:
                    continue

                answer_callback(cb["id"])
                data_val = cb.get("data", "")
                print(f"🔔 Nhận callback: {data_val}")

                if data_val == "period_7":
                    date_start, date_stop = get_dates(7)
                    period_label = "7 ngày qua"
                elif data_val == "period_14":
                    date_start, date_stop = get_dates(14)
                    period_label = "14 ngày qua"
                elif data_val == "period_month":
                    date_start, date_stop = get_dates(0)
                    period_label = "Trong tháng"
                else:
                    continue

                report = build_report_with_all_data(date_start, date_stop, period_label)
                send_telegram(report)
                print(f"✅ Đã gửi báo cáo: {data_val}")

        except Exception as e:
            print(f"❌ Lỗi listener: {e}")
            time.sleep(5)


# ─── MAIN ───────────────────────────────────────────────────

if __name__ == "__main__":
    period = os.getenv("PERIOD", "daily")
    print(f"🤖 Chạy với period: {period}")

    if period == "period_7":
        date_start, date_stop = get_dates(7)
        report = build_report_with_all_data(date_start, date_stop, "7 ngày qua")
        send_telegram(report)

    elif period == "period_14":
        date_start, date_stop = get_dates(14)
        report = build_report_with_all_data(date_start, date_stop, "14 ngày qua")
        send_telegram(report)

    elif period == "period_month":
        date_start, date_stop = get_dates(0)
        report = build_report_with_all_data(date_start, date_stop, "Trong tháng")
        send_telegram(report)

    elif period == "custom_date":
        custom_date = os.getenv("CUSTOM_DATE")
        if not custom_date:
            print("❌ Thiếu CUSTOM_DATE")
            send_telegram("⚠️ Lỗi: thiếu ngày để báo cáo (CUSTOM_DATE rỗng).")
        else:
            report = build_report_with_all_data(custom_date, custom_date, "Theo ngày")
            send_telegram(report)

    elif period == "date_range":
        date_range = os.getenv("DATE_RANGE", "")
        if not date_range or "|" not in date_range:
            print("❌ Thiếu DATE_RANGE hoặc sai định dạng")
            send_telegram("⚠️ Lỗi: thiếu khoảng ngày (DATE_RANGE rỗng hoặc sai định dạng).")
        else:
            date_start, date_stop = date_range.split("|", 1)
            date_start = date_start.strip()
            date_stop  = date_stop.strip()
            label = (
                f"{datetime.strptime(date_start, '%Y-%m-%d').strftime('%d/%m')}"
                f" – "
                f"{datetime.strptime(date_stop, '%Y-%m-%d').strftime('%d/%m/%Y')}"
            )
            report = build_report_with_all_data(date_start, date_stop, label)
            send_telegram(report)

    else:
        daily_job()
