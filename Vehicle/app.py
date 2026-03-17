import uvicorn
import threading
import struct
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from vehicle import Vehicle
from microwave import MicroWave

from commands import COMMANDS
from cap import Cap
from DB import db, init
import sys
import tty
import termios
from datetime import datetime
from zoneinfo import ZoneInfo

from socket_stream import socket_stream

vehicle = Vehicle(commands=COMMANDS)
front_distance_sensor = MicroWave("FRONT")
back_distance_sensor = MicroWave("BACK")
cap = Cap(0)

PC_IP = "10.10.14.1"  # PC Flask가 돌아가는 IP
PC_STATE_PORT = 9998
PC_STREAM_PORT = 9999
KST = ZoneInfo("Asia/Seoul")

def get_key():
    if sys.platform != 'win32':
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
            if front_distance_sensor.is_safe():
                result = vehicle.execute(cmd)
                print(f"→ {result}")
            else:
                print("위험상태 감지 정지")
                vehicle.stop()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init()
    vehicle.connect()

    # 키보드 스레드
    threading.Thread(target=keyboard_listener, args=(vehicle,), daemon=True).start()

    # PC로 차량 상태/영상 전송 스레드
    threading.Thread(target=socket_stream, args=(cap,vehicle,PC_IP,PC_STREAM_PORT), daemon=True).start()

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
