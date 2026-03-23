from flask import Flask, render_template, jsonify, request, Response, send_from_directory
from threading import Thread
import os
import logging

from DB import db
from DB.models import BaseModel
from DB.repository import get_sessions, get_session_commands, get_all_devices
from Socket.socket_server import socket_server, generate_server
import Socket.socket_server as socket_module
from motion_planner import MotionPlanner

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMGS_DIR = os.path.join(BASE_DIR, "imgs")
os.makedirs(IMGS_DIR, exist_ok=True)



def get_planner():
    """현재 세션의 플래너를 가져오거나 새로 생성"""
    global planner
    did = socket_module.current_device_id
    sid = socket_module.current_session_id
    if not did or not sid:
        return None
    if planner is None or planner.session_id != sid:
        planner = MotionPlanner(did, sid, socket_module.send_command)
        print(f"🧠 MotionPlanner 생성 (device={did}, session={sid})")
    return planner


# ===== 로깅 필터 =====
class NoPollingLog(logging.Filter):
    FILTERED = {'/api/vehicle_state', '/api/significant_events', '/api/gesture'}
    def filter(self, record):
        return not any(p in record.getMessage() for p in self.FILTERED)

logging.getLogger('werkzeug').addFilter(NoPollingLog())


# ───── 페이지 ─────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/index2')
def index2():
    return render_template('index2_temp.html')

@app.route('/video_feed2')
def video_feed2():
    return Response(generate_server(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/imgs/<path:filename>')
def serve_image(filename):
    return send_from_directory(IMGS_DIR, filename)


# ───── 수동 제어 ─────

@app.route('/api/execute_for', methods=['POST'])
def execute_for():
    data = request.get_json()
    cmd = data.get('command')
    duration = float(data.get('duration', 1.0))
    ok = socket_module.send_command(cmd, duration)
    if not ok:
        return jsonify({'status': 'error', 'reason': 'Pi 연결 없음'}), 503
    return jsonify({'status': 'ok', 'executed': cmd, 'duration': duration})


# ───── 실시간 폴링 ─────

@app.route('/api/vehicle_state')
def vehicle_state():
    return jsonify(socket_module.last_state or {})

@app.route('/api/significant_events')
def significant_events():
    return jsonify(socket_module.get_and_clear_events())


# ───── 디바이스 / 세션 / 명령 ─────

@app.route('/api/devices')
def devices():
    return jsonify(get_all_devices())

@app.route('/api/sessions')
def sessions():
    did = request.args.get('device_id', socket_module.current_device_id)
    return jsonify(get_sessions(did) if did else [])

@app.route('/api/session/<session_id>/commands')
def session_commands(session_id):
    return jsonify(get_session_commands(session_id))


# ───── 모션 플래닝 ─────

@app.route('/api/plan/return_home', methods=['POST'])
def plan_return_home():
    """현재 세션 전체 역추적 귀환"""
    p = get_planner()
    if not p:
        return jsonify({'error': '디바이스/세션 없음'}), 400
    if p.is_running:
        return jsonify({'error': '이미 실행 중'}), 409

    result = {"status": "pending"}
    def cb(status, msg):
        result["status"] = status
        result["message"] = msg

    ok = p.return_home(callback=cb)
    if not ok:
        return jsonify({'error': result.get("message", "실행 실패")}), 400

    preview = p.get_preview("RETURN_HOME")
    return jsonify({
        'status': 'started',
        'type': 'RETURN_HOME',
        'total_steps': p.total_steps,
        'preview': preview,
    })


@app.route('/api/plan/replay', methods=['POST'])
def plan_replay():
    """현재 세션 전체 재실행"""
    p = get_planner()
    if not p:
        return jsonify({'error': '디바이스/세션 없음'}), 400
    if p.is_running:
        return jsonify({'error': '이미 실행 중'}), 409

    ok = p.replay()
    if not ok:
        return jsonify({'error': '실행할 명령 없음'}), 400

    preview = p.get_preview("REPLAY")
    return jsonify({
        'status': 'started',
        'type': 'REPLAY',
        'total_steps': p.total_steps,
        'preview': preview,
    })


@app.route('/api/plan/undo', methods=['POST'])
def plan_undo():
    """
    특정 명령 1개를 반대로 실행 (UNDO).
    POST body: CommandLog의 dict (seq, command, speed, duration, actual_duration, source)
    """
    p = get_planner()
    if not p:
        return jsonify({'error': '디바이스/세션 없음'}), 400
    if p.is_running:
        return jsonify({'error': '이미 실행 중'}), 409

    cmd_log = request.get_json()
    if not cmd_log or not cmd_log.get('command'):
        return jsonify({'error': 'command 데이터 필요'}), 400

    ok = p.undo_command(cmd_log)
    if not ok:
        return jsonify({'error': '되돌릴 수 없는 명령'}), 400

    from motion_planner import REVERSE_MAP
    return jsonify({
        'status': 'started',
        'type': 'UNDO',
        'original': cmd_log['command'],
        'reversed': REVERSE_MAP.get(cmd_log['command']),
        'duration': p._get_duration(cmd_log),
    })


@app.route('/api/plan/redo', methods=['POST'])
def plan_redo():
    """
    특정 명령 1개를 다시 실행 (DO/REDO).
    POST body: CommandLog의 dict
    """
    p = get_planner()
    if not p:
        return jsonify({'error': '디바이스/세션 없음'}), 400
    if p.is_running:
        return jsonify({'error': '이미 실행 중'}), 409

    cmd_log = request.get_json()
    if not cmd_log or not cmd_log.get('command'):
        return jsonify({'error': 'command 데이터 필요'}), 400

    ok = p.redo_command(cmd_log)
    if not ok:
        return jsonify({'error': '재실행 불가'}), 400

    return jsonify({
        'status': 'started',
        'type': 'REDO',
        'command': cmd_log['command'],
        'duration': p._get_duration(cmd_log),
    })


@app.route('/api/plan/cancel', methods=['POST'])
def plan_cancel():
    p = get_planner()
    if p and p.is_running:
        p.cancel()
    return jsonify({'status': 'cancelled'})


@app.route('/api/plan/status')
def plan_status():
    p = get_planner()
    if not p:
        return jsonify({'is_running': False})
    return jsonify(p.get_status())


# ───── 시작 ─────

if __name__ == '__main__':
    db.connect()


    Thread(target=socket_server, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)