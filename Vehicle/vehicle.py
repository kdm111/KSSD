class Vehicle:
    def __init__(self, name: str, commands: dict = None):
        self.id = name
        self.motor_left = None
        self.motor_right = None
        self.is_connected = False
        self.mock_mode = False
 
        # speed
        self.speed = 0.5
        self.min_speed = 0.3
        self.max_speed = 0.9
        self.rot_speed = 0.8
        self.delta = 0.1
 
        # status
        self.status = 'READY'
        self.current_command = ''
 
        # commands (DI)
        self.commands = commands or {}
 
    def connect(self):
        try:
            from gpiozero import Motor
            self.motor_left = Motor(forward=27, backward=17, enable=22, pwm=True)
            self.motor_right = Motor(forward=24, backward=23, enable=25, pwm=True)
            self.is_connected = True
            print("✅ 모터 연결 (GPIO)")
        except Exception:
            self.mock_mode = True
            self.is_connected = True
            print("⚠️ Mock 모드 (GPIO 없음)")
 
    def disconnect(self):
        if not self.mock_mode and self.motor_left:
            self.motor_left.stop()
            self.motor_left.close()
        if not self.mock_mode and self.motor_right:
            self.motor_right.stop()
            self.motor_right.close()
        self.is_connected = False
        print("🔌 Vehicle 연결 해제")
 
    def execute(self, command_name: str):
        if not self.is_connected:
            return {"error": "not connected"}
        if command_name not in self.commands:
            return {"error": f"unknown: {command_name}"}

        if self.mock_mode:
            self.commands[command_name](self)  # speed_up/down 반영을 위해 호출
            print(f"🎮 [Mock] {command_name} (speed: {self.speed})")
            return {"executed": command_name, "mock": True, "speed": self.speed}
        
        self.commands[command_name](self)
        return {"executed": command_name, "speed": self.speed, "status": self.status}
    
    def get_info(self):
        return {
            "is_connected": self.is_connected,
            "mock_mode": self.mock_mode,
            "status": self.status,
            "speed": self.speed,
            "current_command": self.current_command,
        }