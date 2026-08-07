import os
import requests
import json

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

resp = requests.get(APPS_SCRIPT_URL, timeout=60)
data = resp.json()

livechat = data.get("livechat", [])
print(f"Livechat rows: {len(livechat)}")
print(f"Livechat sheet: {data.get('livechatSheetName')}")

if livechat:
    print("\nMau dong dau:")
    print(json.dumps(livechat[0], ensure_ascii=False, indent=2))

    # Tim dong co PH2L
    ph2l = [r for r in livechat if
            r.get("CHẤT LƯỢNG MESS") == "PH2L" or
            r.get("Ghi chú") == "PH2L" or
            r.get("GHI CHÚ") == "PH2L"]
    print(f"\nSo dong PH2L: {len(ph2l)}")
    if ph2l:
        print("Mau dong PH2L dau tien:")
        print(json.dumps(ph2l[0], ensure_ascii=False, indent=2))
