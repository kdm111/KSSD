from flask import Flask, render_template, jsonify, request, Response
# 
from threading import Thread
import time

from cap import Cap
from Model import GestureApp

#from flask_socketio import SocketIO

app = Flask(__name__)

# routing
@app.route('/')
def index():
    return render_template('index.html', detected_data='123')

@app.route('/video_feed')
def video_feed():
    return Response(cap.generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/gesture')
def get_gesture():
    return jsonify({'gesture': gesture_app.read_data()})

if __name__ == '__main__':

    cap = Cap(0)
    gesture_app = GestureApp('data_test.csv', cap)
    t1 = Thread(target=gesture_app.run, daemon=True)
    t1.start()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

