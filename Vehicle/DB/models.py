from peewee import *
from .database import db

class BaseModel(Model):
    class Meta:
        database = db

class Log(BaseModel):
    timestamp = TextField()
    gesture = CharField()

    class Meta:
        table_name = 'log'

class Command(BaseModel):
    command = TextField()
    class Meta:
        table_name = 'command'

class YoloDetectionResult(BaseModel):
    timestamp = TextField()
    label = TextField()
    confidence = FloatField()
    bbox_area = IntegerField()
    inference_ms = FloatField()
    distance_cm = IntegerField()
    img_dir = TextField()
    class Meta:
        table_name = 'yolo_detection_result'

