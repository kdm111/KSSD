import state
from DB import insert_log

def execute(cmd):
    from vechicle_temp import action_map
    action = action_map.get(cmd)
    if action:
        action()
    else:
        print("지원되지 않는 명령 수행")
        insert_log(f"{cmd} ")


def forward():
    state.STATUS = 'FORWARD'
    state.motor_left.forward(state.SPEED)
    state.motor_right.forward(state.SPEED)

def backward():
    state.STATUS = 'BACKWARD'
    state.motor_left.backward(state.SPEED)
    state.motor_right.backward(state.SPEED)

def turn_left():
    state.STATUS = 'TURN LEFT'
    state.motor_left.forward(state.MIN_SPEED)
    state.motor_right.forward(state.SPEED)

def turn_right():
    state.STATUS = 'TURN RIGHT'
    state.motor_left.forward(state.SPEED)
    state.motor_right.forward(state.MIN_SPEED)

def stop():
    state.STATUS = 'READY'
    state.motor_left.stop()
    state.motor_right.stop()

def speed_down():
    state.SPEED = min(state.MIN_SPEED, round(state.SPEED - state.DELTA, 1))
    execute(state.CURR_CMD)

def speed_up():
    state.SPEED = min(state.MAX_SPEED, round(state.SPEED + state.DELTA, 1))
    execute(state.CURR_CMD)

def spin():
    state.SPEED = 0.5
    state.STATUS = 'SPINNING'
    state.motor_left.forward(SPEED)
    state.motor_right.backward(SPEED)

def get_status():
    return state.STATUS
