"""
app.py — Flask Web Application
ระบบแจ้งเตือนทุนการศึกษา มทส
"""
from sut_scraper import scrape_sut_scholarships
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from database import get_connection, init_db, seed_data
from matcher import find_matches, log_notification
from email_sender import send_bulk_emails
from datetime import datetime, date
import sys

# Windows terminal UTF-8 print fix
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

app = Flask(__name__)
app.secret_key = "scholarpath_sut_2026"


# ─────────────────────────────
# คำนวณวันหมดเขต
# ─────────────────────────────
def get_days_left(deadline_str):
    try:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        return (deadline - date.today()).days
    except Exception:
        return 9999


# ─────────────────────────────
# หน้าแรก
# ─────────────────────────────
@app.route("/")
def index():
    if "student_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# ─────────────────────────────
# Login
# ─────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email    = request.form.get("email")
        password = request.form.get("password")
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM students WHERE email = ? AND password = ?",
            (email, password)
        )
        student = cursor.fetchone()
        conn.close()
        if student:
            session["student_id"]    = student["id"]
            session["student_name"]  = student["name"]
            session["student_email"] = student["email"]
            return redirect(url_for("dashboard"))
        else:
            error = "Email หรือรหัสผ่านไม่ถูกต้อง"
    return render_template("login.html", error=error)


# ─────────────────────────────
# Register
# ─────────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        name        = request.form.get("name")
        email       = request.form.get("email")
        password    = request.form.get("password")
        phone       = request.form.get("phone")
        gpa         = float(request.form.get("gpa", 0))
        faculty     = request.form.get("faculty")
        level       = request.form.get("level")
        nationality = request.form.get("nationality", "ไทย")
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO students
                (name, email, password, phone, gpa, faculty, level, nationality)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, email, password, phone, gpa, faculty, level, nationality))
            conn.commit()
            conn.close()
            return redirect(url_for("login"))
        except Exception:
            error = "Email นี้มีในระบบแล้ว"
    return render_template("register.html", error=error)


# ─────────────────────────────
# Dashboard
# ─────────────────────────────
@app.route("/dashboard")
def dashboard():
    if "student_id" not in session:
        return redirect(url_for("login"))
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE id = ?", (session["student_id"],))
    student_row = cursor.fetchone()
    if not student_row:
        session.clear()
        return redirect(url_for("login"))
    student = dict(student_row)

    # ทุนที่เข้าเกณฑ์
    cursor.execute("""
        SELECT * FROM scholarships
        WHERE is_active = 1
        AND deadline >= date('now')
        AND min_gpa <= ?
        AND (level = 'ทุกระดับ' OR level = ?)
        AND (nationality = 'ทุกสัญชาติ' OR nationality = ?)
        AND (faculty = 'ทุกคณะ' OR faculty = ?)
        ORDER BY deadline ASC
    """, (student["gpa"], student["level"], student["nationality"], student["faculty"]))

    my_scholarships = []
    for s in cursor.fetchall():
        s = dict(s)
        s["days_left"] = get_days_left(s["deadline"])
        my_scholarships.append(s)

    # Bookmark ของนักศึกษา
    cursor.execute("""
        SELECT scholarship_id FROM bookmarks WHERE student_id = ?
    """, (session["student_id"],))
    bookmarked_ids = {row["scholarship_id"] for row in cursor.fetchall()}

    # แจ้งเตือนล่าสุด
    cursor.execute("""
        SELECT n.*, s.title
        FROM notifications n
        JOIN scholarships s ON n.scholarship_id = s.id
        WHERE n.student_id = ?
        ORDER BY n.sent_at DESC
        LIMIT 5
    """, (session["student_id"],))
    notifications = [dict(n) for n in cursor.fetchall()]
    conn.close()

    return render_template(
        "dashboard.html",
        student=student,
        scholarships=my_scholarships,
        notifications=notifications,
        bookmarked_ids=bookmarked_ids
    )


