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
