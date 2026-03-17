import socket
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import time
import cv2
import json
import struct

# 한국시간 설정
KST = ZoneInfo("Asia/Seoul")

def socket_stream(cap, vehicle, PC_IP, PC_PORT):
    """PC에 데이터를 소켓으로 전송"""
    
    time.sleep(1.5)  # 카메라 준비 대기

    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((PC_IP, PC_PORT))
            print(f"✅ PC 소켓 연결 ({PC_IP}:{PC_PORT})")

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
                # timestamp 고정 23바이트 + 이미지
                sock.sendall(
                    struct.pack(">L", len(img_data)) +    # 이미지 크기
                    timestamp.encode('utf-8') +            # 23바이트
                    img_data +                             # 이미지
                    struct.pack(">L", len(state_data)) +  # 상태 크기
                    state_data                             # 상태 JSON
                )

        except BrokenPipeError:
            print("⚠️ Broken pipe - 재연결 시도")
            break
            
        except Exception as e:
            print(f"⚠️ 소켓 연결 실패: {e}, 1.5초 후 재시도...")
            time.sleep(1.5)


        time.sleep(0.3)