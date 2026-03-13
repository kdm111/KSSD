import threading
import time
from fastapi import FastAPI, socket
from DB import db, init, insert_log

app = FastAPI()

# 차량 Pi 소켓 연결
#vehicle_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#vehicle_sock.connect(('차량Pi_IP', 9000))



@app.on_event("startup")
def startup():
    init()

    print("DB 연결 완료 ✅")

@app.post('/gesture')
async def receive_gesture(data: dict):
    cmd = {"command": "forward", "speed": 0.7}
    insert_log
    vehicle_sock.send(json.dumps(cmd).encode())
    return {"status": "ok"}

@app.on_event("shutdown")
def startup():
    init()        
    print("DB 연결 해지")