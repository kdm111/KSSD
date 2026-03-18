import time


class DriveManager:
    def __init__(self, vehicle, front_sensor=None, rear_sensor=None, cap=None):
        self.vehicle = vehicle
        self.front_sensor = front_sensor
        self.rear_sensor = rear_sensor
        self.cap = cap

    def execute(self, command: str) -> dict:
        """단발 실행"""
        result = self.vehicle.execute(command)
        result["blocked"] = False
        return result

    def execute_for(self, command: str, seconds: float) -> dict:
        """시간 지정 실행"""
        self.vehicle.execute(command)
        time.sleep(seconds)
        self.vehicle.execute("STP")
        print(f"⏱ {command} {seconds}초 완료 → STP")
        return {
            "executed": command,
            "duration": seconds,
            "blocked": False,
            "completed": True,
        }