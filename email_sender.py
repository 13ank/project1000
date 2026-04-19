"""
email_sender.py — ส่ง Email แจ้งเตือนทุนการศึกษาผ่าน SMTP
ระบบแจ้งเตือนทุนการศึกษา มทส

Network Programming ที่ใช้:
  - TCP Connection  : เชื่อมต่อ SMTP Server ที่ port 587
  - TLS Handshake   : เข้ารหัสการส่งข้อมูลด้วย starttls()
  - SMTP Protocol   : ส่ง Email ตามมาตรฐาน RFC 5321
  - Multi-threading : ส่งหลาย Email พร้อมกัน
"""

import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ─── ตั้งค่า SMTP ─────────────────────────────────────
SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587          # Port สำหรับ TLS
SENDER_EMAIL  = "swkspr@gmail.com"   # เปลี่ยนเป็นอีเมลจริง
SENDER_PASS   = "fvlk fncn lwee rtit"      # App Password จาก Google

# ─── Templates อีเมล ─────────────────────────────────
EMAIL_TEMPLATES = {
    "new": {
        "subject": "[ทุนใหม่] {title} เปิดรับสมัครแล้ว!",
        "urgency": "มีทุนการศึกษาใหม่ที่ตรงกับโปรไฟล์ของคุณ",
        "color": "#2e7d32"
    },
    "30days": {
        "subject": "[แจ้งเตือน] {title} — เหลืออีก 30 วัน",
        "urgency": "ทุนนี้กำลังจะหมดเขตใน 30 วัน อย่าลืมเตรียมเอกสาร",
        "color": "#1565c0"
    },
    "7days": {
        "subject": "[ด่วน] {title} — เหลืออีกเพียง 7 วัน!",
        "urgency": "เหลือเวลาอีกเพียง 7 วันเท่านั้น รีบสมัครด่วน!",
        "color": "#e65100"
    },
    "1day": {
        "subject": "[ด่วนมาก!] {title} — พรุ่งนี้หมดเขตแล้ว!",
        "urgency": "พรุ่งนี้คือวันสุดท้าย! สมัครได้เลยทันที",
        "color": "#b71c1c"
    }
}

def build_email_html(student_name, scholarship, notif_type, days_left):
    """สร้าง HTML Email ที่สวยงาม"""
    template = EMAIL_TEMPLATES[notif_type]
    title = scholarship["title"]
    deadline = scholarship["deadline"]
    amount = f"{scholarship['amount']:,.0f}" if scholarship["amount"] else "ไม่ระบุ"
    apply_url = scholarship.get("apply_url", "#")
    color = template["color"]
    urgency = template["urgency"]

    html = f"""
    <html>
    <body style="font-family: Sarabun, Arial, sans-serif; background:#f5f5f5; padding:20px;">
      <div style="max-width:600px; margin:0 auto; background:#fff; border-radius:8px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.1);">

        <!-- Header -->
        <div style="background:{color}; padding:24px; text-align:center;">
          <h1 style="color:#fff; margin:0; font-size:20px;">🎓 ScholarPath มทส</h1>
          <p style="color:rgba(255,255,255,0.85); margin:8px 0 0; font-size:14px;">ระบบแจ้งเตือนทุนการศึกษา</p>
        </div>

        <!-- Body -->
        <div style="padding:28px;">
          <p style="font-size:16px; color:#333;">สวัสดีครับ/ค่ะ คุณ <strong>{student_name}</strong></p>
          <p style="color:#555; font-size:15px;">{urgency}</p>

          <!-- Scholarship Card -->
          <div style="border:2px solid {color}; border-radius:6px; padding:20px; margin:20px 0;">
            <h2 style="color:{color}; margin:0 0 12px; font-size:18px;">{title}</h2>
            <table style="width:100%; font-size:14px; color:#555;">
              <tr>
                <td style="padding:4px 0;"><strong> จำนวนทุน:</strong></td>
                <td>{amount} บาท/เดือน</td>
              </tr>
              <tr>
                <td style="padding:4px 0;"><strong> หมดเขต:</strong></td>
                <td style="color:{color};"><strong>{deadline}</strong>
                  {"(พรุ่งนี้!)" if days_left <= 1 else f"(อีก {days_left} วัน)"}
                </td>
              </tr>
              <tr>
                <td style="padding:4px 0;"><strong> แหล่งทุน:</strong></td>
                <td>{scholarship.get('source', 'มทส')}</td>
              </tr>
              <tr>
                <td style="padding:4px 0;"><strong> ระดับ:</strong></td>
                <td>{scholarship.get('level', 'ทุกระดับ')}</td>
              </tr>
            </table>
          </div>

          <!-- CTA Button -->
          <div style="text-align:center; margin:24px 0;">
            <a href="{apply_url}"
               style="background:{color}; color:#fff; padding:12px 32px; border-radius:4px;
                      text-decoration:none; font-size:15px; font-weight:bold; display:inline-block;">
               สมัครทุนนี้เลย
            </a>
          </div>

          <p style="font-size:12px; color:#999; text-align:center; margin-top:24px;">
            อีเมลนี้ส่งโดยอัตโนมัติจากระบบ ScholarPath มทส<br>
            หากต้องการยกเลิกการแจ้งเตือน กรุณาเข้าไปที่ตั้งค่าบัญชีของคุณ
          </p>
        </div>

      </div>
    </body>
    </html>
    """
    return html

