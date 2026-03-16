import uvicorn
import threading
import socket
import struct
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from vehicle import Vehicle
from commands import COMMANDS
from cap import Cap
from DB import db
from DB.create_db import init
import sys
import tty
import termios

vehicle = Vehicle(commands=COMMANDS)
cap = Cap(0)

PC_IP = "PC의IP주소"  # PC Flask가 돌아가는 IP
PC_PORT = 9999


def socket_stream(cap):
    """PC에 카메라 영상을 소켓으로 전송"""
    import time
    time.sleep(3)  # 카메라 준비 대기

    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((PC_IP, PC_PORT))
            print(f"✅ PC 소켓 연결 ({PC_IP}:{PC_PORT})")

            while True:
                frame = cap.get_frame()
                if frame is None:
                    continue
                import cv2
                _, buffer = cv2.imencode('.jpg', frame)
                data = buffer.tobytes()
                sock.sendall(struct.pack(">L", len(data)) + data)

        except Exception as e:
            print(f"⚠️ 소켓 연결 실패: {e}, 3초 후 재시도...")
            import time
            time.sleep(3)


def get_key():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        key = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return key


def keyboard_listener(vehicle):
    key_map = {
        'w': 'FOR', 's': 'BAK', 'a': 'LFT', 'd': 'RIT',
        'e': 'FST', 'r': 'SLW', ' ': 'STP', 'x': 'SPN',
    }
    print("🎮 키보드: w/s/a/d/e/r/space/x/q")
    while True:
        key = get_key()
        if key == 'q':
            vehicle.execute('STP')
            break
        cmd = key_map.get(key)
        if cmd:
            result = vehicle.execute(cmd)
            print(f"→ {result}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init()
    vehicle.connect()

    # 키보드 스레드
    threading.Thread(target=keyboard_listener, args=(vehicle,), daemon=True).start()

    # PC로 영상 전송 스레드
    threading.Thread(target=socket_stream, args=(cap,), daemon=True).start()

    print("✅ 서버 시작 | 카메라: http://0.0.0.0:8000/camera")
    yield

    vehicle.disconnect()
    cap.release()
    db.close()
    print("🛑 서버 종료")


app = FastAPI(title="RC Car", lifespan=lifespan)

@app.get("/camera")
def camera_feed():
    return StreamingResponse(cap.generate(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/status")
async def get_status():
    return vehicle.get_info()

@app.get("/detections")
async def get_detections():
    return {"detections": cap.get_detections()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
