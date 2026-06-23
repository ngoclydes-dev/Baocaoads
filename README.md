# 📊 Meta Ads → Telegram Daily Report Bot

Bot tự động lấy dữ liệu Meta Ads và gửi báo cáo hằng ngày lên Telegram.

## Thông tin báo cáo

| Chỉ số | Mô tả |
|---|---|
| 🏷️ Tên tài khoản | Tên tài khoản quảng cáo Meta |
| 💸 Tổng chi tiêu | Chi phí trong ngày hôm qua |
| 💬 Tin nhắn mới | Số cuộc hội thoại mới (Messenger/DM) |
| 💰 Giá / tin nhắn mới | Chi phí trung bình mỗi tin nhắn |
| 🛒 Lượt mua | Số lượng purchase được ghi nhận |

---

## Hướng dẫn cài đặt

### 1. Lấy Meta Access Token

1. Truy cập [Meta for Developers](https://developers.facebook.com/tools/explorer/)
2. Chọn ứng dụng của bạn (hoặc tạo app mới loại **Business**)
3. Thêm quyền: `ads_read`, `ads_management`, `business_management`
4. Nhấn **Generate Access Token**
5. Để token không hết hạn → dùng **Long-lived token** hoặc **System User Token** (khuyến nghị)

> **Lấy System User Token (không hết hạn):**  
> Meta Business Suite → Cài đặt → Người dùng hệ thống → Thêm người dùng hệ thống → Tạo token

### 2. Lấy Ad Account ID

1. Vào [Meta Ads Manager](https://business.facebook.com/adsmanager)
2. URL sẽ có dạng: `?act=123456789` → ID của bạn là `act_123456789`
3. Hoặc vào **Cài đặt tài khoản** → **Thông tin tài khoản**

### 3. Tạo Telegram Bot

```
1. Nhắn /newbot cho @BotFather trên Telegram
2. Đặt tên và username cho bot
3. Lưu lại token dạng: 123456789:ABCxxxxx
```

### 4. Lấy Telegram Chat ID

**Chat cá nhân:**
```
Nhắn tin cho @userinfobot → nó sẽ trả về your_id
```

**Group/Channel:**
```
1. Thêm bot vào group
2. Gửi 1 tin nhắn bất kỳ trong group
3. Mở trình duyệt: https://api.telegram.org/bot<TOKEN>/getUpdates
4. Tìm "chat":{"id": -1001234567890} → đó là group_id
```

### 5. Cài đặt và chạy

```bash
# Clone / tải code về
cd meta_ads_bot

# Cài dependencies
pip install -r requirements.txt

# Copy file cấu hình
cp .env.example .env

# Chỉnh sửa .env với thông tin của bạn
nano .env

# Chạy bot
python meta_ads_bot.py
```

### 6. Test ngay (không chờ đến giờ hẹn)

Mở file `meta_ads_bot.py`, bỏ comment dòng `daily_job()`:

```python
if __name__ == "__main__":
    daily_job()  # ← bỏ comment dòng này để test
    ...
```

---

## Chạy nền với systemd (Linux/VPS)

Tạo file `/etc/systemd/system/meta-ads-bot.service`:

```ini
[Unit]
Description=Meta Ads Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/meta_ads_bot
ExecStart=/usr/bin/python3 /home/ubuntu/meta_ads_bot/meta_ads_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable meta-ads-bot
sudo systemctl start meta-ads-bot
sudo systemctl status meta-ads-bot
```

## Chạy nền với PM2 (Node.js ecosystem)

```bash
pip install pm2  # hoặc npm install -g pm2
pm2 start meta_ads_bot.py --interpreter python3 --name meta-ads-bot
pm2 save
pm2 startup
```

---

## Ví dụ tin nhắn Telegram

```
📊 BÁO CÁO META ADS – 22/06/2025
────────────────────────────────
🏷️ Tên tài khoản: Công ty ABC
💸 Tổng chi tiêu: 1,250,000 VND
💬 Tin nhắn mới: 47
💰 Giá / tin nhắn mới: 26,596 VND
🛒 Lượt mua: 12
────────────────────────────────
🕐 Cập nhật lúc 08:00 | 22/06/2025
```

---

## Lưu ý về Action Types

Meta Ads dùng các action type sau cho tin nhắn:
- `onsite_conversion.messaging_conversation_started_7d` – tin nhắn mới (chính)
- `onsite_conversion.messaging_first_reply` – phản hồi đầu tiên (fallback)

Nếu chiến dịch của bạn dùng objective khác, kiểm tra action type thực tế bằng cách gọi:

```python
# Debug: in toàn bộ actions
insights = get_insights("2025-06-21", "2025-06-21")
print(insights.get("actions", []))
```
