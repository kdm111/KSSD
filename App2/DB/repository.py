"""
GestDrive DB Repository
"""
import json
import uuid
import time as _time
from datetime import datetime
from .models import *


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Device
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def register_device(device_id: str, device_name: str = ""):
    device, created = Device.get_or_create(
        device_id=device_id,
        defaults={"device_name": device_name, "registered_at": _now()}
    )
    if not created and device_name:
        device.device_name = device_name
        device.save()
    return device

def device_online(device_id: str, socket_id: str = None):
    Device.update(is_online=True, socket_id=socket_id, last_seen=_now()
                  ).where(Device.device_id == device_id).execute()

def device_offline(device_id: str):
    Device.update(is_online=False, socket_id=None, last_seen=_now()
                  ).where(Device.device_id == device_id).execute()

def get_device(device_id: str):
    try: return Device.get(Device.device_id == device_id)
    except Device.DoesNotExist: return None

def get_all_devices():
    return list(Device.select().dicts())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Session
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def start_session(device_id: str) -> str:
    sid = str(uuid.uuid4())[:8]
    Session.create(session_id=sid, device_id=device_id,
                   started_at=_now(), status="ACTIVE")
    return sid

def end_session(session_id: str, status: str = "COMPLETED"):
    Session.update(ended_at=_now(), status=status
                   ).where(Session.session_id == session_id).execute()

def get_sessions(device_id: str, limit: int = 20):
    return list(Session.select().where(Session.device_id == device_id)
                .order_by(Session.started_at.desc()).limit(limit).dicts())

def get_active_session(device_id: str):
    try: return Session.get((Session.device_id == device_id) & (Session.status == "ACTIVE"))
    except Session.DoesNotExist: return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CommandLog — 핵심: 수동 vs PC 구분
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_seq_counters = {}    # {session_id: int}
_last_commands = {}   # {session_id: (command, time_float, seq)}


def record_command(session_id: str, device_id: str,
                   command: str, speed: float,
                   source: str = "MANUAL", duration: float = -1):
    """
    명령 기록.

    source="MANUAL", duration=-1  → 제스처/수동 제어 (언제 끝날지 모름)
    source="PC",     duration=2.0 → PC에서 시간 지정 제어

    수동 명령의 actual_duration은 다음 명령이 올 때 자동 계산됨.
    """
    now_ts = _time.time()

    # 이전 수동 명령의 actual_duration 계산
    if session_id in _last_commands:
        _, prev_ts, prev_seq = _last_commands[session_id]
        actual = round(now_ts - prev_ts, 2)
        CommandLog.update(actual_duration=actual).where(
            (CommandLog.session_id == session_id) &
            (CommandLog.seq == prev_seq)
        ).execute()

    seq = _seq_counters.get(session_id, 0)
    CommandLog.create(
        session_id=session_id,
        device_id=device_id,
        seq=seq,
        command=command,
        speed=speed,
        source=source,
        duration=duration,
        actual_duration=duration if source == "PC" else None,
        timestamp=_now(),
    )
    _seq_counters[session_id] = seq + 1
    _last_commands[session_id] = (command, now_ts, seq)


def get_session_commands(session_id: str):
    return list(CommandLog.select().where(CommandLog.session_id == session_id)
                .order_by(CommandLog.seq).dicts())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VehicleStateLog (하위 호환)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def insert_vehicle_state_log(state_dict, device_id: str = "default"):
    return VehicleStateLog.create(
        device_id=device_id,
        is_connected=state_dict.get("is_connected"),
        status=state_dict.get("status"),
        speed=state_dict.get("speed"),
        current_command=state_dict.get("current_command"),
        timestamp=state_dict.get("timestamp"),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# YoloDetectionLog (하위 호환)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def insert_yolo_detection_log(detection_dict, device_id: str = "default",
                               session_id: str = None):
    return YoloDetectionLog.create(
        device_id=device_id,
        session_id=session_id,
        timestamp=detection_dict.get("timestamp"),
        save_path=detection_dict.get("save_path", ""),
        label=detection_dict.get("label", ""),
        confidence=detection_dict.get("confidence", 0),
        distance_cm=detection_dict.get("distance_cm", 0),
        bbox_area=detection_dict.get("bbox_area"),
        inference_ms=detection_dict.get("inference_ms"),
        speed=detection_dict.get("speed"),
        current_command=detection_dict.get("current_command"),
    )

def get_yolo_detections(device_id: str = None, limit: int = 100):
    q = YoloDetectionLog.select().order_by(YoloDetectionLog.timestamp.desc())
    if device_id:
        q = q.where(YoloDetectionLog.device_id == device_id)
    return list(q.limit(limit).dicts())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Log / Gesture (기존 그대로)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def insert_log(gesture: str):
    Log.create(timestamp=_now(), gesture=gesture, operation='recognize')

def get_recent(limit=100):
    return Log.select().order_by(Log.timestamp.desc()).limit(limit)

def get_all():
    return Log.select()

def insert_gesture_log(gesture: str, action: str):
    ts = _now()
    Gesture.create(timestamp=ts, gesture=gesture, action_map=action)
    Log.create(timestamp=ts, gesture=gesture, operation='insert')

def delete_gesture_log(gesture: str):
    Gesture.delete().where(Gesture.gesture == gesture).execute()
    Log.create(timestamp=_now(), gesture=gesture, operation='delete')

def update_gesture_log(old_gesture: str, new_gesture: str):
    Gesture.update(gesture=new_gesture).where(Gesture.gesture == old_gesture).execute()
    Log.create(timestamp=_now(), gesture=old_gesture, operation='update')

def get_gesture_id(gesture: str):
    try: return Gesture.get(Gesture.gesture == gesture).id
    except Gesture.DoesNotExist: return None

def get_gesture_action(gesture: str):
    try: return Gesture.get(Gesture.gesture == gesture).action_map
    except Gesture.DoesNotExist: return None

def check_gesture_exists(gesture: str) -> bool:
    return Gesture.select().where(Gesture.gesture == gesture).exists()

def get_gesture_recent(limit=100):
    return Gesture.select().order_by(Gesture.timestamp.desc()).limit(limit)

def get_gesture_all():
    return Gesture.select()