def send_single_email(student, scholarship, notif_type, days_left):
    """
    ส่ง Email หานักศึกษา 1 คน
    ใช้ SMTP Protocol ผ่าน TCP + TLS
    """
    template = EMAIL_TEMPLATES[notif_type]
    subject = template["subject"].format(title=scholarship["title"])
    recipient = student["email"]
    name = student["name"]

    # สร้าง Email Message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"ScholarPath มทส <{SENDER_EMAIL}>"
    msg["To"]      = recipient

    # แนบ HTML
    html_body = build_email_html(name, scholarship, notif_type, days_left)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        # ── Network Programming เริ่มตรงนี้ ──────────────────
        print(f"    [SMTP] กำลังเชื่อมต่อ {SMTP_HOST}:{SMTP_PORT} (TCP)...")
        smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT)   # 1. TCP Connection

        smtp.ehlo()                                  # 2. ทักทาย SMTP Server
        smtp.starttls()                              # 3. TLS Handshake (เข้ารหัส)
        smtp.ehlo()                                  # 4. ทักทายอีกครั้งหลัง TLS

        smtp.login(SENDER_EMAIL, SENDER_PASS)        # 5. Authentication
        smtp.sendmail(SENDER_EMAIL, recipient,       # 6. ส่ง Email
                      msg.as_string())
        smtp.quit()                                  # 7. ปิด Connection
        # ──────────────────────────────────────────────────────

        print(f"    [✓] ส่งสำเร็จ → {recipient}")
        return True

    except smtplib.SMTPAuthenticationError:
        print(f"    [✗] Authentication ล้มเหลว — ตรวจสอบ Email/Password")
        return False
    except smtplib.SMTPException as e:
        print(f"    [✗] SMTP Error: {e}")
        return False
    except Exception as e:
        print(f"    [✗] Error: {e}")
        return False

def send_bulk_emails(matches, log_func=None):
    """
    ส่ง Email หาหลายคนพร้อมกัน โดยใช้ Multi-threading
    แต่ละ Thread จัดการ TCP Connection ของตัวเอง
    """
    if not matches:
        print("[Email] ไม่มี Email ที่ต้องส่ง")
        return

    print(f"\n[Email] เริ่มส่ง {len(matches)} Email พร้อมกัน (Multi-threading)")
    print("=" * 50)

    threads = []
    results = {}

    def send_and_log(match, index):
        student     = match["student"]
        scholarship = match["scholarship"]
        notif_type  = match["notif_type"]
        days_left   = match["days_left"]

        print(f"\n  [Thread-{index}] ส่งให้ {student['name']}")
        success = send_single_email(student, scholarship, notif_type, days_left)
        results[index] = success

        # บันทึก log
        if log_func:
            status = "sent" if success else "failed"
            log_func(student["id"], scholarship["id"], notif_type, status)

    # สร้าง Thread สำหรับแต่ละ Email
    for i, match in enumerate(matches):
        t = threading.Thread(target=send_and_log, args=(match, i+1))
        threads.append(t)
        t.start()

    # รอทุก Thread เสร็จ
    for t in threads:
        t.join()

    success_count = sum(1 for v in results.values() if v)
    print(f"\n[Email] สรุป: ส่งสำเร็จ {success_count}/{len(matches)}")
    print("=" * 50)

if __name__ == "__main__":
    # ทดสอบส่ง Email
    test_student = {
        "id": 1,
        "name": "สมชาย ใจดี",
        "email": "test@example.com"
    }
    test_scholarship = {
        "title": "ทุนเรียนดี มทส",
        "amount": 15000,
        "deadline": "2025-03-15",
        "source": "มทส",
        "level": "ปริญญาตรี",
        "apply_url": "https://sut.ac.th/scholarship"
    }
    send_single_email(test_student, test_scholarship, "7days", 7)
