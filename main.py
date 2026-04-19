"""
main.py — จุดเริ่มต้นของระบบแจ้งเตือนทุนการศึกษา มทส
รันไฟล์นี้เพื่อเริ่มระบบทั้งหมด
"""

from database import init_db, seed_data
from matcher import find_matches
from email_sender import send_bulk_emails
from matcher import log_notification

def main():
    print("=" * 55)
    print("  🎓 ScholarPath — ระบบแจ้งเตือนทุนการศึกษา มทส")
    print("=" * 55)

    # 1. เตรียม Database
    print("\n[1] เตรียมฐานข้อมูล...")
    init_db()
    seed_data()

    # 2. จับคู่นักศึกษากับทุน
    print("\n[2] ตรวจสอบและจับคู่...")
    matches = find_matches()

    # 3. ส่ง Email
    print("\n[3] ส่ง Email แจ้งเตือน...")
    if matches:
        send_bulk_emails(matches, log_func=log_notification)
    else:
        print("  ไม่มีการแจ้งเตือนในขณะนี้")

    print("\n✅ ระบบทำงานเสร็จสิ้น")
    print("=" * 55)
    print("\nหมายเหตุ: แก้ไข SENDER_EMAIL และ SENDER_PASS")
    print("ใน email_sender.py ก่อนใช้งานจริง")

if __name__ == "__main__":
    main()
