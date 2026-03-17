from typing import Text
from peewee import *
from .database import db

class BaseModel(Model):
    class Meta:
        database = db

# 로그 테이블
class Log(BaseModel):
    timestamp = TextField()
    gesture = CharField()
    operation = CharField()

    class Meta:
        table_name = 'log'

# 제스처를 담을 테이블
class Gesture(BaseModel):
    timestamp = TextField()
    gesture = CharField()
    action_map = CharField()
    class Meta:
        table_name = 'gesture'

class VehicleStateLog(BaseModel):
    timestamp = TextField()
    is_connected = TextField()
    status = TextField()
    speed = FloatField()
    current_command = TextField()
    class Meta:
        table_name = 'vehicle_state_log'

class YoloDetectionLog(BaseModel):
    """YOLO significant detection 기록 (save_flag=True일 때)"""
    timestamp = TextField()
    save_path = TextField()           # 이미지 파일명 (확장자 없음)
    label = TextField()               # 감지된 객체 라벨
    confidence = FloatField()         # 감지 신뢰도
    distance_cm = FloatField()        # 추정 거리 (cm)
    bbox_area = FloatField(null=True) # 바운딩박스 면적 (w*h)
    inference_ms = FloatField(null=True) # 추론 시간 (ms)
    speed = FloatField(null=True)     # 저장 시점의 차량 속도
    current_command = TextField(null=True) # 저장 시점의 명령

    class Meta:
        table_name = 'yolo_detection_log'