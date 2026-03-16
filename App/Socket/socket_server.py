import socket
import struct
import cv2
import numpy as np
from flask import Flask, Response, render_template
import threading

app = Flask(__name__)
output_frame = None
lock = threading.Lock()

SERVER_IP = '0.0.0.0'
PORT = 9999 # 서버포트

def socket_server():
    global output_frame
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_IP, PORT))
    server_socket.listen(5)
    
    print("소켓 서버 대기 중...")
    conn, addr = server_socket.accept()
    
    data = b""
    payload_size = struct.calcsize(">L")

    while True:
        try:
            # 프레임 길이 정보 수신
            while len(data) < payload_size:
                data += conn.recv(4096)
            
            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack(">L", packed_msg_size)[0]

            # 실제 프레임 데이터 수신
            while len(data) < msg_size:
                data += conn.recv(4096)
            
            frame_data = data[:msg_size]
            data = data[msg_size:]

            # 이미지 디코딩
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            with lock:
                output_frame = frame.copy()
        except:
            break

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