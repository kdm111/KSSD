class Encoder:
    def __init__(self):
        self.encoder = ''
        self.wheel_width = 0.67 

    def connect(self):
        try:
            from gpiozero import DigitalInputDevice
        except ImportError:
            self.mock_mode = True
            print(f"⚠️ {self.direction} Mock 모드 (gpiozero 없음)")
            return

        try:
            self.encoder = DigitalInputDevice(26)
            print(f"✅ {self.encoder} 인코더 센서 연결 완료")
        except Exception as e:
            self.mock_mode = True
            print(f"⚠️ {self.direction} Mock 모드 ({e})")
    def detected():
        print("물체 감지: 광선이 차단되었습니다!")

    def cleared():
        print("상태 정상: 광선이 통과 중입니다.")
    def get_curr_speed():
        e



# 상태 변화에 따른 함수 연결
sensor1.when_activated = detected   # 차단 시 (High)
sensor1.when_deactivated = cleared  # 통과 시 (Low)
# sensor2.when_activated = detected   # 차단 시 (High)
# sensor2.when_deactivated = cleared  # 통과 시 (Low)



