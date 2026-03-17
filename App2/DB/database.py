from peewee import SqliteDatabase
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # DB/ 폴더
db = SqliteDatabase(os.path.join(BASE_DIR, 'gcc.db'), check_same_thread=False)

#db = SqliteDatabase('gcc.db', check_same_thread=False)
# 다른 모듈에서 db 사용할 때 추가할 것
# db.connect()
