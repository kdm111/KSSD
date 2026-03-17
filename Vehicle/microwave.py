class MicroWave:
    def __init__(self, direction):
        # 
        self.direction = direction
        self.distance_sensor = None
        self.mock_mode = False
        self.is_connected = False
        self.threshold = 0.4
    def connect(self):
        try:
            from gpiozero import DistanceSensor
            if self.direction == "FRONT":
                self.distance_sensor = DistanceSensor(echo=12, trigger=4)
            elif self.direction == "BACK":
                self.distance_sensor = DistanceSensor(echo=19, trigger=8)
            print("✅ 초음파 연결 (GPIO)")
        except Exception:
            self.mock_mode = True
            self.is_connected = True
            print("⚠️ Mock 모드 (GPIO 없음)")

    def get_distance(self):
        if not self.is_connected:
            return 1.0
        return self.distance_sensor.distance * 100

    def is_safe(self):
        return self.get_distance() > self.threshold