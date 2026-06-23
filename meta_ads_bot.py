"""
Meta Ads → Telegram Daily Report Bot
Gửi báo cáo hằng ngày từ Meta Ads lên Telegram
"""

import os
import requests
import schedule
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIG ────────────────────────────────────────────────
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
AD_ACCOUNT_ID     = os.getenv("AD_ACCOUNT_ID")        # format: act_XXXXXXXXXX
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")
REPORT_TIME        = os.getenv("REPORT_TIME", "08:00") # giờ gửi báo cáo (HH:MM)

META_API_VERSION = "v21.0"
META_BASE_URL    = f"https://graph.facebook.com/{META_API_VERSION}"

# ─── META ADS API ───────────────────────────────────────────

def get_account_info():
    """Lấy tên tài khoản quảng cáo"""
    url = f"{META_BASE_URL}/{AD_ACCOUNT_ID}"
    params = {
        "fields": "name,currency",
        "access_token": META_ACCESS_TOKEN,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_insights(date_start: str, date_stop: str):
    """
    Lấy insights: spend, messaging_conversation_started_7d, purchases
    date_start / date_stop format: YYYY-MM-DD
    """
    url = f"{META_BASE_URL}/{AD_ACCOUNT_ID}/insights"
    params = {
        "fields": (
            "account_name,"
            "spend,"
            "actions,"
            "cost_per_action_type"
        ),
        "time_range": f'{{"since":"{date_start}","until":"{date_stop}"}}',
        "level": "account",
        "access_token": META_ACCESS_TOKEN,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return data[0] if data else {}


def extract_action(actions: list, action_type: str) -> int:
    """Trích xuất giá trị action theo type"""
    for a in actions or []:
        if a.get("action_type") == action_type:
            return int(float(a.get("value", 0)))
    return 0


def extract_cost_per_action(cost_list: list, action_type: str) -> float:
    """Trích xuất cost per action theo type"""
    for c in cost_list or []:
        if c.get("action_type") == action_type:
            return float(c.get("value", 0))
    return 0.0


def build_report(period_label: str = "Hôm qua") -> str:
    """Tổng hợp báo cáo thành chuỗi text"""
    yesterday = datetime.now() - timedelta(days=1)
    date_str  = yesterday.strftime("%Y-%m-%d")
    display   = yesterday.strftime("%d/%m/%Y")

    insights     = get_insights(date_str, date_str)
    account_info = get_account_info()

    account_name = account_info.get("name", "N/A")
    currency     = account_info.get("currency", "VND")
    spend        = float(insights.get("spend", 0))
    actions      = insights.get("actions", [])
    cost_per_act = insights.get("cost_per_action_type", [])

    # Tin nhắn mới – Meta dùng action type này cho Messenger/Instagram DM leads
    messages_new = extract_action(actions, "onsite_conversion.messaging_conversation_started_7d")
    if messages_new == 0:
        # fallback: messaging_first_reply hoặc messaging_welcome_message_view
        messages_new = extract_action(actions, "onsite_conversion.messaging_first_reply")

    cost_per_message = extract_cost_per_action(
        cost_per_act, "onsite_conversion.messaging_conversation_started_7d"
    )
    if cost_per_message == 0:
        cost_per_message = (spend / messages_new) if messages_new > 0 else 0

    purchases = extract_action(actions, "onsite_conversion.purchase")

    # Format số
    def fmt_currency(val):
        return f"{val:,.0f} {currency}"

    report = (
        f"📊 *BÁO CÁO META ADS – {display}*\n"
        f"{'─' * 32}\n"
        f"🏷️ *Tên tài khoản:* {account_name}\n"
        f"💸 *Tổng chi tiêu:* {fmt_currency(spend)}\n"
        f"💬 *Tin nhắn mới:* {messages_new:,}\n"
        f"💰 *Giá / tin nhắn mới:* {fmt_currency(cost_per_message)}\n"
        f"🛒 *Lượt mua:* {purchases:,}\n"
        f"{'─' * 32}\n"
        f"🕐 Cập nhật lúc {datetime.now().strftime('%H:%M')} | {display}"
    )
    return report


# ─── TELEGRAM ───────────────────────────────────────────────

def send_telegram(message: str):
    """Gửi tin nhắn lên Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ─── JOB ────────────────────────────────────────────────────

AD_ACCOUNTS = [
    os.getenv("AD_ACCOUNT_1"),
    os.getenv("AD_ACCOUNT_2"),
    os.getenv("AD_ACCOUNT_3"),
    os.getenv("AD_ACCOUNT_4"),
]

def daily_job():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Đang lấy dữ liệu Meta Ads...")
    date_display = (datetime.now() - timedelta(days=1)).strftime('%d/%m/%Y')
    full_report = (
        f"📊 *BÁO CÁO META ADS – {date_display}*\n"
        f"🕐 Cập nhật lúc {datetime.now().strftime('%H:%M')}\n"
        f"{'═' * 32}\n\n"
    )

    for i, account_id in enumerate(AD_ACCOUNTS, 1):
        if not account_id:
            continue
        try:
            global AD_ACCOUNT_ID
            AD_ACCOUNT_ID = account_id
            insights = get_insights(
                (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            )
            account_info = get_account_info()
            spend = float(insights.get("spend", 0))
            actions = insights.get("actions", [])
            cost_per_act = insights.get("cost_per_action_type", [])
            messages_new = extract_action(actions, "onsite_conversion.messaging_conversation_started_7d")
            if messages_new == 0:
                messages_new = extract_action(actions, "onsite_conversion.messaging_first_reply")
            cost_per_message = extract_cost_per_action(cost_per_act, "onsite_conversion.messaging_conversation_started_7d")
            if cost_per_message == 0:
                cost_per_message = (spend / messages_new) if messages_new > 0 else 0
            purchases = extract_action(actions, "onsite_conversion.purchase")
            currency = account_info.get("currency", "VND")

            full_report += (
                f"🏷️ *{account_info.get('name', f'Tài khoản {i}')}*\n"
                f"💸 Chi tiêu: {spend:,.0f} {currency}\n"
                f"💬 Tin nhắn mới: {messages_new:,}\n"
                f"💰 Giá/tin nhắn: {cost_per_message:,.0f} {currency}\n"
                f"🛒 Lượt mua: {purchases:,}\n"
                f"{'─' * 32}\n\n"
            )
        except Exception as e:
            full_report += f"❌ Tài khoản {i} lỗi: `{e}`\n\n"

    send_telegram(full_report)
    print("✅ Đã gửi báo cáo lên Telegram.")


# ─── MAIN ───────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"🤖 Meta Ads Bot khởi động – báo cáo lúc {REPORT_TIME} mỗi ngày")
    # Chạy ngay lần đầu để test
    daily_job()

    schedule.every().day.at(REPORT_TIME).do(daily_job)

    while True:
        schedule.run_pending()
        time.sleep(60)
