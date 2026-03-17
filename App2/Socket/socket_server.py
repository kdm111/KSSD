import socket
import struct
import cv2
import numpy as np
from flask import Flask, Response, render_template
import threading
import os
import json
import time

from DB import insert_vehicle_state_log, insert_yolo_detection_log

app = Flask(__name__)
output_frame = None
lock = threading.Lock()
SERVER_IP = '0.0.0.0'
PORT = 9999
TIMESTAMP_SIZE = 23

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(BASE_DIR, "..", "imgs")
SAVE_DIR = os.path.abspath(SAVE_DIR)
os.makedirs(SAVE_DIR, exist_ok=True)

# ===== 프론트 폴링용 상태 =====
# /api/vehicle_state 에서 반환할 데이터
last_state = {}

# ===== significant 이벤트 큐 =====
# /api/significant_events 에서 가져감 (가져가면 비워짐)
significant_events = []
sig_lock = threading.Lock()

current_conn = None

# 상태 변경 비교용 (타임스탬프/save_path 제외)
_prev_compare = None


def send_command(command: str, duration: float = 0):
    global current_conn
    if current_conn is None:
        print("⚠️ Pi 연결 없음")
        return False
    try:
        payload = json.dumps({"command": command, "duration": duration}).encode('utf-8')
        current_conn.sendall(struct.pack(">L", len(payload)) + payload)
        return True
    except Exception as e:
        print(f"⚠️ 명령 전송 실패: {e}")
        return False


def get_and_clear_events():
    """프론트에서 호출 — 쌓인 significant 이벤트를 가져가고 큐 비우기"""
    with sig_lock:
        evts = significant_events.copy()
        significant_events.clear()
    return evts


def socket_server():
    global current_conn, last_state, output_frame, _prev_compare
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_IP, PORT))
    server_socket.listen(5)

    print(f"소켓 서버 대기 중... (Port: {PORT})")
    conn, addr = server_socket.accept()
    current_conn = conn
    print(f"연결됨: {addr}")

    data = b""
    payload_size = struct.calcsize(">L")

    while True:
        try:
            # 1. 이미지 크기 수신
            while len(data) < payload_size:
                packet = conn.recv(4096)
                if not packet: return
                data += packet

            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack(">L", packed_msg_size)[0]

            # 2. timestamp 수신 (23바이트)
            while len(data) < TIMESTAMP_SIZE:
                packet = conn.recv(4096)
                if not packet: return
                data += packet

            timestamp = data[:TIMESTAMP_SIZE].decode('utf-8').strip()
            data = data[TIMESTAMP_SIZE:]

            # 3. 이미지 데이터 수신
            while len(data) < msg_size:
                packet = conn.recv(4096)
                if not packet: return
                data += packet

            frame_data = data[:msg_size]
            data = data[msg_size:]

            # 4. 상태 JSON 크기 수신
            while len(data) < payload_size:
                data += conn.recv(4096)
            state_size = struct.unpack(">L", data[:payload_size])[0]
            data = data[payload_size:]

            # 5. 상태 JSON 본문 수신
            while len(data) < state_size:
                data += conn.recv(4096)
            json_data = data[:state_size].decode('utf-8')
            data = data[state_size:]

            current_state = json.loads(json_data)

            # 6. save_flag 수신 (1바이트)
            while len(data) < 1:
                data += conn.recv(4096)
            save_flag = struct.unpack(">?", data[:1])[0]
            data = data[1:]

            save_path = current_state.get("save_path")

            # ===== last_state 업데이트 (프론트 폴링용) =====
            last_state = {
                "timestamp": timestamp,
                "is_connected": current_state.get("is_connected"),
                "status": current_state.get("status"),
                "speed": current_state.get("speed"),
                "current_command": current_state.get("current_command"),
                "mock_mode": current_state.get("mock_mode"),
            }

            # ===== 상태 변경 시 DB 로깅 =====
            temp_compare = {
                "is_connected": current_state.get("is_connected"),
                "status": current_state.get("status"),
                "speed": current_state.get("speed"),
                "current_command": current_state.get("current_command"),
            }
            if temp_compare != _prev_compare:
                log_data = {**temp_compare, "timestamp": timestamp}
                insert_vehicle_state_log(log_data)
                _prev_compare = temp_compare

            # ===== 이미지 디코딩 =====
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is not None:
                with lock:
                    output_frame = frame.copy()

                # ===== significant 이벤트 처리 =====
                if save_flag and save_path:
                    full_path = os.path.join(SAVE_DIR, f"{save_path}.jpg")
                    cv2.imwrite(full_path, frame)
                    print(f"📸 저장: {save_path}.jpg")

                    # 이벤트 데이터 구성
                    evt = {
                        "timestamp": timestamp,
                        "save_path": save_path,
                        "label": current_state.get("label", ""),
                        "confidence": current_state.get("confidence", 0),
                        "distance_cm": current_state.get("distance_cm", 0),
                        "bbox_area": current_state.get("bbox_area"),
                        "inference_ms": current_state.get("inference_ms"),
                        "speed": current_state.get("speed", 0),
                        "current_command": current_state.get("current_command", ""),
                    }

                    # DB에 YOLO detection 기록
                    try:
                        insert_yolo_detection_log(evt)
                    except Exception as e:
                        print(f"⚠️ YOLO DB 저장 실패: {e}")

                    # 프론트 이벤트 큐에 추가
                    with sig_lock:
                        significant_events.append(evt)
            else:
                print("이미지 디코딩 실패")

        except Exception as e:
            print(f"에러 발생: {e}")
            break

    conn.close()
    server_socket.close()


def generate_server():
    while True:
        with lock:
            if output_frame is None:
                frame = None
            else:
                frame = output_frame.copy()

        if frame is None:
            time.sleep(0.01)
            continue

        (flag, encodedImage) = cv2.imencode(".jpg", frame)
        if not flag:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')