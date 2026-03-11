import time

class TimeManager: # 타이머 클래스
    def __init__(self):
        self.last_times = {}

    def is_time_up(self, name, interval):
        now = time.time()
        # 처음 부르는 이름이면 0으로 초기화
        last_time = self.last_times.get(name, 0)
        
        if now - last_time > interval:
            self.last_times[name] = now # 시간 업데이트까지 한 번에
            return True
        return False