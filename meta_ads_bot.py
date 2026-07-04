"""
Meta Ads → Telegram Daily Report Bot v2
- Báo cáo hằng ngày tự động
- Có dòng tổng cộng
- Có nút bấm: 7 ngày, 14 ngày, trong tháng
- Cảnh báo sắp đạt ngưỡng thanh toán (còn ≤ 2.000.000đ)
- Cảnh báo trước 1 ngày đến ngày lập hóa đơn
- Hỗ trợ xem báo cáo theo ngày cụ thể (custom_date)
- SĐT mới từ Pancake (theo từng page)
- Lịch hẹn & SĐT hợp lệ từ Google Sheet DATA
- PH2L từ Google Sheet Livechat
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
    {"id": "108481465282735", "name": "Love + Rosa Quang Trung Go Vap"},
    {"id": "105124961775914", "name": "Love + Rosa Cham Soc Da Mun"},
    {"id": "101059842189274", "name": "Love + Rosa Ky Dong Quan 3"},
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
            print(f"Loi Pancake {page['name']}: {e}")
    return pancake_pages_data

# ─── GOOGLE SHEET ─────────────────────────────────────────────

def vn_date_from_iso(iso_str: str) -> str:
    """Chuyển ISO UTC từ Apps Script sang ngày VN (YYYY-MM-DD)."""
    try:
        dt_utc = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        dt_vn = dt_utc + timedelta(hours=7)
        return dt_vn.strftime("%Y-%m-%d")
    except Exception:
        return ""


def vn_date_from_ddmmyyyy(date_str: str) -> str:
    """Chuyển ngày dạng dd/MM/yyyy sang YYYY-MM-DD."""
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
    """Gọi Apps Script Web App, trả về dict gồm data và livechat."""
    if not APPS_SCRIPT_URL:
        print("Thieu APPS_SCRIPT_URL")
        return {"data": [], "livechat": []}

    resp = requests.get(APPS_SCRIPT_URL, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    return {
        "data": payload.get("data", []),
        "livechat": payload.get("livechat", []),
    }


def get_appointment_count(rows: list, date_start: str, date_stop: str) -> int:
    """Đếm Lịch hẹn: TINH TRANG CHOT = Chot lich hen hoac Da chuyen doi."""
    lich_hen = 0
    for row in rows:
        ngay_raw = row.get("NGAY", "") or row.get("NGÀY", "")
        if not ngay_raw:
            continue
        vn_date = vn_date_from_iso(str(ngay_raw))
        if not vn_date or vn_date < date_start or vn_date > date_stop:
            continue
        status = (row.get("TINH TRANG CHOT", "") or row.get("TÌNH TRẠNG CHỐT", "") or "").strip()
        if status == "Chot lich hen" or status == "Chốt lịch hẹn" or status.startswith("Da chuyen doi") or status.startswith("Đã chuyển đổi"):
            lich_hen += 1
    return lich_hen


def get_new_phone_count_sheet(rows: list, date_start: str, date_stop: str) -> int:
    """Đếm SĐT hợp lệ (khử trùng) từ sheet DATA."""
    seen_phones = set()
    for row in rows:
        ngay_raw = row.get("NGAY", "") or row.get("NGÀY", "")
        if not ngay_raw:
            continue
        vn_date = vn_date_from_iso(str(ngay_raw))
        if not vn_date or vn_date < date_start or vn_date > date_stop:
            continue
        status = (row.get("TINH TRANG SDT", "") or row.get("TÌNH TRẠNG SĐT", "") or "").strip()
        if status != "Hop le" and status != "Hợp lệ":
            continue
        phone = normalize_phone(row.get("SDT", "") or row.get("SĐT", ""))
        if phone:
            seen_phones.add(phone)
    return len(seen_phones)


def get_ph2l_count(livechat_rows: list, date_start: str, date_stop: str) -> int:
    count = 0
    for row in livechat_rows:
        ngay_raw = str(row.get("NGAY", "") or row.get("NGÀY", "") or "").strip()
        if not ngay_raw:
            continue
        vn_date = vn_date_from_ddmmyyyy(ngay_raw)
        if not vn_date:
            vn_date = vn_date_from_iso(ngay_raw)
        if not vn_date or vn_date < date_start or vn_date > date_stop:
            continue
        ghi_chu = (row.get("Ghi chu", "") or row.get("Ghi chú", "") or "").strip()
        if ghi_chu == "PH2L":
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
) -> str:
    now = datetime.now(VN_TZ)

    if date_start == date_stop:
        date_display = datetime.strptime(date_stop, "%Y-%m-%d").strftime("%d/%m/%Y")
        date_line = f"Ngay {date_display}"
    else:
        display_start = datetime.strptime(date_start, "%Y-%m-%d").strftime("%d/%m")
        display_stop  = datetime.strptime(date_stop,  "%Y-%m-%d").strftime("%d/%m/%Y")
        date_line = f"{display_start} - {display_stop}"

    lines = [
        f"BAO CAO META ADS - {period_label.upper()}",
        f"📅 {date_line}",
        f"🕐 Cap nhat luc {now.strftime('%H:%M')}",
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
                f"💸 Chi tieu: {s['spend']:,.0f} {s['currency']}",
                f"💬 Tin nhan moi: {s['messages']:,}",
                f"💰 Gia/tin nhan: {s['cost_per_msg']:,.0f} {s['currency']}",
                f"🛒 Luot mua: {s['purchases']:,}",
            ])
        except Exception as e:
            lines.append(f"Tai khoan {i} loi: {e}")

    total_pancake_phones = 0
    if pancake_pages_data is not None:
        lines.append("-" * 32)
        lines.append("📱 PANCAKE - SDT MOI")
        for page_name, count in pancake_pages_data:
            total_pancake_phones += count
            lines.append(f"🏷️ {page_name}: {count}")

    if sheet_phone_count is not None or appointment_count is not None or ph2l_count is not None:
        lines.append("-" * 32)
        lines.append("📋 DU LIEU TU SHEET")
        if sheet_phone_count is not None:
            lines.append(f"📞 SDT moi hop le: {sheet_phone_count}")
        if appointment_count is not None:
            lines.append(f"📅 Lich hen moi: {appointment_count}")
        if ph2l_count is not None:
            lines.append(f"💬 PH2L: {ph2l_count}")

    lines.append("-" * 32)
    avg_cost = (total_spend / total_msgs) if total_msgs > 0 else 0
    lines.append("📌 TONG CONG")
    lines.append(f"💸 Chi tieu: {total_spend:,.0f} {currency}")
    lines.append(f"💬 Tin nhan moi: {total_msgs:,}")
    lines.append(f"💰 Gia/tin nhan: {avg_cost:,.0f} {currency}")
    if pancake_pages_data is not None:
        cost_per_pancake = (total_spend / total_pancake_phones) if total_pancake_phones > 0 else 0
        lines.append(f"📞 Tong SDT moi (Pancake): {total_pancake_phones}")
        lines.append(f"💵 Chi phi/SDT moi: {cost_per_pancake:,.0f} {currency}")
    if sheet_phone_count is not None:
        cost_per_sheet = (total_spend / sheet_phone_count) if sheet_phone_count > 0 else 0
        lines.append(f"📞 Tong SDT hop le (Sheet): {sheet_phone_count}")
        lines.append(f"💵 Chi phi/SDT hop le: {cost_per_sheet:,.0f} {currency}")
    if appointment_count is not None:
        cost_per_appt = (total_spend / appointment_count) if appointment_count > 0 else 0
        lines.append(f"📅 Lich hen moi: {appointment_count}")
        lines.append(f"📆 Chi phi/Lich hen: {cost_per_appt:,.0f} {currency}")
    if ph2l_count is not None:
        ph2l_ratio = (ph2l_count / total_msgs * 100) if total_msgs > 0 else 0
        lines.append(f"💬 Tong PH2L: {ph2l_count}")
        lines.append(f"📊 Ty le PH2L/Tin nhan: {ph2l_ratio:.1f}%")
    lines.append(f"🛒 Luot mua: {total_buys:,}")

    return "\n".join(lines)


def build_report_with_all_data(date_start: str, date_stop: str, period_label: str) -> str:
    """Lấy dữ liệu Pancake + Sheet (DATA + Livechat), rồi build báo cáo."""
    # Pancake
    try:
        pancake_pages_data = get_pancake_pages_data(date_start, date_stop)
    except Exception as e:
        print(f"Loi Pancake: {e}")
        pancake_pages_data = None

    # Sheet DATA + Livechat
    try:
        sheet_data = fetch_sheet_data()
        rows = sheet_data["data"]
        livechat_rows = sheet_data["livechat"]
        sheet_phone_count = get_new_phone_count_sheet(rows, date_start, date_stop)
        appointment_count = get_appointment_count(rows, date_start, date_stop)
        ph2l_count = get_ph2l_count(livechat_rows, date_start, date_stop)
    except Exception as e:
        print(f"Loi Sheet: {e}")
        sheet_phone_count = None
        appointment_count = None
        ph2l_count = None

    return build_report(
        date_start, date_stop, period_label,
        pancake_pages_data=pancake_pages_data,
        sheet_phone_count=sheet_phone_count,
        appointment_count=appointment_count,
        ph2l_count=ph2l_count,
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
                {"text": "7 ngay",       "callback_data": "period_7"},
                {"text": "14 ngay",      "callback_data": "period_14"},
                {"text": "Trong thang",  "callback_data": "period_month"},
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
            name     = get_short_name(info.get("name", ""), fallback=f"Tai khoan {i}")
            currency = info.get("currency", "VND")
            balance  = float(info.get("balance", 0))

            threshold = ACCOUNT_THRESHOLDS[i-1] if i-1 < len(ACCOUNT_THRESHOLDS) else 0

            if threshold > 0:
                remaining = threshold - balance
                if remaining <= THRESHOLD_ALERT_AMOUNT:
                    if remaining <= 0:
                        alerts.append(f"🔴 {name} DA DAT/VUOT nguong thanh toan! Vui long kiem tra the.")
                    else:
                        alerts.append(f"⚠️ {name} con {remaining:,.0f}d den nguong thanh toan.")

            bill_day = BILL_DAYS[i-1] if i-1 < len(BILL_DAYS) else 0
            if bill_day > 0:
                now      = datetime.now(VN_TZ)
                tomorrow = now + timedelta(days=1)
                if tomorrow.day == bill_day:
                    alerts.append(f"📅 {name} con 1 ngay nua den ngay lap hoa don, vui long nap tien/kiem tra the.")
        except Exception as e:
            print(f"Loi kiem tra billing tai khoan {i}: {e}")

    if alerts:
        msg  = "CANH BAO THANH TOAN\n"
        msg += "-" * 32 + "\n"
        msg += "\n".join(alerts)
        send_telegram(msg)
        print("Da gui canh bao!")
    else:
        print("Tat ca tai khoan con an toan.")


def daily_job():
    print(f"[{datetime.now(VN_TZ).strftime('%H:%M:%S')}] Dang lay du lieu Meta Ads...")

    try:
        date_start, date_stop = get_dates(1)
        report = build_report_with_all_data(date_start, date_stop, "Hom qua")
        print("=== NOI DUNG TIN NHAN ===")
        print(repr(report))
        send_telegram_with_buttons(report)
        print("Da gui bao cao len Telegram.")
    except Exception as e:
        print(f"Loi gui bao cao: {e}")
        send_telegram(f"Meta Ads Bot loi\n{e}")

    try:
        check_spending_alert()
    except Exception as e:
        print(f"Loi check spending alert: {e}")


# ─── LANG NGHE NUT BAM ──────────────────────────────────────

def listen_callbacks():
    print("Dang lang nghe nut bam...")
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
                print(f"Nhan callback: {data_val}")

                if data_val == "period_7":
                    date_start, date_stop = get_dates(7)
                    period_label = "7 ngay qua"
                elif data_val == "period_14":
                    date_start, date_stop = get_dates(14)
                    period_label = "14 ngay qua"
                elif data_val == "period_month":
                    date_start, date_stop = get_dates(0)
                    period_label = "Trong thang"
                else:
                    continue

                report = build_report_with_all_data(date_start, date_stop, period_label)
                send_telegram(report)
                print(f"Da gui bao cao: {data_val}")

        except Exception as e:
            print(f"Loi listener: {e}")
            time.sleep(5)


# ─── MAIN ───────────────────────────────────────────────────

if __name__ == "__main__":
    period = os.getenv("PERIOD", "daily")
    print(f"Chay voi period: {period}")

    if period == "period_7":
        date_start, date_stop = get_dates(7)
        report = build_report_with_all_data(date_start, date_stop, "7 ngay qua")
        send_telegram(report)

    elif period == "period_14":
        date_start, date_stop = get_dates(14)
        report = build_report_with_all_data(date_start, date_stop, "14 ngay qua")
        send_telegram(report)

    elif period == "period_month":
        date_start, date_stop = get_dates(0)
        report = build_report_with_all_data(date_start, date_stop, "Trong thang")
        send_telegram(report)

    elif period == "custom_date":
        custom_date = os.getenv("CUSTOM_DATE")
        if not custom_date:
            print("Thieu CUSTOM_DATE")
            send_telegram("Loi: thieu ngay de bao cao (CUSTOM_DATE rong).")
        else:
            report = build_report_with_all_data(custom_date, custom_date, "Theo ngay")
            send_telegram(report)

    else:
        daily_job()
