import time
import string
from .models import Log
from .models import Gesture
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
# init
def gesture_init_log():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    specific_actions = {
        'w': 'FOR',
        's': 'BAK',
        'a': 'LFT',
        'd': 'RIT',
        'x': 'STP'
    }
    alphabets = string.ascii_lowercase
    for alpha in alphabets:
        action = specific_actions.get(alpha, None)
        Gesture.create(timestamp=timestamp,gesture=alpha,action_map=action)
    
    numbers = string.digits
    for num in numbers:
        Gesture.create(timestamp=timestamp, gesture=num, action_map=None)

# insert
def insert_gesture_log(gesture: str, action: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"GestureTable : [{timestamp}] {gesture} 입력")
    Gesture.create(timestamp=timestamp,gesture=gesture,action_map=action)
    Log.create(timestamp=timestamp,gesture=gesture,operation='insert')

# delete
def delete_gesture_log(gesture: str):
    query = Gesture.delete().where(Gesture.gesture == gesture)
    query.execute() # 실제로 삭제 실행

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"GestureTable : [{timestamp}] {gesture} 삭제 완료")
    Log.create(timestamp=timestamp,gesture=gesture,operation='delete')

# update
def update_gesture_log(old_gesture:str,new_gesture:str):
    query = Gesture.update(gesture=new_gesture).where(Gesture.gesture == old_gesture)
    query.execute() # 실제 업데이트 실행

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"GestureTable : [{timestamp}] 업데이트 완료")
    Log.create(timestamp=timestamp,gesture=old_gesture,operation='update')

# id값 가져오기
def get_gesture_id(gesture:str):
    try:
        # gesture가 일치하는 데이터 중 하나를 가져옴
        record = Gesture.select(Gesture.id).where(Gesture.gesture == gesture).get()
        return record.id
    except Gesture.DoesNotExist:
        # 만약 해당 제스처가 DB에 없다면 처리
        return None

# action_map 가져오기
def get_gesture_action(gesture:str):
    try:
        record = Gesture.select(Gesture.action_map).where(Gesture.gesture == gesture).get()
        return record.action_map
    except Gesture.DoesNotExist:
        # 만약 해당 제스처가 DB에 없다면 처리
        return None

# DB안에있는 gesture 확인
def check_gesture_exists(gesture:str) -> bool:
    exists = Gesture.select().where(Gesture.gesture == gesture).exists()
    return exists

def get_gesture_recent(limit: int = 100):
    return Gesture.select().order_by(Gesture.timestamp.desc()).limit(limit)

def get_gesture_all():
    return Gesture.select()