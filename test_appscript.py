import os
import requests
import json

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

resp = requests.get(APPS_SCRIPT_URL, timeout=30)
data = resp.json()

livechat = data.get("livechat", [])
print(f"Tong rows: {len(livechat)}")
print()

# In 10 dong dau de xem cau truc
for i, row in enumerate(livechat[:10]):
    print(f"=== Dong {i+1} ===")
    print(json.dumps(row, indent=2, ensure_ascii=False))
    print()
