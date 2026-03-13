#from gpiozero import Motor
#from pynput import keyboard
from time import sleep
import sys
import tty
import termios
from DB import insert_log
import state
from action import *
# 모터 설정
state.motor_left = Motor(forward=17, backward=27)
state.motor_right = Motor(forward=23, backward=24)

state.motor_left = ''
state.motor_right = ''


def get_key():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        key = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return key


print(f"자동차 시작! 'q'나 'ESC'로 종료.")
# 동작맵
action_map = {
    # 기본동작
    'FOR' : forward,
    'BAK' : backward,
    'LFT' : turn_left,
    'RIT' : turn_right,
    'STP' : stop,

    # 속도 제어
    'SLW' : speed_down,
    'FST' : speed_up,

    # 제자리 회전
    'SPN' : 'spin',

    # 상태
    'STATUS' : get_status
}

try:
    while True:
        CURR_CMD = input()
        if CURR_CMD in action_map:
            execute(CURR_CMD)
        
        

except KeyboardInterrupt:
    print("\n중단됨")
finally:
    state.motor_left.stop()
    state.motor_right.stop()
    print("자동차 프로그램 종료")