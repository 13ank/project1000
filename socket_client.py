"""
socket_client.py — TCP Socket Client สำหรับนักศึกษา
ระบบแจ้งเตือนทุนการศึกษา มทส

วิธีใช้:
  python socket_client.py
"""

import socket
import threading

HOST = '127.0.0.1'  # เชื่อมต่อ Server ที่เครื่องเดียวกัน
PORT = 9999

def receive_messages(client):
    """รับข้อความจาก Server ตลอดเวลา — รันใน Thread แยก"""
    while True:
        try:
            message = client.recv(1024).decode('utf-8')
            if message:
                print(message, end='')
        except:
            print("\n[ระบบ] หลุดการเชื่อมต่อจาก Server")
            break

def start_client():
    """เริ่ม TCP Client"""
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        print("=" * 50)
        print("  🎓 ScholarPath — ระบบแจ้งเตือนทุน มทส")
        print("=" * 50)
        print(f"[ระบบ] กำลังเชื่อมต่อ Server {HOST}:{PORT}...")

        # ── TCP Connection ──────────────────────────────
        client.connect((HOST, PORT))
        print("[ระบบ] เชื่อมต่อสำเร็จ!\n")

        # รัน Thread รับข้อความในพื้นหลัง
        t = threading.Thread(target=receive_messages, args=(client,))
        t.daemon = True
        t.start()

        # ส่งข้อความไปยัง Server
        while True:
            message = input()
            if message:
                client.send(message.encode('utf-8'))
                if message.lower() == '/quit':
                    break

    except ConnectionRefusedError:
        print(f"[Error] ไม่สามารถเชื่อมต่อได้ — ตรวจสอบว่า Server รันอยู่หรือเปล่า")
    except KeyboardInterrupt:
        print("\n[ระบบ] ออกจากโปรแกรม")
    finally:
        client.close()

print("\n📌 คำสั่งที่ใช้ได้:")
print("  /status       — ดูจำนวนคนที่ Online")
print("  /scholarships — ดูทุนที่เข้าเกณฑ์")
print("  /quit         — ออกจากระบบ\n")

if __name__ == "__main__":
    start_client()
