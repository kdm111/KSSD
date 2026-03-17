from flask import Flask, render_template, jsonify, request, Response

from threading import Thread
import time
import os

#from cap import Cap
#from Model import GestureApp
from DB import db
from Socket.socket_server import socket_server
from Socket.socket_server import generate_server

#from flask_socketio import SocketIO

app = Flask(__name__)

# loggin 정책 설정
import logging

class NoGestureLog(logging.Filter):
    FILTERED = {'/api/gesture', '/api/vehicle_state'}
    def filter(self, record):
        msg = record.getMessage()
        return not any(path in msg for path in self.FILTERED)

logging.getLogger('werkzeug').addFilter(NoGestureLog())

# routing
@app.route('/')
def index():
    return render_template('index.html')

# @app.route('/video_feed')
# def video_feed():
#     return Response(cap.generate(),
#                     mimetype='multipart/x-mixed-replace; boundary=frame')

# @app.route('/api/gesture')
# def get_gesture():
#     return jsonify({'gesture': gesture_app.read_data()})

# @app.route('/api/set_flags', methods=['POST'])
# def set_flags():
#     data = request.get_json()
#     action = data.get('action') # 'i', 'd', 'u', 'reset' 중 하나
    
#     # 모든 플래그 초기화 함수 (GestureApp 내부에 있다고 가정하거나 직접 구현)
#     if action == 'reset':
#         gesture_app.flags["reset"] = True
#         gesture_app.flags['i'] = False
#         gesture_app.flags['d'] = False
#         gesture_app.flags['u'] = False
        
#         mode_name = "STANDBY"
#     else:
#         # 선택한 플래그만 True로 만들고 나머지는 False (배타적 선택)
#         for key in ['i', 'd', 'u']:
#             gesture_app.flags[key] = (key == action)
#         mode_name = action.upper()

#     return jsonify({'status': 'success', 'active_mode': mode_name})

# @app.route('/api/set_action', methods=['POST'])
# def set_action():
#     data = request.get_json()
#     target_action = data.get('action')  # 예: 'FOR', 'BAK', 'STP' 등
#     # 1. 모든 동작 플래그를 False로 초기화 (배타적 선택)
#     for key in gesture_app.action_flags:
#         gesture_app.action_flags[key] = False

#     # 2. 클릭한 액션만 True로 변경
#     if target_action in gesture_app.action_flags:
#         gesture_app.action_flags[target_action] = True
#     # 3. 현재 전체 플래그 상태를 응답으로 보내주기
#     return jsonify({
#         'status': 'success', 
#         'active_action': target_action,
#         'all_flags': gesture_app.action_flags
#     })

@app.route('/video_feed2')
def video_feed2():
    # 두 번째 영상 스트리밍 경로
    return Response(generate_server(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/index2') # 라즈베리파이에서 받아와서 출력할 웹 페이지
def index2():
    # templates/index2.html 파일을 렌더링
    return render_template('index2.html')

@app.route('/api/vehicle_state')
def vehicle_state():
    from Socket.socket_server import last_state
    return jsonify(last_state)

if __name__ == '__main__':

    db.connect()

    #gesture_app = GestureApp(data_path, cap)

    #t1 = Thread(target=gesture_app.run, daemon=True)
    #t1.start()

    # 소켓 서버를 별도 스레드에서 실행
    t_socket = Thread(target=socket_server,daemon=True)
    t_socket.start()

    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

