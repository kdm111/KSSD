import state
from DB import insert_log



def execute(cmd):
    action = action_map.get(cmd)
    if action:
        action()
    else:
        print("지원되지 않는 명령 수행")
        insert_log(f"{cmd} ")


def forward():
    state.STATUS = 'FORWARD'
    state.CURR_CMD = 'FOR'
    state.motor_left.forward(state.SPEED)
    state.motor_right.forward(state.SPEED)

def backward():
    state.STATUS = 'BACKWARD'
    state.CURR_CMD = 'BAK'
    state.motor_left.backward(state.SPEED)
    state.motor_right.backward(state.SPEED)

def turn_left():
    state.STATUS = 'TURN LEFT'
    state.CURR_CMD = 'LFT'
    state.motor_left.forward(state.ROT_SPEED)
    state.motor_right.forward(state.MIN_SPEED)

def turn_right():
    state.STATUS = 'TURN RIGHT'
    state.CURR_CMD = 'RIT'
    state.motor_left.forward(state.MIN_SPEED)
    state.motor_right.forward(state.ROT_SPEED)

def stop():
    state.STATUS = 'READY'
    state.CURR_CMD = 'STP'
    state.motor_left.stop()
    state.motor_right.stop()

def speed_down():
    state.SPEED = max(state.MIN_SPEED, round(state.SPEED - state.DELTA, 2))
    execute(state.CURR_CMD)

def speed_up():
    state.SPEED = min(state.MAX_SPEED, round(state.SPEED + state.DELTA, 2))
    execute(state.CURR_CMD)

def spin():
    state.SPEED = 0.5
    state.STATUS = 'SPINNING'
    state.CURR_CMD = 'SPN'
    state.motor_left.forward(state.SPEED)
    state.motor_right.backward(state.SPEED)

def get_status():
    return state.STATUS

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
    'SPN' : spin,
    # 상태
    'STATUS' : get_status
}