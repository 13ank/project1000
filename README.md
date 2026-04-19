# 🎓 ScholarPath — ระบบแจ้งเตือนทุนการศึกษา มทส

> ระบบแจ้งเตือนทุนการศึกษาอัตโนมัติสำหรับนักศึกษามหาวิทยาลัยเทคโนโลยีสุรนารี  
> โปรเจควิชา **โครงงานการสื่อสารข้อมูลและเครือข่าย**

---

## 📌 ระบบทำอะไร?

ScholarPath ช่วยให้นักศึกษา มทส ไม่พลาดโอกาสรับทุนการศึกษา โดย

- ✅ แสดงทุนที่ **ตรงกับโปรไฟล์** ของนักศึกษา (GPA / คณะ / ระดับการศึกษา)
- ✅ ส่ง **Email แจ้งเตือนอัตโนมัติ** เมื่อทุนใกล้หมดเขต (30 / 7 / 1 วัน)
- ✅ รองรับการเชื่อมต่อแบบ **Real-time ผ่าน TCP Socket**
- ✅ เปิดให้เข้าจากอินเทอร์เน็ตได้จริงผ่าน **ngrok**

---


## 🌐 Network Programming ที่ใช้

| Protocol | ไฟล์ | Port | หน้าที่ |
|---|---|---|---|
| TCP Socket | `socket_server.py` | 9999 | Real-time notification |
| SMTP + TLS | `email_sender.py` | 587 | ส่ง Email แจ้งเตือน |
| HTTP/Flask | `app.py` | 5000 | Web Application |
| HTTPS/ngrok | ngrok | 443 | Public URL |
| HTTP Fetch | `scraper.py` | 80/443 | ดึงข้อมูลทุนจาก มทส |

---

## 📁 โครงสร้างไฟล์

```
project 1000/
│
├── app.py              # Flask Web Application (HTTP :5000)
├── database.py         # SQLite Database + ข้อมูลเริ่มต้น
├── matcher.py          # จับคู่ทุนกับนักศึกษา
├── email_sender.py     # ส่ง Email ผ่าน SMTP + TLS
├── scheduler.py        # ส่ง Email อัตโนมัติทุก 24 ชั่วโมง
├── socket_server.py    # TCP Server (port 9999)
├── socket_client.py    # TCP Client สำหรับนักศึกษา
├── sut_scraper.py      # ดึงข้อมูลทุนจาก scholarship.sut.ac.th
├── main.py             # รันระบบ Email ทั้งหมดในครั้งเดียว
│
├── templates/          # HTML Templates (Flask/Jinja2)
│   ├── base.html       # Layout หลัก + Navbar
│   ├── login.html      # หน้า Login
│   ├── register.html   # หน้าสมัครสมาชิก
│   ├── dashboard.html  # หน้าหลัก + สถิติ
│   ├── scholarships.html  # ทุนทั้งหมด + Filter
│   ├── profile.html    # แก้ไขข้อมูลส่วนตัว
│   └── bookmarks.html  # ทุนที่บันทึกไว้
│
└── scholarships.db     # SQLite Database (สร้างอัตโนมัติ)
```

---

## 🗄️ Database Schema

```sql
-- ข้อมูลนักศึกษา
CREATE TABLE students (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT,
    email       TEXT UNIQUE,
    password    TEXT,
    phone       TEXT,
    gpa         REAL,
    faculty     TEXT,   -- สำนักวิชา
    level       TEXT,   -- ปริญญาตรี / โท / เอก
    nationality TEXT,   -- ไทย / ต่างชาติ
    created_at  TEXT
)

-- ข้อมูลทุนการศึกษา
CREATE TABLE scholarships (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT,
    description TEXT,
    source      TEXT,
    amount      REAL,
    min_gpa     REAL,
    faculty     TEXT,
    level       TEXT,
    nationality TEXT,
    deadline    TEXT,
    apply_url   TEXT,
    is_active   INTEGER
)

-- log การแจ้งเตือน
CREATE TABLE notifications (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id     INTEGER,
    scholarship_id INTEGER,
    type           TEXT,   -- new / 30days / 7days / 1day
    sent_at        TEXT,
    status         TEXT    -- sent / failed
)

-- ทุนที่บันทึกไว้
CREATE TABLE bookmarks (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id     INTEGER,
    scholarship_id INTEGER,
    created_at     TEXT
)
```

---

## 🚀 วิธีติดตั้งและรัน

### 1. ติดตั้ง Python Libraries

```bash
pip install flask twilio
```

### 2. รัน Web Application

```bash
python app.py
```
เปิดเบราว์เซอร์ไปที่ `http://127.0.0.1:5000`

