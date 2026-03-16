from DB import insert_log


def forward(vehicle):
    vehicle.status = 'FORWARD'
    vehicle.current_command = 'FOR'
    vehicle.motor_left.forward(vehicle.speed)
    vehicle.motor_right.forward(vehicle.speed)


def backward(vehicle):
    vehicle.status = 'BACKWARD'
    vehicle.current_command = 'BAK'
    vehicle.motor_left.backward(vehicle.speed)
    vehicle.motor_right.backward(vehicle.speed)


def turn_left(vehicle):
    vehicle.status = 'TURN LEFT'
    vehicle.current_command = 'LFT'
    vehicle.motor_left.forward(vehicle.rot_speed)
    vehicle.motor_right.forward(vehicle.min_speed)


def turn_right(vehicle):
    vehicle.status = 'TURN RIGHT'
    vehicle.current_command = 'RIT'
    vehicle.motor_left.forward(vehicle.min_speed)
    vehicle.motor_right.forward(vehicle.rot_speed)


def stop(vehicle):
    vehicle.status = 'READY'
    vehicle.current_command = 'STP'
    vehicle.motor_left.stop()
    vehicle.motor_right.stop()


def speed_down(vehicle):
    vehicle.speed = max(vehicle.min_speed, round(vehicle.speed - vehicle.delta, 2))
    # 현재 명령 재실행 (속도 반영)
    if vehicle.current_command in COMMANDS:
        COMMANDS[vehicle.current_command](vehicle)


def speed_up(vehicle):
    vehicle.speed = min(vehicle.max_speed, round(vehicle.speed + vehicle.delta, 2))
    if vehicle.current_command in COMMANDS:
        COMMANDS[vehicle.current_command](vehicle)


def spin(vehicle):
    vehicle.speed = 0.5
    vehicle.status = 'SPINNING'
    vehicle.current_command = 'SPN'
    vehicle.motor_left.forward(vehicle.speed)
    vehicle.motor_right.backward(vehicle.speed)


# 명령 맵
COMMANDS = {
    'FOR': forward,
    'BAK': backward,
    'LFT': turn_left,
    'RIT': turn_right,
    'STP': stop,
    'SLW': speed_down,
    'FST': speed_up,
    'SPN': spin,
}