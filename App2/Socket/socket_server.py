import socket
import struct
import cv2
import numpy as np
from flask import Flask, Response
import threading
import os
import json
import time
from motion_planner import MotionPlanner

from DB import (
    insert_vehicle_state_log, insert_yolo_detection_log,
    register_device, device_online, device_offline,
    start_session, end_session, record_command,
)

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

# ===== 상태 공유 =====
last_state = {}
significant_events = []
sig_lock = threading.Lock()

current_conn = None
current_device_id = None
current_session_id = None
_prev_compare = None
_last_cmd = None

# ===== 모션 플래너 (세션 연결 시 생성) =====
planner = None

def send_command(command: str, duration: float = 0):
    """PC → RC카로 명령 전송. duration>0이면 PC 자동 제어."""
    global current_conn
    if current_conn is None:
        return False
    try:
        payload = json.dumps({"command": command, "duration": duration}).encode('utf-8')
        current_conn.sendall(struct.pack(">L", len(payload)) + payload)

        # PC에서 보낸 명령도 CommandLog에 기록
        if current_session_id and current_device_id:
            record_command(
                current_session_id, current_device_id,
                command, last_state.get("speed", 0.5),
                source="PC", duration=duration
            )
        return True
    except Exception as e:
        print(f"⚠️ 명령 전송 실패: {e}")
        return False


def get_and_clear_events():
    with sig_lock:
        evts = significant_events.copy()
        significant_events.clear()
    return evts


def _recv_exact(conn, data, size):
    while len(data) < size:
        packet = conn.recv(4096)
        if not packet:
            raise ConnectionError("연결 끊김")
        data += packet
    return data


def socket_server():
    global current_conn, current_device_id, current_session_id

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_IP, PORT))
    server_socket.listen(5)
    print(f"소켓 서버 대기 중... (Port: {PORT})")

    while True:
        try:
            conn, addr = server_socket.accept()
            current_conn = conn
            print(f"✅ 연결됨: {addr}")
            _handle_connection(conn, addr)
        except Exception as e:
            print(f"서버 에러: {e}")
            if current_session_id:
                end_session(current_session_id, "ABORTED")
            if current_device_id:
                device_offline(current_device_id)
            current_session_id = None
            current_device_id = None
        finally:
            if current_conn:
                try: current_conn.close()
                except: pass
                current_conn = None
        print("🔄 새 연결 대기 중...")


def _handle_connection(conn, addr):
    """
    Vehicle 프로토콜:
    1. vehicle_id 크기 (4B) + vehicle_id (가변)
    2. 이미지 크기 (4B) + timestamp (23B) + 이미지
    3. 상태JSON 크기 (4B) + 상태JSON
    4. save_flag (1B)
    """
    global last_state, output_frame, _prev_compare, _last_cmd
    global current_device_id, current_session_id
    global planner

    data = b""
    PL = 4  # struct ">L" = 4 bytes
    device_id = None
    session_id = None
    first_frame = True

    try:
        while True:
            # 1. vehicle_id
            data = _recv_exact(conn, data, PL)
            vid_size = struct.unpack(">L", data[:PL])[0]
            data = data[PL:]
            data = _recv_exact(conn, data, vid_size)
            vehicle_id = data[:vid_size].decode('utf-8')
            data = data[vid_size:]

            # 첫 프레임: 디바이스 등록 + 세션 시작
            if first_frame:
                device_id = vehicle_id or f"rc_{addr[0].replace('.', '_')}"
                current_device_id = device_id
                register_device(device_id, device_name=f"RC Car ({addr[0]})")
                device_online(device_id, socket_id=f"{addr[0]}:{addr[1]}")
                session_id = start_session(device_id)
                planner = MotionPlanner(device_id, session_id, send_command)
                current_session_id = session_id
                _last_cmd = None
                _prev_compare = None
                first_frame = False
                print(f"📋 세션 시작: {session_id} (device: {device_id})")

            # 2. 이미지
            data = _recv_exact(conn, data, PL)
            img_size = struct.unpack(">L", data[:PL])[0]
            data = data[PL:]

            data = _recv_exact(conn, data, TIMESTAMP_SIZE)
            timestamp = data[:TIMESTAMP_SIZE].decode('utf-8').strip()
            data = data[TIMESTAMP_SIZE:]

            data = _recv_exact(conn, data, img_size)
            frame_data = data[:img_size]
            data = data[img_size:]

            # 3. 상태 JSON
            data = _recv_exact(conn, data, PL)
            state_size = struct.unpack(">L", data[:PL])[0]
            data = data[PL:]

            data = _recv_exact(conn, data, state_size)
            current_state = json.loads(data[:state_size].decode('utf-8'))
            data = data[state_size:]

            # 4. save_flag
            data = _recv_exact(conn, data, 1)
            save_flag = struct.unpack(">?", data[:1])[0]
            data = data[1:]

            # ===== 데이터 추출 =====
            save_path = current_state.get("save_path")
            cmd = current_state.get("current_command", "")
            spd = current_state.get("speed", 0.5)

            # ===== last_state (프론트 폴링용) =====
            last_state = {
                "device_id": device_id,
                "session_id": session_id,
                "timestamp": timestamp,
                "is_connected": current_state.get("is_connected"),
                "status": current_state.get("status"),
                "speed": spd,
                "current_command": cmd,
                "mock_mode": current_state.get("mock_mode"),
            }

            # ===== 수동 명령 변경 → CommandLog (source=MANUAL) =====
            if cmd != _last_cmd:
                record_command(session_id, device_id, cmd, spd,
                               source="MANUAL", duration=-1)
                _last_cmd = cmd

            # ===== 상태 변경 → VehicleStateLog =====
            temp = {
                "is_connected": current_state.get("is_connected"),
                "status": current_state.get("status"),
                "speed": spd, "current_command": cmd,
            }
            if temp != _prev_compare:
                insert_vehicle_state_log({**temp, "timestamp": timestamp},
                                         device_id=device_id)
                _prev_compare = temp

            # ===== 이미지 =====
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is not None:
                with lock:
                    output_frame = frame.copy()

                if save_flag and save_path:
                    full_path = os.path.join(SAVE_DIR, f"{save_path}.jpg")
                    cv2.imwrite(full_path, frame)
                    print(f"📸 저장: {save_path}.jpg")

                    evt = {
                        "timestamp": timestamp, "save_path": save_path,
                        "label": current_state.get("label", ""),
                        "confidence": current_state.get("confidence", 0),
                        "distance_cm": current_state.get("distance_cm", 0),
                        "bbox_area": current_state.get("bbox_area"),
                        "inference_ms": current_state.get("inference_ms"),
                        "speed": spd, "current_command": cmd,
                    }
                    try:
                        insert_yolo_detection_log(evt, device_id, session_id)
                    except Exception as e:
                        print(f"⚠️ YOLO DB 실패: {e}")

                    with sig_lock:
                        significant_events.append(evt)

    except ConnectionError:
        print(f"🔌 연결 종료: {device_id}")
    except Exception as e:
        print(f"에러: {e}")
    finally:
        if session_id:
            end_session(session_id, "COMPLETED")
            print(f"📋 세션 종료: {session_id}")
        if device_id:
            device_offline(device_id)
        current_device_id = None
        current_session_id = None


def generate_server():
    while True:
        with lock:
            frame = output_frame.copy() if output_frame is not None else None
        if frame is None:
            time.sleep(0.01)
            continue
        ok, buf = cv2.imencode(".jpg", frame)
        if not ok: continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + bytearray(buf) + b'\r\n')