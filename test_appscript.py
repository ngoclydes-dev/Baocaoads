import os
import requests
import json

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

# Goi truc tiep Apps Script de xem raw headers
# Them endpoint debug vao Apps Script tam thoi
resp = requests.get(APPS_SCRIPT_URL, timeout=30)
data = resp.json()

livechat = data.get("livechat", [])
if livechat:
    print("=== TAT CA KEYS TRONG 1 DONG LIVECHAT ===")
    print(json.dumps(list(livechat[5].keys()), ensure_ascii=False, indent=2))
    print()
    print("=== DONG CO PH2L ===")
    for i, row in enumerate(livechat):
        if row.get("Ghi chu") == "PH2L" or row.get("Ghi chú") == "PH2L":
            print(f"Dong {i+1}:", json.dumps(row, ensure_ascii=False))
            break
