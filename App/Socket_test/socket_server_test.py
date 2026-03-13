import socket
from pynput import keyboard
import pickle
import struct
from flask import Flask, Response, render_template

app = Flask(__name__)

SERVER_IP = '0.0.0.0'
PORT = 9999 # 서버포트
FLASK_PORT = 5001

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((SERVER_IP, PORT))
server_socket.listen(5) # 최대 받을 수 있는 클라이언트 수
print("영상 수신 대기 중...")

client_socket, addr = server_socket.accept()
print(f"연결됨: {addr}")

data = b""
payload_size = struct.calcsize("Q") # 8바이트

running = True
def on_press(key):
    global running
    try:
        if key.char == 'q':
            print("\n[STOP] 종료 신호를 생성합니다...")
            client_socket.sendall(b'QUIT') 
            running = False
            return False # 키보드 리스너 종료
    except AttributeError:
        pass

# 1. 리스너를 '비차단(Non-blocking)' 모드로 시작
listener = keyboard.Listener(on_press=on_press)
listener.start()

def generate_frames():
    global data
    try:
        while running:
            # 1. 8바이트 헤더(데이터 크기) 수신
            while len(data) < payload_size:
                packet = client_socket.recv(4096)
                if not packet: return
                data += packet
            
            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("Q", packed_msg_size)[0]

            # 2. 실제 이미지 데이터 수신
            while len(data) < msg_size:
                data += client_socket.recv(4096)
            
            frame_data = data[:msg_size]
            data = data[msg_size:]

            # 3. 데이터 복구 (Unpickle -> Byte변환)
            # 여기서는 웹 브라우저가 인식할 수 있게 바로 JPEG 바이트로 보냅니다.
            frame_encoded = pickle.loads(frame_data)
            frame_bytes = frame_encoded.tobytes()

            # 4. MJPEG 포맷으로 웹 브라우저에 전송
            # MJPEG(Motion JPEG) 스트리밍의 핵심 규격
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
    except Exception as e:
        print(f"에러 발생: {e}")
    finally:
        client_socket.close()

@app.route('/')
def index():
    return render_template('index.html')

# 3. 실제 이미지 데이터만 쏴주는 통로 (이름을 살짝 바꿉니다)
@app.route('/stream_data')
def stream_data():
    return Response(generate_frames(), 
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=FLASK_PORT)