from .models import Log, Command, YoloDetectionResult
from datetime import datetime

def insert_log(gesture: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {gesture} 입력")
    Log.create(timestamp=timestamp, gesture=gesture)

def get_recent(limit: int = 100):
    return Log.select().order_by(Log.timestamp.desc()).limit(limit)


def get_all():
    return Log.select()

def get_command(id: int):
    return Command.select().where(id=id)

def insert_yolo_detection_result(label:str, confidence: float, bbox_area: int, inference_ms: float, distance_cm: int):
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S.") + f"{now.microsecond // 1000:03d}"
    return YoloDetectionResult.create(timestamp=now, label=label, confidence=confidence, bbox_area=bbox_area, inference_ms=inference_ms, distance_cm=distance_cm)