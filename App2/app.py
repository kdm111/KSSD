from flask import Flask, render_template, jsonify, request, Response, send_from_directory

from threading import Thread
import time
import os

from DB import db
from Socket.socket_server import socket_server, generate_server
import Socket.socket_server as socket_module

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMGS_DIR = os.path.join(BASE_DIR, "imgs")
os.makedirs(IMGS_DIR, exist_ok=True)

import logging

class NoPollingLog(logging.Filter):
    FILTERED = {'/api/gesture', '/api/vehicle_state', '/api/significant_events'}
    def filter(self, record):
        msg = record.getMessage()
        return not any(path in msg for path in self.FILTERED)

logging.getLogger('werkzeug').addFilter(NoPollingLog())


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/index2')
def index2():
    return render_template('index2_temp.html')

@app.route('/video_feed2')
def video_feed2():
    return Response(generate_server(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/imgs/<path:filename>')
def serve_image(filename):
    return send_from_directory(IMGS_DIR, filename)

@app.route('/api/execute_for', methods=['POST'])
def execute_for():
    data = request.get_json()
    cmd = data.get('command')
    duration = float(data.get('duration', 1.0))
    ok = socket_module.send_command(cmd, duration)
    if not ok:
        return jsonify({'status': 'error', 'reason': 'Pi 연결 없음'}), 503
    return jsonify({'status': 'ok', 'executed': cmd, 'duration': duration})

@app.route('/api/vehicle_state')
def vehicle_state():
    """차량 상태 폴링 (200ms 주기)"""
    return jsonify(socket_module.last_state or {})

@app.route('/api/significant_events')
def significant_events():
    """쌓인 significant 이벤트를 가져감 (가져가면 큐 비워짐)"""
    evts = socket_module.get_and_clear_events()
    return jsonify(evts)


if __name__ == '__main__':
    db.connect()
    t_socket = Thread(target=socket_server, daemon=True)
    t_socket.start()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)