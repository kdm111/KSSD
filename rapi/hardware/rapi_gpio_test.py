from gpiozero import Motor
from pynput import keyboard
from time import sleep
import sys
import tty
import termios

# 모터 설정
motor_left_front = Motor(forward=27, backward=17, enable=22, pwm=True)
motor_right_front = Motor(forward=24, backward=23, enable=25, pwm=True)
# motor_left_rear = Motor(forward=5, backward=6, enable=13, pwm=True)
# motor_right_rear = Motor(forward=16, backward=20, enable=21, pwm=True)

MAX_SPEED = 1.0
MIN_SPEED = 0.4
ROT_SPEED = 0.6


# 현재 눌린 키를 저장할 세트
pressed_keys = set()

def on_press(key):
    try:
        # 알파벳 키 저장
        pressed_keys.add(key.char.lower())
    except AttributeError:
        # 특수 키(ESC 등) 저장
        pressed_keys.add(key)

def on_release(key):
    try:
        pressed_keys.discard(key.char.lower())
    except AttributeError:
        pressed_keys.discard(key)
    
    if key == keyboard.Key.esc or (hasattr(key, 'char') and key.char == 'q'):
        return False # 리스너 종료

def get_key():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    #print(f"{fd} {old}")
    try:
        tty.setraw(fd)
        key = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return key
# 리스너를 비동기(Non-blocking)로 시작
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

print(f"{listener.running}프로그램 시작! 'a'를 누르면 모터가 돕니다. 'q'나 'ESC'로 종료.")

try:
    while listener.running:
        key = get_key()
        if key=='w':
            print("모터 작동 중 (전진/후진 시퀀스)")
            # 1. 전진
            # for i in range(5, 15, 5):
            motor_left_front.forward(MAX_SPEED)
            motor_right_front.forward(MAX_SPEED)
            sleep(0.5) # 너무 길면 키 떼는 반응이 늦으므로 0.5초로 단축
            
        elif key=='s':
            # 2. 후진
            motor_left_front.backward(MAX_SPEED)
            motor_right_front.backward(MAX_SPEED)
            sleep(0.5)

        elif key=='a':
            # 3. 좌회전
            motor_left_front.forward(ROT_SPEED)
            motor_right_front.forward(MAX_SPEED)
            sleep(0.5)
        
        elif key=='d':
            # 4. 우회전
            motor_left_front.forward(MAX_SPEED)
            motor_right_front.forward(ROT_SPEED)
            sleep(0.5)

        elif key=='z':
            # 5. 최저 속도
            motor_left_front.forward(MIN_SPEED)
            motor_right_front.forward(MIN_SPEED)
            sleep(0.5)
                    
        else:
            # 아무 키도 안 눌렸을 때 모터 정지
            motor_left_front.stop()
            motor_right_front.stop()
            sleep(0.5)
        if key =='q':
            exit()
            
            
        sleep(0.1) # CPU 점유율 방지용 미세 대기

except KeyboardInterrupt:
    print("\n중단됨")
finally:
    motor_left_front.stop()
    motor_right_front.stop()
    listener.stop()
    print("프로그램 종료")