# ─────────────────────────────
# ทุนทั้งหมด
# ─────────────────────────────
@app.route("/scholarships")
def scholarships():
    if "student_id" not in session:
        return redirect(url_for("login"))
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM scholarships
        WHERE is_active = 1
        AND deadline >= date('now')
        ORDER BY deadline ASC
    """)
    all_scholarships = []
    for s in cursor.fetchall():
        s = dict(s)
        s["days_left"] = get_days_left(s["deadline"])
        all_scholarships.append(s)

    # Bookmark ของนักศึกษา
    cursor.execute("""
        SELECT scholarship_id FROM bookmarks WHERE student_id = ?
    """, (session["student_id"],))
    bookmarked_ids = {row["scholarship_id"] for row in cursor.fetchall()}
    conn.close()

    return render_template(
        "scholarships.html",
        scholarships=all_scholarships,
        bookmarked_ids=bookmarked_ids
    )


# ─────────────────────────────
# Bookmarks — ทุนที่บันทึกไว้
# ─────────────────────────────
@app.route("/bookmarks")
def bookmarks():
    if "student_id" not in session:
        return redirect(url_for("login"))
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.* FROM scholarships s
        JOIN bookmarks b ON s.id = b.scholarship_id
        WHERE b.student_id = ?
        ORDER BY b.created_at DESC
    """, (session["student_id"],))
    bookmarked = []
    for s in cursor.fetchall():
        s = dict(s)
        s["days_left"] = get_days_left(s["deadline"])
        bookmarked.append(s)
    conn.close()
    return render_template("bookmarks.html", scholarships=bookmarked)


# ─────────────────────────────
# Scholarship Detail
# ─────────────────────────────
@app.route("/scholarship/<int:scholarship_id>")
def scholarship_detail(scholarship_id):
    if "student_id" not in session:
        return redirect(url_for("login"))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM scholarships WHERE id = ? AND is_active = 1
    """, (scholarship_id,))
    scholarship = cursor.fetchone()
    conn.close()
    if not scholarship:
        return "ไม่พบทุนนี้", 404
    scholarship = dict(scholarship)
    scholarship["days_left"] = get_days_left(scholarship["deadline"])
    return render_template("scholarship_detail.html", scholarship=scholarship)


# ─────────────────────────────
# Profile — ดูและแก้ไขข้อมูล
# ─────────────────────────────
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "student_id" not in session:
        return redirect(url_for("login"))

    conn   = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        name        = request.form.get("name")
        phone       = request.form.get("phone")
        gpa         = float(request.form.get("gpa", 0))
        faculty     = request.form.get("faculty")
        level       = request.form.get("level")
        nationality = request.form.get("nationality", "ไทย")
        new_password = request.form.get("new_password")

        if new_password:
            cursor.execute("""
                UPDATE students
                SET name=?, phone=?, gpa=?, faculty=?, level=?, nationality=?, password=?
                WHERE id=?
            """, (name, phone, gpa, faculty, level, nationality, new_password, session["student_id"]))
        else:
            cursor.execute("""
                UPDATE students
                SET name=?, phone=?, gpa=?, faculty=?, level=?, nationality=?
                WHERE id=?
            """, (name, phone, gpa, faculty, level, nationality, session["student_id"]))

        conn.commit()
        session["student_name"] = name
        conn.close()
        return redirect(url_for("profile"))

    cursor.execute("SELECT * FROM students WHERE id = ?", (session["student_id"],))
    student = dict(cursor.fetchone())
    conn.close()
    return render_template("profile.html", student=student)


# ─────────────────────────────
# Logout
# ─────────────────────────────
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ═════════════════════════════════════════════
# REST API Endpoints
# ═════════════════════════════════════════════

# GET /api/scholarships — ดึงทุนทั้งหมด
@app.route("/api/scholarships", methods=["GET"])
def api_scholarships():
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM scholarships
        WHERE is_active = 1
        AND deadline >= date('now')
        ORDER BY deadline ASC
    """)
    result = []
    for s in cursor.fetchall():
        s = dict(s)
        s["days_left"] = get_days_left(s["deadline"])
        result.append(s)
    conn.close()
    return jsonify({"status": "ok", "count": len(result), "scholarships": result})


