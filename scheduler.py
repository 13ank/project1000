"""
scheduler.py — ระบบตรวจสอบและส่งแจ้งเตือนอัตโนมัติทุกวัน
ระบบแจ้งเตือนทุนการศึกษา มทส
"""

import time
import threading
from datetime import datetime
from database import init_db, seed_data
from matcher import find_matches, log_notification
from email_sender import send_bulk_emails

def run_daily_check():
    """
    ฟังก์ชันหลัก — ทำงานทุกวัน
    1. หาคู่นักศึกษา-ทุนที่เข้าเกณฑ์
    2. ส่ง Email แจ้งเตือน
    3. บันทึก Log
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*55}")
    print(f"  ScholarPath — Daily Check [{now}]")
    print(f"{'='*55}")

    # จับคู่นักศึกษากับทุน
    matches = find_matches()

    if matches:
        # ส่ง Email พร้อมบันทึก Log
        send_bulk_emails(matches, log_func=log_notification)
    else:
        print("\n[Scheduler] ไม่มีการแจ้งเตือนวันนี้")

    print(f"\n[Scheduler] เสร็จสิ้น — รอรอบถัดไป...")

def start_scheduler(interval_seconds=86400):
    """
    เริ่ม Scheduler ทำงานทุก interval_seconds วินาที
    ค่าเริ่มต้น = 86400 วินาที = 24 ชั่วโมง

    สำหรับทดสอบ ส่ง interval_seconds=30 เพื่อรันทุก 30 วินาที
    """
    print(f"[Scheduler] เริ่มทำงาน — ตรวจสอบทุก {interval_seconds} วินาที")
    print(f"[Scheduler] กด Ctrl+C เพื่อหยุด\n")

    # รันครั้งแรกทันที
    run_daily_check()

    # วนรันตาม interval
    while True:
        time.sleep(interval_seconds)
        run_daily_check()

def start_scheduler_thread(interval_seconds=86400):
    """รัน Scheduler ใน Background Thread"""
    t = threading.Thread(
        target=start_scheduler,
        args=(interval_seconds,),
        daemon=True
    )
    t.start()
    print(f"[Scheduler] รันใน Background Thread แล้ว")
    return t

if __name__ == "__main__":
    # เตรียม Database
    init_db()
    seed_data()

    # รันทุก 30 วินาที (สำหรับทดสอบ)
    # เปลี่ยนเป็น 86400 ตอน deploy จริง
    try:
        start_scheduler(interval_seconds=86400)
    except KeyboardInterrupt:
        print("\n[Scheduler] หยุดทำงาน")
