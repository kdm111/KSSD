import cv2
import socket
import struct
import time

SERVER_IP = '10.10.14.1'
PORT = 9999

def start_client():

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((SERVER_IP, PORT)) # 서버 IP
    
    # 웹캠 대신 동영상 파일 사용 (파일이 없으면 0으로 바꿔서 웹캠 사용 가능)
    cap = cv2.VideoCapture(0)

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # 1. 프레임 크기 조절 (전송 속도 향상)
            frame = cv2.resize(frame, (640, 480))
            # 2. JPEG로 인코딩 (압축)
            _, img_encoded = cv2.imencode('.jpg', frame)
            data = img_encoded.tobytes()

            # 3. 데이터 길이 전송 (서버가 얼마나 읽어야 할지 알기 위함)
            # 'L'은 unsigned long (4바이트)
            client_socket.sendall(struct.pack(">L", len(data)) + data)
            
            time.sleep(0.03) # 약 30fps 유지
    except Exception as e:
        print(f"에러: {e}")
    finally:
        cap.release()
        client_socket.close()

if __name__ == "__main__":
    start_client()