# GET /api/scholarships/<id> — ดึงทุนรายการเดียว
@app.route("/api/scholarships/<int:scholarship_id>", methods=["GET"])
def api_scholarship_detail(scholarship_id):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scholarships WHERE id = ?", (scholarship_id,))
    s = cursor.fetchone()
    conn.close()
    if not s:
        return jsonify({"status": "error", "message": "ไม่พบทุนนี้"}), 404
    s = dict(s)
    s["days_left"] = get_days_left(s["deadline"])
    return jsonify({"status": "ok", "scholarship": s})


# GET /api/students/<id>/matches — ทุนที่เข้าเกณฑ์ของนักศึกษา
@app.route("/api/students/<int:student_id>/matches", methods=["GET"])
def api_student_matches(student_id):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    student = cursor.fetchone()
    if not student:
        conn.close()
        return jsonify({"status": "error", "message": "ไม่พบนักศึกษา"}), 404
    student = dict(student)
    cursor.execute("""
        SELECT * FROM scholarships
        WHERE is_active = 1
        AND deadline >= date('now')
        AND min_gpa <= ?
        AND (level = 'ทุกระดับ' OR level = ?)
        AND (nationality = 'ทุกสัญชาติ' OR nationality = ?)
        AND (faculty = 'ทุกคณะ' OR faculty = ?)
        ORDER BY deadline ASC
    """, (student["gpa"], student["level"], student["nationality"], student["faculty"]))
    result = []
    for s in cursor.fetchall():
        s = dict(s)
        s["days_left"] = get_days_left(s["deadline"])
        result.append(s)
    conn.close()
    return jsonify({"status": "ok", "student": student["name"], "count": len(result), "matches": result})


# GET /api/send-notifications — ส่ง Email แจ้งเตือน
@app.route("/api/send-notifications", methods=["GET"])
def api_send_notifications():
    matches = find_matches()
    if matches:
        send_bulk_emails(matches, log_func=log_notification)
        return jsonify({"status": "ok", "sent": len(matches)})
    return jsonify({"status": "ok", "sent": 0})


# POST /api/bookmark/<id> — Toggle Bookmark (เพิ่ม/ลบ)
@app.route("/api/bookmark/<int:scholarship_id>", methods=["POST"])
def api_toggle_bookmark(scholarship_id):
    if "student_id" not in session:
        return jsonify({"status": "error", "message": "กรุณา Login ก่อน"}), 401
    student_id = session["student_id"]
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM bookmarks
        WHERE student_id = ? AND scholarship_id = ?
    """, (student_id, scholarship_id))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("""
            DELETE FROM bookmarks
            WHERE student_id = ? AND scholarship_id = ?
        """, (student_id, scholarship_id))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "action": "removed", "bookmarked": False})
    else:
        cursor.execute("""
            INSERT INTO bookmarks (student_id, scholarship_id)
            VALUES (?, ?)
        """, (student_id, scholarship_id))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "action": "added", "bookmarked": True})


# GET /api/bookmarks — ดึง Bookmark ของนักศึกษา
@app.route("/api/bookmarks", methods=["GET"])
def api_get_bookmarks():
    if "student_id" not in session:
        return jsonify({"status": "error", "message": "กรุณา Login ก่อน"}), 401
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.* FROM scholarships s
        JOIN bookmarks b ON s.id = b.scholarship_id
        WHERE b.student_id = ?
        ORDER BY b.created_at DESC
    """, (session["student_id"],))
    result = []
    for s in cursor.fetchall():
        s = dict(s)
        s["days_left"] = get_days_left(s["deadline"])
        result.append(s)
    conn.close()
    return jsonify({"status": "ok", "count": len(result), "bookmarks": result})


# ─────────────────────────────
# Run Server
# ─────────────────────────────
if __name__ == "__main__":
    init_db()
    seed_data()
    scrape_sut_scholarships()
    print("\n🎓 ScholarPath เปิดที่ http://127.0.0.1:5000")
    print("\n📡 REST API Endpoints:")
    print("  GET  /api/scholarships")
    print("  GET  /api/scholarships/<id>")
    print("  GET  /api/students/<id>/matches")
    print("  GET  /api/send-notifications")
    print("  POST /api/bookmark/<id>")
    print("  GET  /api/bookmarks")
    app.run(debug=True)