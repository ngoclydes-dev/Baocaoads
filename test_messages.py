import os
import requests
from datetime import datetime, timedelta, timezone

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
META_API_VERSION = "v21.0"
META_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"
VN_TZ = timezone(timedelta(hours=7))

AD_ACCOUNTS = {
    "AD_ACCOUNT_1": os.getenv("AD_ACCOUNT_1"),
    "AD_ACCOUNT_2": os.getenv("AD_ACCOUNT_2"),
    "AD_ACCOUNT_3": os.getenv("AD_ACCOUNT_3"),
}


def get_account_name(account_id):
    url = f"{META_BASE_URL}/{account_id}"
    params = {"fields": "name", "access_token": META_ACCESS_TOKEN}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("name", account_id)


def get_insights(account_id, date_start, date_stop):
    url = f"{META_BASE_URL}/{account_id}/insights"
    params = {
        "fields": "spend,actions",
        "time_range": f'{{"since":"{date_start}","until":"{date_stop}"}}',
        "level": "account",
        "access_token": META_ACCESS_TOKEN,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return data[0] if data else {}


def extract_action(actions, action_type):
    for a in actions or []:
        if a.get("action_type") == action_type:
            return int(float(a.get("value", 0)))
    return 0


if __name__ == "__main__":
    # Đổi ngày này thành ngày bạn muốn so sánh với Ads Manager
    date_check = "2026-06-27"

    print(f"Kiểm tra ngày: {date_check}\n")

    for env_name, account_id in AD_ACCOUNTS.items():
        if not account_id:
            print(f"{env_name}: KHÔNG có giá trị\n")
            continue

        try:
            name = get_account_name(account_id)
            insight = get_insights(account_id, date_check, date_check)
            actions = insight.get("actions", [])

            first_reply = extract_action(actions, "onsite_conversion.messaging_first_reply")
            conv_started = extract_action(actions, "onsite_conversion.messaging_conversation_started_7d")
            conv_replied = extract_action(actions, "onsite_conversion.messaging_conversation_replied_7d")
            total_conn = extract_action(actions, "onsite_conversion.total_messaging_connection")

            print(f"--- {name} ({env_name}) ---")
            print(f"  messaging_first_reply:              {first_reply}")
            print(f"  messaging_conversation_started_7d:  {conv_started}")
            print(f"  messaging_conversation_replied_7d:  {conv_replied}")
            print(f"  total_messaging_connection:         {total_conn}")
            print()
        except Exception as e:
            print(f"{env_name}: LỖI - {e}\n")
