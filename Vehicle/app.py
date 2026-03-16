import uvicorn
import threading
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

# Vehicle에 명령 주입
vehicle = Vehicle(commands=COMMANDS)
cap = Cap(0)


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
    """키보드 제어 (테스트용, 나중에 블루투스로 교체)"""
    key_map = {
        'w': 'FOR',
        's': 'BAK',
        'a': 'LFT',
        'd': 'RIT',
        'e': 'FST',
        'r': 'SLW',
        ' ': 'STP',
        'x': 'SPN',
    }
    print("🎮 키보드: w/s/a/d/e(가속)/r(감속)/space(정지)/x(스핀)/q(종료)")
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

    kb_thread = threading.Thread(
        target=keyboard_listener,
        args=(vehicle,),
        daemon=True,
    )
    kb_thread.start()

    print("✅ 서버 시작 | 카메라: http://0.0.0.0:8000/camera")
    yield

    vehicle.disconnect()
    cap.release()
    db.close()
    print("🛑 서버 종료")


app = FastAPI(title="RC Car", lifespan=lifespan)


@app.get("/camera")
def camera_feed():
    return StreamingResponse(
        cap.generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/status")
async def get_status():
    return vehicle.get_info()


@app.get("/detections")
async def get_detections():
    return {"detections": cap.get_detections()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)