import socket
import cv2
import struct
import pickle

# PC의 IP 주소를 입력하세요
SERVER_IP = '10.10.14.2'
PORT = 9999

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((SERVER_IP, PORT))
print("서버 연결됨")

cam = cv2.VideoCapture(0) # 0번 카메라

if not cam.isOpened():
    print("카메라를 찾을 수 없습니다.")
    exit()

# AF_INET -> 
# AF: Address Family (주소 체계 묶음)
# INET: Internet (인터넷)
# 즉, **"인터넷 주소 체계를 사용하는 그룹"**이라는 뜻입니다.

# 1. 서버로부터 종료 신호가 왔는지 체크 (비동기 방식이 좋음)


try:
    while True:
        client_socket.setblocking(False) # 논블로킹 설정
        try:
            msg = client_socket.recv(1024)
            if msg == b'QUIT':
                print("서버로부터 종료 명령을 받았습니다.")
                break
        except BlockingIOError:
            pass # 받은 데이터가 없으면 그냥 넘어감
        client_socket.setblocking(True) # 논블로킹 설정

        ret, frame = cam.read()
        if not ret: break
        
        # 전송 속도를 위해 크기 조절
        frame = cv2.resize(frame, (640, 480))
        # JPEG 압축
        result, frame_encoded = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        
        # 데이터 직렬화
        data = pickle.dumps(frame_encoded)
        # 헤더(Q:8바이트) + 실제데이터 전송
        client_socket.sendall(struct.pack("Q", len(data)) + data)

except (BrokenPipeError, ConnectionResetError):
    print("서버와 연결이 끊겼습니다. 프로그램을 종료합니다.")
except Exception as e:
    print(f"전송 중단: {e}")
finally:
    cam.release()
    client_socket.close()