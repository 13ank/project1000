"""
database.py — โมเดลข้อมูลและการเชื่อมต่อ Database
ระบบแจ้งเตือนทุนการศึกษา มทส
"""

import sqlite3
from datetime import datetime

DB_NAME = "scholarships.db"

# สำนักวิชาทั้งหมดของ มทส
FACULTIES = [
    "วิทยาศาสตร์",
    "เทคโนโลยีสังคม",
    "เทคโนโลยีการเกษตร",
    "แพทยศาสตร์",
    "พยาบาลศาสตร์",
    "วิศวกรรมศาสตร์",
    "ทันตแพทยศาสตร์",
    "สาธารณสุขศาสตร์",
    "ศาสตร์และศิลป์ดิจิทัล",
]


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # ตาราง นักศึกษา
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            email       TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            phone       TEXT,
            gpa         REAL DEFAULT 0.0,
            faculty     TEXT,
            level       TEXT,  -- ปริญญาตรี, โท, เอก
            nationality TEXT DEFAULT 'ไทย',
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    # ตาราง ทุนการศึกษา
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scholarships (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT NOT NULL,
            description  TEXT,
            source       TEXT,
            amount       REAL,
            min_gpa      REAL DEFAULT 0.0,
            faculty      TEXT DEFAULT 'ทุกคณะ',
            level        TEXT DEFAULT 'ทุกระดับ',
            nationality  TEXT DEFAULT 'ทุกสัญชาติ',
            deadline     TEXT NOT NULL,
            apply_url    TEXT,
            is_active    INTEGER DEFAULT 1,
            created_at   TEXT DEFAULT (datetime('now'))
        )
    """)

    # ตาราง การแจ้งเตือน (log)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id       INTEGER,
            scholarship_id   INTEGER,
            type             TEXT,  -- new, 30days, 7days, 1day
            sent_at          TEXT DEFAULT (datetime('now')),
            status           TEXT DEFAULT 'sent',
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (scholarship_id) REFERENCES scholarships(id)
        )
    """)

    # ตาราง Bookmark
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id     INTEGER,
            scholarship_id INTEGER,
            created_at     TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (scholarship_id) REFERENCES scholarships(id)
        )
    """)

    cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_scholarships_unique
    ON scholarships(title, deadline, apply_url)
""")

    try:
        cursor.execute("ALTER TABLE students ADD COLUMN phone TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()
    print("[DB] สร้างฐานข้อมูลสำเร็จ")


def seed_data():
    """ข้อมูลตัวอย่างสำหรับทดสอบ"""
    conn = get_connection()
    cursor = conn.cursor()

    # ── นักศึกษาตัวอย่าง (ครบทุกสำนักวิชา) ──────────────────────────
    students = [
        ("ไอคอน เล็กมาก",       "zeedzadroleplay6@gmail.com", "1234", 4.00, "วิศวกรรมศาสตร์",        "ปริญญาโท",  "ไทย"),
        ("สมหญิง รักเรียน",      "somying@sut.ac.th",          "1234", 3.75, "วิทยาศาสตร์",           "ปริญญาโท",  "ไทย"),
        ("John Smith",           "john@sut.ac.th",             "1234", 3.20, "ศาสตร์และศิลป์ดิจิทัล", "ปริญญาตรี", "ต่างชาติ"),
        ("น้องสายน้ำ น่ารักมาก", "sainamthanaporn@gmail.com",  "1234", 3.50, "วิศวกรรมศาสตร์",        "ปริญญาตรี", "ไทย"),
        ("นายออม สมเยส",         "smyenthnathip@gmail.com",    "1234", 3.50, "วิทยาศาสตร์",           "ปริญญาตรี", "ไทย"),
        ("นางสาวมินท์ ใจดี",     "mint@sut.ac.th",             "1234", 3.10, "แพทยศาสตร์",            "ปริญญาตรี", "ไทย"),
        ("นายเกษม ทำนา",         "kasem@sut.ac.th",            "1234", 2.80, "เทคโนโลยีการเกษตร",     "ปริญญาตรี", "ไทย"),
        ("นางสาวพิม สุขสันต์",   "pim@sut.ac.th",              "1234", 3.60, "พยาบาลศาสตร์",          "ปริญญาตรี", "ไทย"),
        ("นายบอล สังคมดี",       "ball@sut.ac.th",             "1234", 3.20, "เทคโนโลยีสังคม",        "ปริญญาตรี", "ไทย"),
        ("นางสาวฟ้า สาธารณะ",    "fah@sut.ac.th",              "1234", 3.40, "สาธารณสุขศาสตร์",       "ปริญญาตรี", "ไทย"),
        ("นายปาล์ม ฟันดี",       "palm@sut.ac.th",             "1234", 3.30, "ทันตแพทยศาสตร์",        "ปริญญาตรี", "ไทย"),
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO students (name, email, password, gpa, faculty, level, nationality)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, students)

    # ── ทุนการศึกษาตัวอย่าง ──────────────────────────────────────
    scholarships = [
        (
            "ทุนยกเว้นค่าเล่าเรียน มทส",
            "ทุนยกเว้นค่าเล่าเรียนสำหรับนักศึกษาที่มีผลการเรียนดีและขาดแคลนทุนทรัพย์ "
            "พิจารณาจาก GPA และฐานะทางการเงินของครอบครัว",
            "มทส", 15000, 3.00, "ทุกคณะ", "ปริญญาตรี", "ไทย",
            "2026-04-30", "https://scholarship.sut.ac.th",
        ),
        (
            "กองทุนการศึกษา มทส (เงินให้เปล่า)",
            "จัดสรรจากเงินดอกเบี้ยของกองทุน เป็นเงินให้เปล่า สำหรับนักศึกษาที่ขาดแคลนทุนทรัพย์ "
            "ไม่มีข้อผูกพันในการชำระคืน",
            "มทส", 10000, 2.00, "ทุกคณะ", "ปริญญาตรี", "ไทย",
            "2026-05-31", "https://scholarship.sut.ac.th",
        ),
        (
            "กองทุนช่วยค่าครองชีพ มทส",
            "เงินช่วยเหลือค่าครองชีพสำหรับนักศึกษาที่ขาดแคลนทุนทรัพย์ "
            "ไม่เกิน 3,000 บาท/ภาคการศึกษา",
            "มทส", 3000, 2.00, "ทุกคณะ", "ปริญญาตรี", "ไทย",
            "2026-03-31", "https://scholarship.sut.ac.th",
        ),
        (
            "กองทุนกู้ยืมเพื่อการศึกษา (กยศ.) มทส",
            "ให้ยืมค่าเล่าเรียนและค่าครองชีพ ไม่เกิน 15,000 บาท/ภาคการศึกษา "
            "ชำระคืนเมื่อสำเร็จการศึกษาและมีงานทำ",
            "มทส / รัฐบาล", 15000, 2.00, "ทุกคณะ", "ปริญญาตรี", "ไทย",
            "2026-06-30", "https://scholarship.sut.ac.th",
        ),
        (
            "เงินยืมฉุกเฉิน มทส",
            "สำหรับนักศึกษาที่ขาดแคลนทุนทรัพย์กะทันหัน ไม่เกิน 5,000 บาท/ภาค "
            "ชำระคืนก่อนสอบปลายภาค",
            "มทส", 5000, 2.00, "ทุกคณะ", "ทุกระดับ", "ไทย",
            "2026-12-31", "https://scholarship.sut.ac.th/emergency-loan",
        ),
        (
            "ทุนการศึกษาหลวงพ่อคูณ ปริสุทโธ",
            "ทุนจากดอกผลกองทุนหลวงพ่อคูณ ปริสุทโธ สำหรับนักศึกษาที่ขาดแคลนทุนทรัพย์ "
            "และมีความประพฤติดี",
            "มูลนิธิหลวงพ่อคูณ", 10000, 2.50, "ทุกคณะ", "ปริญญาตรี", "ไทย",
            "2026-05-15", "https://scholarship.sut.ac.th/luangpho-khoon",
        ),
        (
            "ทุนองค์กรภายนอก มทส",
            "ทุนให้เปล่าจากมูลนิธิ บริษัท ห้างร้านภายนอก มูลค่า 2,000–60,000 บาท "
            "กว่า 189 ทุน/ปี ประกาศทุนตลอดทั้งปี",
            "องค์กรภายนอก", 30000, 2.50, "ทุกคณะ", "ปริญญาตรี", "ไทย",
            "2026-04-30", "https://scholarship.sut.ac.th/external",
        ),
        (
            "ทุน สควค. ครูวิทยาศาสตร์-คณิตศาสตร์ (ตรี-โท 6 ปี)",
            "ทุนเรียนฟรี 6 ปี ต่อเนื่องปริญญาตรี-โท สาขาคณิตศาสตร์ ฟิสิกส์ เคมี ชีววิทยา "
            "จำนวน 10 ทุน GPAX ไม่ต่ำกว่า 3.00",
            "สควค. / มทส", 0, 3.00, "วิทยาศาสตร์", "ปริญญาตรี", "ไทย",
            "2026-04-30", "https://scholarship.sut.ac.th/science-teacher",
        ),
        (
            "ทุนบัณฑิตศึกษา มทส (RA/TA)",
            "ทุนผู้ช่วยวิจัย (RA) และผู้ช่วยสอน (TA) สำหรับนักศึกษาระดับบัณฑิตศึกษา "
            "ได้รับค่าตอบแทนรายเดือน พร้อมยกเว้นค่าเล่าเรียน",
            "มทส", 8000, 3.25, "ทุกคณะ", "ปริญญาโท", "ไทย",
            "2026-05-31", "https://scholarship.sut.ac.th/ra-ta",
        ),
        (
            "ทุนนักศึกษาต่างชาติ มทส (ASEAN)",
            "ทุนสำหรับนักศึกษาต่างชาติในกลุ่ม ASEAN ที่มีผลการเรียนดีเยี่ยม "
            "ครอบคลุมค่าเล่าเรียนและค่าที่พัก",
            "มทส", 20000, 3.00, "ทุกคณะ", "ปริญญาตรี", "ต่างชาติ",
            "2026-06-15", "https://scholarship.sut.ac.th/asean",
        ),
        (
            "ทุนวิจัยระดับปริญญาเอก มทส",
            "ทุนสนับสนุนการทำวิทยานิพนธ์ระดับปริญญาเอก ครอบคลุมค่าเล่าเรียนและค่าวิจัย "
            "ไม่เกิน 4 ปี",
            "มทส", 25000, 3.50, "ทุกคณะ", "ปริญญาเอก", "ทุกสัญชาติ",
            "2026-07-31", "https://scholarship.sut.ac.th/phd-research",
        ),
        (
            "ทุนความเป็นเลิศทางวิชาการ มทส",
            "สำหรับนักศึกษาที่มีผลการเรียนดีเด่น GPA ไม่ต่ำกว่า 3.75 ในปีการศึกษาที่ผ่านมา "
            "ทุนละ 20,000 บาท/ปี",
            "มทส", 20000, 3.75, "ทุกคณะ", "ปริญญาตรี", "ไทย",
            "2026-04-15", "https://scholarship.sut.ac.th/academic-excellence",
        ),
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO scholarships
        (title, description, source, amount, min_gpa, faculty, level, nationality, deadline, apply_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, scholarships)

    conn.commit()
    conn.close()
    print("[DB] เพิ่มข้อมูลตัวอย่างสำเร็จ")


def fix_invalid_deadlines():
    """
    แก้ deadline ที่ว่าง/ผิดรูปแบบ
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE scholarships
        SET deadline = date('now', '+30 day')
        WHERE deadline IS NULL
           OR trim(deadline) = ''
           OR length(deadline) != 10
    """)

    conn.commit()
    conn.close()
    print("[DB] แก้ deadline ที่ผิดรูปแบบแล้ว")


def clear_scraped_scholarships():
    """
    ลบทุนที่มาจากการ scrape เพื่อให้ดึงใหม่ได้
    ใช้ตอนข้อมูล deadline เก่าเพี้ยน
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM scholarships
        WHERE source = 'มทส'
          AND apply_url LIKE 'https://cia.sut.ac.th/%'
    """)

    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    print(f"[DB] ลบทุนจาก scraper แล้ว {deleted} รายการ")


def show_deadlines(limit=20):
    """
    ใช้เช็กข้อมูล deadline ใน DB
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, deadline, apply_url
        FROM scholarships
        ORDER BY deadline ASC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    print("\n[DB] ตัวอย่างข้อมูล deadline")
    print("-" * 80)
    for row in rows:
        print(f"{row['id']:>3} | {row['deadline']} | {row['title']}")
    print("-" * 80)


if __name__ == "__main__":
    init_db()
    seed_data()
    fix_invalid_deadlines()
    show_deadlines()