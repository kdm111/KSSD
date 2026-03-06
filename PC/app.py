from flask import Flask, render_template, jsonify, request

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({'status': 'ok', 'message': 'Server is running'})
@socketio.on('gesture')
def on_gesture(data):
    socketio.emit('gesture', data)

@app.route('/api/data', methods=['POST'])
def receive_data():
    data = request.get_json()
    print(f"[수신] {data}")
    # HID에서 받은 데이터 브라우저로 전송
    socketio.emit('gesture', data)
    return jsonify({'result': 'success'})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)