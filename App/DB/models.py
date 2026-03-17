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

