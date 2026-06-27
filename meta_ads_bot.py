"""
Meta Ads → Telegram Daily Report Bot v2
- Báo cáo hằng ngày tự động
- Có dòng tổng cộng
- Có nút bấm: 7 ngày, 14 ngày, trong tháng
- Cảnh báo ngưỡng thanh toán
- Cảnh báo ngày thanh toán hóa đơn
"""

import os
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

AD_ACCOUNTS = [
    os.getenv("AD_ACCOUNT_1"),
    os.getenv("AD_ACCOUNT_2"),
    os.getenv("AD_ACCOUNT_3"),
    os.getenv("AD_ACCOUNT_4"),
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
    """Lấy thông tin hạn mức và số dư tài khoản"""
    global AD_ACCOUNT_ID
    AD_ACCOUNT_ID = account_id
    url = f"{META_BASE_URL}/{AD_ACCOUNT_ID}"
    params = {
        "fields": "name,currency,spend_cap,amount_spent,balance",
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

    messages = extract_action(actions, "onsite_conversion.messaging_conversation_started_7d")
    if messages == 0:
        messages = extract_action(actions, "onsite_conversion.messaging_first_reply")

    cost_per_msg = extract_cost_per_action(cost_per_act, "onsite_conversion.messaging_conversation_started_7d")
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


# ─── BUILD REPORT ───────────────────────────────────────────

def build_report(date_start: str, date_stop: str, period_label: str) -> str:
    now           = datetime.now(VN_TZ)
    display_start = datetime.strptime(date_start, "%Y-%m-%d").strftime("%d/%m")
    display_stop  = datetime.strptime(date_stop,  "%Y-%m-%d").strftime("%d/%m/%Y")

    report = (
        f"📊 <b>BÁO CÁO META ADS – {period_label.upper()}</b>\n"
        f"📅 {display_start} – {display_stop}\n"
        f"🕐 Cập nhật lúc {now.strftime('%H:%M')}\n"
        f"{'═' * 32}\n\n"
    )

    total_spend = 0.0
    total_msgs  = 0
    total_buys  = 0
    currency    = "VND"

    for i, account_id in enumerate(AD_ACCOUNTS, 1):
        if not account_id:
            continue
        try:
            s        = get_account_stats(account_id, date_start, date_stop)
            currency = s["currency"]
            total_spend += s["spend"]
            total_msgs  += s["messages"]
            total_buys  += s["purchases"]

            report += (
                f"🏷️ <b>{s['name']}</b>\n"
                f"💸 Chi tiêu: {s['spend']:,.0f} {s['currency']}\n"
                f"💬 Tin nhắn mới: {s['messages']:,}\n"
                f"💰 Giá/tin nhắn: {s['cost_per_msg']:,.0f} {s['currency']}\n"
                f"🛒 Lượt mua: {s['purchases']:,}\n"
                f"{'─' * 32}\n\n"
            )
        except Exception as e:
            report += f"❌ Tài khoản {i} lỗi: {e}\n\n"

    avg_cost = (total_spend / total_msgs) if total_msgs > 0 else 0
    report += (
        f"📌 <b>TỔNG CỘNG</b>\n"
        f"💸 Chi tiêu: {total_spend:,.0f} {currency}\n"
        f"💬 Tin nhắn mới: {total_msgs:,}\n"
        f"💰 Giá/tin nhắn: {avg_cost:,.0f} {currency}\n"
        f"🛒 Lượt mua: {total_buys:,}\n"
    )
    return report


def get_dates(days: int):
    """Trả về (date_start, date_stop). days=0 → từ đầu tháng"""
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
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       message,
        "parse_mode": "HTML",
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def send_telegram_with_buttons(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       message,
        "parse_mode": "HTML",
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
ALERT_THRESHOLD = 1_000_000  # Cảnh báo khi còn dưới 1 triệu VND

def check_spending_alert():
    """Kiểm tra và gửi cảnh báo nếu sắp đạt ngưỡng thanh toán"""
    alerts = []

    for i, account_id in enumerate(AD_ACCOUNTS, 1):
        if not account_id:
            continue
        try:
            info         = get_account_billing(account_id)
            name         = info.get("name", f"Tài khoản {i}")
            currency     = info.get("currency", "VND")
            spend_cap    = float(info.get("spend_cap", 0))
            amount_spent = float(info.get("amount_spent", 0))
            balance      = float(info.get("balance", 0))

            if spend_cap > 0:
                remaining = spend_cap - amount_spent
                percent   = (amount_spent / spend_cap) * 100
                if remaining <= ALERT_THRESHOLD:
                    alerts.append(
                        f"⚠️ <b>{name}</b>\n"
                        f"💸 Đã chi: {amount_spent:,.0f} / {spend_cap:,.0f} {currency}\n"
                        f"📊 Đã dùng: {percent:.1f}%\n"
                        f"🔴 Còn lại: {remaining:,.0f} {currency}\n"
                    )
            elif balance > 0:
                if balance <= ALERT_THRESHOLD:
                    alerts.append(
                        f"⚠️ <b>{name}</b>\n"
                        f"🔴 Số dư còn lại: {balance:,.0f} {currency}\n"
                    )

            # Kiểm tra ngày thanh toán
            bill_day = BILL_DAYS[i-1] if i-1 < len(BILL_DAYS) else 0
            if bill_day > 0:
                now      = datetime.now(VN_TZ)
                tomorrow = now + timedelta(days=1)
                if tomorrow.day == bill_day:
                    alerts.append(
                        f"📅 <b>{name}</b>\n"
                        f"⏰ Ngày mai ({tomorrow.strftime('%d/%m/%Y')}) là ngày thanh toán hóa đơn!\n"
                        f"💳 Vui lòng kiểm tra số dư tài khoản!\n"
                    )
        except Exception as e:
            print(f"❌ Lỗi kiểm tra billing tài khoản {i}: {e}")

    if alerts:
        msg  = "🚨 <b>CẢNH BÁO NGƯỠNG THANH TOÁN</b>\n"
        msg += "═" * 32 + "\n\n"
        msg += "\n".join(alerts)
        msg += "\n💳 Vui lòng nạp tiền để tránh gián đoạn quảng cáo!"
        send_telegram(msg)
        print("✅ Đã gửi cảnh báo ngưỡng thanh toán!")
    else:
        print("✅ Tất cả tài khoản còn trong ngưỡng an toàn.")


def daily_job():
    print(f"[{datetime.now(VN_TZ).strftime('%H:%M:%S')}] Đang lấy dữ liệu Meta Ads...")
    try:
        date_start, date_stop = get_dates(1)
        report = build_report(date_start, date_stop, "Hôm qua")
        send_telegram_with_buttons(report)
        check_spending_alert()
        print("✅ Đã gửi báo cáo lên Telegram.")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        send_telegram(f"⚠️ <b>Meta Ads Bot lỗi</b>\n<code>{e}</code>")


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
                    report = build_report(date_start, date_stop, "7 ngày qua")
                elif data_val == "period_14":
                    date_start, date_stop = get_dates(14)
                    report = build_report(date_start, date_stop, "14 ngày qua")
                elif data_val == "period_month":
                    date_start, date_stop = get_dates(0)
                    report = build_report(date_start, date_stop, "Trong tháng")
                else:
                    continue

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
        report = build_report(date_start, date_stop, "7 ngày qua")
        send_telegram(report)

    elif period == "period_14":
        date_start, date_stop = get_dates(14)
        report = build_report(date_start, date_stop, "14 ngày qua")
        send_telegram(report)

    elif period == "period_month":
        date_start, date_stop = get_dates(0)
        report = build_report(date_start, date_stop, "Trong tháng")
        send_telegram(report)

    else:
        daily_job()
