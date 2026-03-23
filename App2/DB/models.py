from peewee import *
from .database import db


class BaseModel(Model):
    class Meta:
        database = db


# ===== 디바이스 등록 =====
class Device(BaseModel):
    device_id = CharField(unique=True)
    device_name = CharField(default="")
    socket_id = CharField(null=True)
    registered_at = TextField()
    last_seen = TextField(null=True)
    is_online = BooleanField(default=False)

    class Meta:
        table_name = 'device'


# ===== 주행 세션 =====
class Session(BaseModel):
    session_id = CharField(unique=True)
    device_id = CharField()
    started_at = TextField()
    ended_at = TextField(null=True)
    status = CharField(default="ACTIVE")

    class Meta:
        table_name = 'session'


# ===== 명령 이력 =====
class CommandLog(BaseModel):
    """
    source: "MANUAL" = 제스처/수동 (duration=-1, 다음 명령 올 때까지 무한)
            "PC"     = PC에서 시간 지정 (duration=실제 초)
    """
    session_id = CharField()
    device_id = CharField()
    seq = IntegerField()
    command = CharField()           # FOR, BAK, LFT, RIT, SPN, STP
    speed = FloatField()
    source = CharField(default="MANUAL")  # "MANUAL" or "PC"
    duration = FloatField(default=-1)     # -1 = 무한(수동), >0 = PC 지정 시간
    actual_duration = FloatField(null=True)  # 실제 수행 시간 (사후 계산)
    timestamp = TextField()

    class Meta:
        table_name = 'command_log'
        indexes = (
            (('session_id', 'seq'), True),
        )


# ===== 기존 테이블 =====


class VehicleStateLog(BaseModel):
    device_id = CharField(default="default")
    timestamp = TextField()
    is_connected = TextField()
    status = TextField()
    speed = FloatField()
    current_command = TextField()

    class Meta:
        table_name = 'vehicle_state_log'


class YoloDetectionLog(BaseModel):
    device_id = CharField(default="default")
    session_id = CharField(null=True)
    timestamp = TextField()
    save_path = TextField()
    label = TextField()
    confidence = FloatField()
    distance_cm = FloatField()
    bbox_area = FloatField(null=True)
    inference_ms = FloatField(null=True)
    speed = FloatField(null=True)
    current_command = TextField(null=True)

    class Meta:
        table_name = 'yolo_detection_log'