"""
socket_server.py — TCP Socket Server
ระบบแจ้งเตือนทุนการศึกษา มทส
"""
import socket, threading
from datetime import datetime
from database import get_connection

HOST = '0.0.0.0'
PORT = 9999
connected_clients = {}
clients_lock = threading.Lock()

def ts(): return datetime.now().strftime("%H:%M:%S")

def broadcast(msg, skip=None):
    with clients_lock:
        dead = []
        for c, i in connected_clients.items():
            if c != skip:
                try: c.send(msg.encode('utf-8'))
                except: dead.append(c)
        for c in dead: del connected_clients[c]

def handle_client(conn, addr):
    print(f"[{ts()}] [+] {addr}")
    info = {"email": None, "name": "Unknown"}
    try:
        conn.send("[SERVER] ยินดีต้อนรับสู่ ScholarPath มทส\n".encode('utf-8'))
        conn.send("[SERVER] กรุณาส่ง email ของคุณเพื่อ Login: ".encode('utf-8'))
        email = conn.recv(1024).decode('utf-8').strip()

        db = get_connection()
        cur = db.cursor()
        cur.execute("SELECT * FROM students WHERE email = ?", (email,))
        row = cur.fetchone()
        db.close()

        if not row:
            conn.send("[SERVER] ไม่พบ email นี้ในระบบ\n".encode('utf-8'))
            conn.close(); return

        student = dict(row)
        info["email"] = email
        info["name"]  = student["name"]
        with clients_lock: connected_clients[conn] = info

        conn.send(("[SERVER] สวัสดีครับ " + student["name"] + "! Online แล้ว\n").encode('utf-8'))
        broadcast("[INFO] " + student["name"] + " เข้าสู่ระบบ", conn)
        conn.send(("[SERVER] Online: " + str(len(connected_clients)) + " คน\n").encode('utf-8'))
        conn.send("[SERVER] คำสั่ง: /scholarships /status /quit\n".encode('utf-8'))
        print(f"[{ts()}] Login: {student['name']}")

        while True:
            data = conn.recv(1024)
            if not data: break
            msg = data.decode('utf-8').strip()

            if msg == "/status":
                with clients_lock: n = len(connected_clients)
                conn.send(("[SERVER] Online: " + str(n) + " คน\n").encode('utf-8'))

            elif msg == "/scholarships":
                db = get_connection()
                cur = db.cursor()
                cur.execute(
                    "SELECT title, deadline, amount FROM scholarships "
                    "WHERE is_active=1 AND min_gpa<=? "
                    "AND (level='ทุกระดับ' OR level=?) "
                    "AND (nationality='ทุกสัญชาติ' OR nationality=?) "
                    "AND (faculty='ทุกคณะ' OR faculty=?) "
                    "ORDER BY deadline",
                    (student["gpa"], student["level"], student["nationality"], student["faculty"])
                )
                rows = [dict(r) for r in cur.fetchall()]
                db.close()
                if rows:
                    out = "[SERVER] ทุนที่คุณเข้าเกณฑ์:\n"
                    for s in rows:
                        amt = str(int(s["amount"])) + " บาท" if s["amount"] and s["amount"] > 0 else "เรียนฟรี"
                        out += "  * " + s["title"] + " (" + amt + ") หมดเขต " + s["deadline"] + "\n"
                else:
                    out = "[SERVER] ไม่พบทุนที่เข้าเกณฑ์\n"
                conn.send(out.encode('utf-8'))

            elif msg == "/quit":
                break

    except: pass
    finally:
        with clients_lock:
            if conn in connected_clients:
                n = connected_clients[conn]["name"]
                del connected_clients[conn]
                broadcast("[INFO] " + n + " ออกจากระบบ")
                print(f"[{ts()}] [-] {n}")
        conn.close()

def start_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT)); srv.listen(10)
    print("="*50)
    print("  ScholarPath TCP Server  port", PORT)
    print("  กด Ctrl+C เพื่อหยุด")
    print("="*50)
    try:
        while True:
            c, a = srv.accept()
            t = threading.Thread(target=handle_client, args=(c, a))
            t.daemon = True; t.start()
    except KeyboardInterrupt: print("\n[SERVER] หยุด")
    finally: srv.close()

if __name__ == "__main__":
    start_server()
