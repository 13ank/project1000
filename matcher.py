"""
matcher.py — จับคู่โปรไฟล์นักศึกษากับทุนที่เข้าเกณฑ์
ระบบแจ้งเตือนทุนการศึกษา มทส
"""

from datetime import datetime, date
from database import get_connection


def get_days_until_deadline(deadline_str):
    """คำนวณจำนวนวันที่เหลือก่อนหมดเขต"""
    try:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        today = date.today()
        return (deadline - today).days
    except Exception:
        return -9999


def is_student_eligible(student, scholarship):
    """
    ตรวจสอบว่านักศึกษาเข้าเกณฑ์ทุนนี้หรือไม่
    คืนค่า True/False
    """
    # เช็ค GPA
    if student["gpa"] < scholarship["min_gpa"]:
        return False

    # เช็คคณะ
    if scholarship["faculty"] != "ทุกคณะ":
        if student["faculty"] != scholarship["faculty"]:
            return False

    # เช็คระดับการศึกษา
    if scholarship["level"] != "ทุกระดับ":
        if student["level"] != scholarship["level"]:
            return False

    # เช็คสัญชาติ
    if scholarship["nationality"] != "ทุกสัญชาติ":
        if student["nationality"] != scholarship["nationality"]:
            return False

    return True


def already_notified(student_id, scholarship_id, notif_type):
    """ตรวจสอบว่าเคยส่งแจ้งเตือนประเภทนี้ไปแล้วหรือยัง"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM notifications
        WHERE student_id = ? AND scholarship_id = ? AND type = ?
    """, (student_id, scholarship_id, notif_type))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def log_notification(student_id, scholarship_id, notif_type, status="sent"):
    """บันทึก log การแจ้งเตือน"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO notifications (student_id, scholarship_id, type, status)
        VALUES (?, ?, ?, ?)
    """, (student_id, scholarship_id, notif_type, status))
    conn.commit()
    conn.close()


def get_active_scholarships():
    """ดึงทุนที่ยังเปิดรับอยู่ทั้งหมด"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM scholarships
        WHERE is_active = 1
        ORDER BY deadline ASC
    """)
    scholarships = cursor.fetchall()
    conn.close()
    return scholarships


def get_all_students():
    """ดึงรายชื่อนักศึกษาทั้งหมด"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()
    conn.close()
    return students


def find_matches():
    """
    หัวใจหลักของระบบ — จับคู่นักศึกษากับทุนที่เข้าเกณฑ์
    คืนค่า list ของ (student, scholarship, notif_type, days_left)
    """
    matches = []
    students = get_all_students()
    scholarships = get_active_scholarships()

    print(f"\n[Matcher] ตรวจสอบ {len(students)} นักศึกษา, {len(scholarships)} ทุน")
    print("-" * 50)

    for scholarship in scholarships:
        scholarship = dict(scholarship)
        days_left = get_days_until_deadline(scholarship["deadline"])

        # ข้ามทุนที่หมดเขตแล้ว
        if days_left < 0:
            print(f"  [หมดเขต] {scholarship['title']}")
            continue

        # กำหนดประเภทการแจ้งเตือนตามวันที่เหลือ
        if days_left <= 1:
            notif_type = "1day"
        elif days_left <= 7:
            notif_type = "7days"
        elif days_left <= 30:
            notif_type = "30days"
        else:
            notif_type = None  # ยังไม่ถึงเวลาแจ้งเตือน

        if notif_type is None:
            print(f"  [ยังไม่ถึงเวลา] {scholarship['title']} (เหลือ {days_left} วัน)")
            continue

        print(f"\n  [ทุน] {scholarship['title']} — เหลือ {days_left} วัน ({notif_type})")

        for student in students:
            student = dict(student)

            if is_student_eligible(student, scholarship):
                # ตรวจว่าเคยส่งแล้วหรือยัง
                if not already_notified(student["id"], scholarship["id"], notif_type):
                    matches.append({
                        "student": student,
                        "scholarship": scholarship,
                        "notif_type": notif_type,
                        "days_left": days_left
                    })
                    print(f"    ✓ {student['name']} ({student['email']}) — เข้าเกณฑ์")
                else:
                    print(f"    - {student['name']} — เคยแจ้งเตือนแล้ว")
            else:
                print(f"    ✗ {student['name']} — ไม่เข้าเกณฑ์")

    print(f"\n[Matcher] พบ {len(matches)} คู่ที่ต้องแจ้งเตือน")
    return matches


def find_matches_for_scholarship(scholarship_id):
    """
    จับคู่นักศึกษากับทุนใหม่ 1 รายการ
    ใช้ตอน scraper เจอทุนใหม่ แล้วอยากแจ้งทันที
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM scholarships
        WHERE id = ? AND is_active = 1
    """, (scholarship_id,))
    scholarship = cursor.fetchone()

    if not scholarship:
        conn.close()
        return []

    scholarship = dict(scholarship)

    # ข้ามทุนที่หมดเขตแล้ว
    days_left = get_days_until_deadline(scholarship["deadline"])
    if days_left < 0:
        conn.close()
        return []

    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()
    conn.close()

    matches = []

    print(f"\n[Matcher] ตรวจทุนใหม่: {scholarship['title']}")

    for student in students:
        student = dict(student)

        if is_student_eligible(student, scholarship):
            notif_type = "new"

            # กันส่งซ้ำ
            if not already_notified(student["id"], scholarship["id"], notif_type):
                matches.append({
                    "student": student,
                    "scholarship": scholarship,
                    "notif_type": notif_type,
                    "days_left": days_left
                })
                print(f"  ✓ {student['name']} ({student['email']})")
            else:
                print(f"  - {student['name']} เคยแจ้งแล้ว")
        else:
            print(f"  ✗ {student['name']} ไม่เข้าเกณฑ์")

    print(f"[Matcher] พบ {len(matches)} คนที่ต้องแจ้งสำหรับทุนนี้")
    return matches


if __name__ == "__main__":
    from database import init_db, seed_data

    init_db()
    seed_data()

    matches = find_matches()

    print("\n=== ผลการจับคู่ ===")
    for m in matches:
        print(f"  {m['student']['name']} ← {m['scholarship']['title']} ({m['notif_type']})")