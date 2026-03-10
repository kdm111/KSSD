from .models import Log
from datetime import datetime

def insert_log(gesture: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {gesture} 입력")
    Log.create(timestamp=timestamp, gesture=gesture)

def get_recent(limit: int = 100):
    return Log.select().order_by(Log.timestamp.desc()).limit(limit)

def get_all():
    return Log.select()
