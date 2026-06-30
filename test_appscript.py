import os
import requests

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

print("=== KIỂM TRA APPS_SCRIPT_URL ===")
print(f"Giá trị URL: {APPS_SCRIPT_URL}")
print(f"Độ dài chuỗi: {len(APPS_SCRIPT_URL) if APPS_SCRIPT_URL else 0}")
print()

if not APPS_SCRIPT_URL:
    print("❌ APPS_SCRIPT_URL đang RỖNG - secret chưa được set hoặc tên sai")
else:
    try:
        resp = requests.get(APPS_SCRIPT_URL, timeout=30)
        print(f"Status code: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('Content-Type')}")
        print()
        print("=== RESPONSE TEXT (1000 ký tự đầu) ===")
        print(resp.text[:1000])
        print()

        try:
            data = resp.json()
            print("=== PARSE JSON THÀNH CÔNG ===")
            print("Các key cấp cao nhất:", list(data.keys()))
            print("Số dòng data:", len(data.get("data", [])))
        except Exception as e:
            print(f"❌ KHÔNG parse được JSON: {e}")

    except Exception as e:
        print(f"❌ Lỗi khi gọi request: {e}")
