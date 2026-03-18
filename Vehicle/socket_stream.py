import socket
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import cv2
import json
import struct

# 한국시간 설정
KST = ZoneInfo("Asia/Seoul")

def socket_stream(cap, vehicle, drive_manager, PC_IP, PC_PORT):
    """PC에 데이터를 소켓으로 전송"""

    time.sleep(1.5)  # 카메라 준비 대기

    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((PC_IP, PC_PORT))
            print(f"✅ PC 소켓 연결 ({PC_IP}:{PC_PORT})")
            def receive_commands():
                while True:
                    try:
                        raw = sock.recv(4)
                        if not raw: break
                        cmd_len = struct.unpack(">L", raw)[0]
                        payload = json.loads(sock.recv(cmd_len).decode('utf-8'))
                        cmd = payload.get("command")
                        duration = payload.get("duration", 0)
                        print(f"📥 PC 명령: {cmd} {duration}s")
                        if duration > 0:
                            drive_manager.execute_for(cmd, duration)
                        else:
                            drive_manager.execute(cmd)
                    except:
                        break
            from threading import Thread
            Thread(target=receive_commands, daemon=True).start()  # 여기 추가
            while True:
                frame = cap.get_display_frame()
                if frame is None:
                    time.sleep(0.03)
                    continue

                now = datetime.now(KST)
                timestamp = now.strftime("%Y-%m-%d %H:%M:%S.") + f"{now.microsecond // 1000:03d}"

                _, buffer = cv2.imencode('.jpg', frame)
                img_data = buffer.tobytes()

                vehicle_state = vehicle.get_info()
                vehicle_state["timestamp"] = timestamp
                state_data = json.dumps(vehicle_state).encode('utf-8')

                save_flag, save_path = cap.get_save_info()
                # 가장 가까운 detection 정보를 state에 포함
                detections = cap.get_detections()
                closest = min(detections, key=lambda d: d["distance_cm"]) if detections else {}

                front_sensor = drive_manager.front_sensor
                rear_sensor = drive_manager.rear_sensor
                state_data = json.dumps({
                    **vehicle_state,
                    "save_path": save_path,
                    "label": closest.get("label", ""),
                    "confidence": closest.get("confidence", 0),
                    "distance_cm": closest.get("distance_cm", 0),
                    "bbox_area": (closest["bbox"][2]-closest["bbox"][0]) * (closest["bbox"][3]-closest["bbox"][1]) if closest.get("bbox") else None,
                    "front_distance": front_sensor.get_distance(),   # ← 추가
                    "rear_distance": rear_sensor.get_distance(),      # ← 추가
                    "front_safe": front_sensor.is_safe(),             # ← 추가
                    "rear_safe": rear_sensor.is_safe(),               # ← 추가
                }).encode('utf-8')

                vehicle_id_bytes = vehicle.id.encode('utf-8')
                sock.sendall(
                    struct.pack(">L", len(vehicle_id_bytes)) +      # ← 먼저 크기 4바이트
                    vehicle_id_bytes +   
                    struct.pack(">L", len(img_data)) +    # 이미지 크기
                    timestamp.encode('utf-8') +            # 23바이트
                    img_data +                             # 이미지
                    struct.pack(">L", len(state_data)) +  # 상태 크기
                    state_data +                          # 상태 JSON
                    struct.pack(">?", save_flag)          # bool 1바이트로 전송
                    
                )
        except BrokenPipeError:
            print("⚠️ Broken pipe - 재연결 시도")
            break
        except Exception as e:
            print(f"⚠️ 소켓 연결 실패: {e}, 1.5초 후 재시도...")
            time.sleep(1.5)
        finally:
            time.sleep(0.3)