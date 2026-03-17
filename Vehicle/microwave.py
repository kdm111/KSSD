import time

class MicroWave:
    def __init__(self, direction):
        self.direction = direction
        self.distance_sensor = None
        self.mock_mode = False
        self.threshold = 0.5  # 20cm 이내면 장애물로 판단

    def connect(self):
        try:
            from gpiozero import DistanceSensor
        except ImportError:
            self.mock_mode = True
            print(f"⚠️ {self.direction} Mock 모드 (gpiozero 없음)")
            return

        try:
            if self.direction == "FRONT":
                self.distance_sensor = DistanceSensor(echo=12, trigger=4)
            else:
                self.distance_sensor = DistanceSensor(echo=19, trigger=8)
            print(f"✅ {self.direction} 초음파 연결 완료")
        except Exception as e:
            self.mock_mode = True
            print(f"⚠️ {self.direction} Mock 모드 ({e})")

    def get_distance(self):
        if self.mock_mode or self.distance_sensor is None:
            return 1.0  # Mock 모드일 때는 장애물이 없는 것으로 간주(1m)
        return self.distance_sensor.distance # meter 단위 반환

    def is_safe(self):
        return self.get_distance() > self.threshold