"""
sut_scraper.py — ดึงข้อมูลทุนจากเว็บไซต์ มทส
เมื่อพบทุนใหม่ จะบันทึกลงฐานข้อมูลและส่งแจ้งเตือนทันที
"""

import re
from datetime import datetime, timedelta
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from database import get_connection
from matcher import find_matches_for_scholarship, log_notification
from email_sender import send_bulk_emails

BASE_URL = "https://cia.sut.ac.th/"
CATEGORY_URL = "https://cia.sut.ac.th/category/scholarship/"


def clean_text(text):
    """ล้างข้อความให้สวยขึ้น"""
    if not text:
        return ""
    return " ".join(text.split()).strip()


def parse_deadline(text):
    """
    พยายามแปลงวันหมดเขตจากข้อความ
    รองรับ:
    - YYYY-MM-DD
    - DD/MM/YYYY
    - DD-MM-YYYY
    - May 1, 2026
    ถ้าไม่เจอ จะ fallback เป็นอีก 30 วันข้างหน้า
    """
    if not text:
        return (datetime.today() + timedelta(days=30)).strftime("%Y-%m-%d")

    text = clean_text(text)

    # แบบ Month Day, Year
    month_map = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12"
    }
    m0 = re.search(
        r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}),\s*(\d{4})",
        text,
        re.IGNORECASE
    )
    if m0:
        month_name, day, year = m0.groups()
        month = month_map[month_name.lower()]
        return f"{year}-{month}-{int(day):02d}"

    # แบบ YYYY-MM-DD
    m1 = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m1:
        y, m, d = m1.groups()
        return f"{y}-{m}-{d}"

    # แบบ DD/MM/YYYY
    m2 = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if m2:
        d, m, y = m2.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"

    # แบบ DD-MM-YYYY
    m3 = re.search(r"(\d{1,2})-(\d{1,2})-(\d{4})", text)
    if m3:
        d, m, y = m3.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"

    # fallback
    return (datetime.today() + timedelta(days=30)).strftime("%Y-%m-%d")


def get_requests_session():
    """สร้าง session สำหรับ requests"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    return session


def fetch_html(session, url, timeout=15):
    """โหลด HTML จาก URL"""
    res = session.get(url, timeout=timeout)
    res.raise_for_status()
    return res.text


def get_real_apply_link(session, detail_url):
    """
    เข้าไปหน้า detail แล้วพยายามหาลิงก์สมัครจริง
    ถ้าไม่เจอ จะคืน detail_url กลับมา
    """
    try:
        html = fetch_html(session, detail_url)
        soup = BeautifulSoup(html, "html.parser")

        priority_keywords = [
            "apply", "application", "สมัคร", "สมัครทุน", "click here", "อ่านเพิ่มเติม"
        ]

        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()
            text = clean_text(a.get_text(" ", strip=True)).lower()

            if not href:
                continue

            if any(keyword in text for keyword in priority_keywords):
                return urljoin(detail_url, href)

        return detail_url

    except Exception as e:
        print(f"⚠️ หาลิงก์สมัครจริงไม่ได้: {detail_url} | {e}")
        return detail_url


def parse_detail_page(session, detail_url):
    """
    เข้าไปอ่านหน้า detail เพื่อดึง description, deadline และลิงก์สมัคร
    """
    try:
        html = fetch_html(session, detail_url)
        soup = BeautifulSoup(html, "html.parser")
        page_text = clean_text(soup.get_text(" ", strip=True))

        # description เอา paragraph แรก ๆ
        paragraphs = soup.find_all("p")
        if paragraphs:
            description = clean_text(" ".join(p.get_text(" ", strip=True) for p in paragraphs[:3]))
        else:
            description = page_text[:1000]

        deadline = parse_deadline(page_text)
        apply_url = get_real_apply_link(session, detail_url)

        return {
            "description": description[:1000],
            "deadline": deadline,
            "apply_url": apply_url
        }

    except Exception as e:
        print(f"⚠️ เปิดหน้า detail ไม่ได้: {detail_url} | {e}")
        return {
            "description": "",
            "deadline": (datetime.today() + timedelta(days=30)).strftime("%Y-%m-%d"),
            "apply_url": detail_url
        }


def is_duplicate(cursor, title, deadline, apply_url):
    """ตรวจว่าทุนนี้ซ้ำในฐานข้อมูลหรือยัง"""
    cursor.execute("""
        SELECT id
        FROM scholarships
        WHERE apply_url = ?
           OR (title = ? AND deadline = ?)
        LIMIT 1
    """, (apply_url, title, deadline))
    return cursor.fetchone() is not None


def save_scholarship(cursor, title, description, deadline, apply_url):
    """บันทึกทุนลงฐานข้อมูล"""
    cursor.execute("""
        INSERT OR IGNORE INTO scholarships
        (title, description, source, min_gpa, level, faculty, nationality, deadline, apply_url, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (
        title[:200],
        description,
        "มทส",
        0,
        "ทุกระดับ",
        "ทุกคณะ",
        "ทุกสัญชาติ",
        deadline,
        apply_url
    ))


