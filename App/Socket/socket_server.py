import socket
import struct
import cv2
import numpy as np
from flask import Flask, Response, render_template
import threading
import os

app = Flask(__name__)
output_frame = None
lock = threading.Lock()
SERVER_IP = '0.0.0.0'
PORT = 9999 # 서버포트
TIMESTAMP_SIZE = 23

# 이미지 저장 경로
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # 현재 파일 위치
SAVE_DIR = os.path.join(BASE_DIR, "..", "imgs")         # 상위/imgs
SAVE_DIR = os.path.abspath(SAVE_DIR)                    # 경로 정규화
os.makedirs(SAVE_DIR, exist_ok=True)

def socket_server():
    global output_frame
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 포트 재사용 설정 (서버 재시작 시 편리함)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_IP, PORT))
    server_socket.listen(5)

    print(f"소켓 서버 대기 중... (Port: {PORT})")
    conn, addr = server_socket.accept()
    print(f"연결됨: {addr}")

    data = b""
    payload_size = struct.calcsize(">L")

    while True:
        try:
            # 1. 이미지 크기 수신 (정확히 4바이트 읽기)
            while len(data) < payload_size:
                packet = conn.recv(4096)
                if not packet: return # 연결 종료 시 탈출
                data += packet
            
            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack(">L", packed_msg_size)[0]

            # 2. timestamp 수신 (23바이트)
            while len(data) < TIMESTAMP_SIZE:
                packet = conn.recv(4096)
                if not packet: return
                data += packet
            
            timestamp_raw = data[:TIMESTAMP_SIZE]
            timestamp = timestamp_raw.decode('utf-8').strip() # 공백 제거
            data = data[TIMESTAMP_SIZE:]

            # 3. 이미지 데이터 수신
            while len(data) < msg_size:
                packet = conn.recv(4096)
                if not packet: return
                data += packet
            
            frame_data = data[:msg_size]
            data = data[msg_size:]

            # 이미지 디코딩
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is not None:
                # 파일명으로 사용할 수 없는 문자 처리 (: 등)
                safe_timestamp = timestamp.replace(":", "-").replace(" ", "_")
                save_path = os.path.join(SAVE_DIR, f"{safe_timestamp}.jpg")
                
                # 실제 저장 시도 및 확인
                #success = cv2.imwrite(save_path, frame)
                with lock:
                    output_frame = frame.copy()
            else:
                print("이미지 디코딩 실패")

        except Exception as e:
            print(f"에러 발생: {e}")
            break
    
    conn.close()
    server_socket.close()

def generate_server():
    global output_frame, lock
    while True:
        with lock:
            if output_frame is None:
                continue
            
            # 현재 프레임을 JPEG 형식으로 인코딩
            (flag, encodedImage) = cv2.imencode(".jpg", output_frame)
            
            if not flag:
                continue

        # 바이너리 데이터를 웹 브라우저가 이해할 수 있는 multipart 형식으로 변환
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')
        