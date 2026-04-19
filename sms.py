# sms.py
# ระบบส่ง SMS สำหรับเว็บ Flask

from twilio.rest import Client

# =========================
# ใส่ข้อมูลจาก Twilio
# =========================

ACCOUNT_SID = "YOUR_ACCOUNT_SID"
AUTH_TOKEN = "YOUR_AUTH_TOKEN"
TWILIO_PHONE = "YOUR_TWILIO_PHONE_NUMBER"

# =========================
# สร้าง client
# =========================

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# =========================
# ฟังก์ชันส่ง SMS
# =========================

def send_sms(phone_number, message):
    try:
        message = client.messages.create(
            body=message,
            from_=TWILIO_PHONE,
            to=phone_number
        )

        print("SMS sent:", message.sid)
        return True

    except Exception as e:
        print("SMS error:", e)
        return False