def scrape_sut_scholarships(max_items=15):
    """
    ดึงข้อมูลทุนจากหน้า category ของ มทส
    ถ้ามีทุนใหม่ จะจับคู่และส่งแจ้งเตือนทันที
    """
    print("🚀 กำลังดึงข้อมูลทุนจาก SUT...")

    session = get_requests_session()

    try:
        html = fetch_html(session, CATEGORY_URL)
    except Exception as e:
        print("❌ โหลดหน้า category ไม่ได้:", e)
        return

    soup = BeautifulSoup(html, "html.parser")
    posts = soup.select("article, .post, .entry, .news-item")

    if not posts:
        print("❌ ไม่เจอข้อมูล (selector อาจเปลี่ยน)")
        return

    conn = get_connection()
    cursor = conn.cursor()

    new_count = 0
    skip_count = 0
    seen_in_this_run = set()

    for post in posts[:max_items]:
        link_tag = post.find("a", href=True)
        if not link_tag:
            continue

        title = clean_text(link_tag.get_text(" ", strip=True))
        detail_url = urljoin(BASE_URL, link_tag.get("href", "").strip())

        if not title or not detail_url:
            continue

        # กันซ้ำในรอบเดียวกัน
        run_key = (title.lower(), detail_url.lower())
        if run_key in seen_in_this_run:
            skip_count += 1
            continue
        seen_in_this_run.add(run_key)

        # text จาก list page
        post_text = clean_text(post.get_text(" ", strip=True))
        deadline_hint = parse_deadline(post_text)

        # อ่านหน้า detail
        detail = parse_detail_page(session, detail_url)

        description = detail["description"]
        deadline = detail["deadline"] or deadline_hint
        apply_url = detail["apply_url"] or detail_url

        # ตรวจซ้ำใน DB
        if is_duplicate(cursor, title[:200], deadline, apply_url):
            skip_count += 1
            continue

        try:
            save_scholarship(cursor, title, description, deadline, apply_url)

            if cursor.rowcount > 0:
                new_count += 1
                new_id = cursor.lastrowid

                print(f"✅ เพิ่มทุนใหม่: {title} | deadline={deadline}")

                # commit ก่อน เพื่อให้ matcher มองเห็นข้อมูลใหม่
                conn.commit()

                # จับคู่เฉพาะทุนใหม่
                matches = find_matches_for_scholarship(new_id)

                # ส่งแจ้งเตือนทันที
                if matches:
                    send_bulk_emails(matches, log_func=log_notification)
                else:
                    print("ℹ️ ไม่มีนักศึกษาที่เข้าเกณฑ์สำหรับทุนนี้")
            else:
                skip_count += 1

        except Exception as e:
            print(f"❌ insert error: {title} | {e}")

    conn.commit()
    conn.close()

    print(f"\n🎯 สรุป: เพิ่มใหม่ {new_count} | ข้าม (ซ้ำ) {skip_count}")


if __name__ == "__main__":
    scrape_sut_scholarships()