### 3. รัน TCP Socket Server (CMD แยก)

```bash
python socket_server.py
```

### 4. รัน TCP Client (CMD แยก)

```bash
python socket_client.py
```

### 5. รัน Scheduler อัตโนมัติ (CMD แยก)

```bash
python scheduler.py
```

### 6. เปิด Public URL ด้วย ngrok (CMD แยก)

```bash
ngrok config add-authtoken [YOUR_TOKEN]
ngrok http 5000
```

---

## 📡 REST API Endpoints

| Method | URL | หน้าที่ |
|---|---|---|
| GET | `/api/scholarships` | ดึงทุนทั้งหมด |
| GET | `/api/scholarships/<id>` | ดึงทุนรายการเดียว |
| GET | `/api/students/<id>/matches` | ทุนที่เข้าเกณฑ์ของนักศึกษา |
| GET | `/api/send-notifications` | ส่ง Email แจ้งเตือนทันที |
| POST | `/api/bookmark/<id>` | เพิ่ม / ลบ Bookmark |
| GET | `/api/bookmarks` | ดึง Bookmark ของนักศึกษา |

ตัวอย่างเรียก API ผ่านเบราว์เซอร์
```
http://127.0.0.1:5000/api/scholarships
http://127.0.0.1:5000/api/students/1/matches
```

---

## 💻 TCP Socket Client Commands

```
Login ด้วย Email แล้วใช้คำสั่งเหล่านี้

/scholarships   — ดูทุนที่เข้าเกณฑ์แบบ Real-time
/status         — ดูจำนวนนักศึกษาที่ Online อยู่
/quit           — ออกจากระบบ
```

---

## 👤 บัญชีทดสอบ

| ชื่อ | Email | Password | GPA | สำนักวิชา |
|---|---|---|---|---|
| ไอคอน เล็กมาก | zeedzadroleplay6@gmail.com | 1234 | 4.00 | วิศวกรรมศาสตร์ |
| สมหญิง รักเรียน | somying@sut.ac.th | 1234 | 3.75 | วิทยาศาสตร์ |
| John Smith | john@sut.ac.th | 1234 | 3.20 | ศาสตร์และศิลป์ดิจิทัล |
| น้องสายน้ำ | sainamthanaporn@gmail.com | 1234 | 3.50 | วิศวกรรมศาสตร์ |
| นายออม | smyenthnathip@gmail.com | 1234 | 3.50 | วิทยาศาสตร์ |

---

## ⚙️ ตั้งค่า Email Sender

เปิดไฟล์ `email_sender.py` แล้วแก้ไข

```python
SENDER_EMAIL = "your_gmail@gmail.com"
SENDER_PASS  = "xxxx xxxx xxxx xxxx"  # App Password 16 หลัก
```

วิธีสร้าง App Password
1. เปิด Google Account → Security
2. เปิด 2-Step Verification
3. ไปที่ App Passwords → สร้าง Password ใหม่
4. Copy รหัส 16 หลักมาใส่ในโค้ด

---

## 🔄 System Flow

```
นักศึกษาสมัครสมาชิก (เว็บ/Register)
        ↓
ข้อมูลบันทึกใน scholarships.db
        ↓
Scheduler ทำงานทุก 24 ชั่วโมง
        ↓
Matcher จับคู่ทุน + นักศึกษาที่เข้าเกณฑ์
        ↓
Email Sender ส่ง Email ผ่าน SMTP:587 (TLS)
        ↓
นักศึกษาได้รับ Email แจ้งเตือนในกล่องข้อความ
```

---

## 🛠️ เครื่องมือที่ใช้

| เครื่องมือ | หน้าที่ |
|---|---|
| Python 3.x | ภาษาหลัก |
| Flask | Web Framework |
| SQLite3 | Database (built-in) |
| smtplib | ส่ง Email (built-in) |
| socket | TCP Server/Client (built-in) |
| threading | Multi-threading (built-in) |
| ngrok | Public URL Tunnel |

---

## 📝 หมายเหตุ

- `scholarships.db` สร้างอัตโนมัติเมื่อรัน `python app.py` ครั้งแรก
- ถ้าต้องการ Reset ฐานข้อมูล ให้ลบไฟล์ `scholarships.db` แล้วรันใหม่
- ngrok URL จะเปลี่ยนทุกครั้งที่รันใหม่ ถ้าต้องการ URL คงที่ต้องใช้ Static Domain

---

*ScholarPath — พัฒนาโดยนักศึกษา มหาวิทยาลัยเทคโนโลยีสุรนารี*
