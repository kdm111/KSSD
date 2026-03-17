import time
from .models import *
from datetime import datetime

# log
def insert_log(gesture: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {gesture} 입력")
    Log.create(timestamp=timestamp, gesture=gesture, operation = 'recognize')

def get_recent(limit: int = 100):
    return Log.select().order_by(Log.timestamp.desc()).limit(limit)

def get_all():
    return Log.select()

# gesture
def insert_gesture_log(gesture: str, action: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"GestureTable : [{timestamp}] {gesture} 입력")
    Gesture.create(timestamp=timestamp,gesture=gesture,action_map=action)
    Log.create(timestamp=timestamp,gesture=gesture,operation='insert')

def delete_gesture_log(gesture: str):
    query = Gesture.delete().where(Gesture.gesture == gesture)
    query.execute()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"GestureTable : [{timestamp}] {gesture} 삭제 완료")
    Log.create(timestamp=timestamp,gesture=gesture,operation='delete')

def update_gesture_log(old_gesture:str,new_gesture:str):
    query = Gesture.update(gesture=new_gesture).where(Gesture.gesture == old_gesture)
    query.execute()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"GestureTable : [{timestamp}] 업데이트 완료")
    Log.create(timestamp=timestamp,gesture=old_gesture,operation='update')

def get_gesture_id(gesture:str):
    try:
        record = Gesture.select(Gesture.id).where(Gesture.gesture == gesture).get()
        return record.id
    except Gesture.DoesNotExist:
        return None

def get_gesture_action(gesture:str):
    try:
        record = Gesture.select(Gesture.action_map).where(Gesture.gesture == gesture).get()
        return record.action_map
    except Gesture.DoesNotExist:
        return None

def check_gesture_exists(gesture:str) -> bool:
    exists = Gesture.select().where(Gesture.gesture == gesture).exists()
    return exists

def get_gesture_recent(limit: int = 100):
    return Gesture.select().order_by(Gesture.timestamp.desc()).limit(limit)

def get_gesture_all():
    return Gesture.select()


# vehicle state log
def insert_vehicle_state_log(state_dict):
    return VehicleStateLog.create(
        is_connected=state_dict.get("is_connected"),
        status=state_dict.get("status"),
        speed=state_dict.get("speed"),
        current_command=state_dict.get("current_command"),
        timestamp=state_dict.get("timestamp")
    )

# YOLO detection log (significant 이벤트만)
def insert_yolo_detection_log(detection_dict):
    """significant=True일 때 호출. save_path, label, confidence 등 저장"""
    return YoloDetectionLog.create(
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

def get_yolo_detections(limit: int = 100):
    return YoloDetectionLog.select().order_by(YoloDetectionLog.timestamp.desc()).limit(limit)