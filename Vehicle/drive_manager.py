import time

class DriveManager:
    def __init__(self, vehicle, front_sensor=None, rear_sensor=None, cap=None):
        self.vehicle = vehicle
        self.front_sensor = front_sensor
        self.rear_sensor = rear_sensor
        self.cap = cap

    def avoid_obstacle(self, seconds=0.4) -> dict:
        """장애물 우회 시퀀스"""
        print("🔄 장애물 우회 시작")

        # 1. 일단 정지
        self.vehicle.execute("STP")
        time.sleep(0.3)

        # 2. 좌/우 중 빈 쪽 결정 (YOLO bbox 위치 기반)
        turn_cmd = self._decide_turn_direction()

        # 3. 회전 → 전진 → 복귀 회전
        self.vehicle.execute(turn_cmd)
        time.sleep(0.4)

        self.vehicle.execute("FOR")
        time.sleep(0.8)  # 장애물 옆 통과

        # 반대 방향으로 복귀
        recover_cmd = "RIT" if turn_cmd == "LFT" else "LFT"
        self.vehicle.execute(recover_cmd)
        time.sleep(0.4)

        self.vehicle.execute_for("FOR", seconds - 1.2)
        print("✅ 우회 완료")
        return {"avoided": True, "turn": turn_cmd}

    def _decide_turn_direction(self) -> str:
        """YOLO bbox 중심이 프레임 좌/우 어디에 있는지로 회전 방향 결정"""
        if not self.cap:
            return "LFT"  # 기본값

        detections = self.cap.get_detections()
        if not detections:
            return "LFT"

        # 가장 가까운 장애물 기준
        nearest = min(detections, key=lambda d: d["distance_cm"])
        bbox = nearest.get("bbox")  # [x1, y1, x2, y2]
        if not bbox:
            return "LFT"

        # bbox 중심 x가 프레임 중앙(160 기준, imgsz=320) 대비 좌/우
        cx = (bbox[0] + bbox[2]) / 2
        return "RIT" if cx < 160 else "LFT"  # 장애물 반대 방향으로

    def can_execute(self, command: str) -> tuple[bool, str]:
        """실행 가능 여부 + 이유 반환"""
        if self.vehicle.mock_mode:
            return True, "ok"

        # 차량 연결 확인
        if not self.vehicle.is_connected:
            return False, "vehicle not connected"

        # 전진 계열 명령 → 전방 센서 확인
        if command in ("FOR", "FST"):
            if self.front_sensor and not self.front_sensor.is_safe():
                return False, f"전방 장애물 {self.front_sensor.get_distance():.2f}m"

        # 후진 계열 명령 → 후방 센서 확인
        if command in ("BAK",):
            if self.rear_sensor and not self.rear_sensor.is_safe():
                return False, f"후방 장애물 {self.rear_sensor.get_distance():.2f}m"

        # YOLO detection 확인 (dection 이내 장애물)
        if self.cap:
            detections = self.cap.get_detections()
            for det in detections:
                if det["distance_cm"] < 30:
                    return False, f"yolo: {det['label']} {det['distance_cm']}cm"

        return True, "ok"

    def execute(self, command: str) -> dict:
        ok, reason = self.can_execute(command)
    
        if not ok:
            print(f"🚫 실행 거부: {command} ({reason})")
            # 전진 중 전방 장애물이면 우회 시도
            if command in ("FOR", "FST") and "전방" in reason or "yolo" in reason:
                return self.avoid_obstacle()
            self.vehicle.execute("STP")
            return {"blocked": True, "reason": reason, "command": command}

        result = self.vehicle.execute(command)
        result["blocked"] = False
        return result

    def execute_for(self, command: str, seconds: float) -> dict:
        ok, reason = self.can_execute(command)
        if not ok:
            print(f"🚫 실행 거부: {command} ({reason})")
            # 전진 중 전방 장애물이면 우회 시도
            if command in ("FOR", "FST") and "전방" in reason or "yolo" in reason:
                return self.avoid_obstacle(seconds)
            return {"blocked": True, "reason": reason, "command": command}

        self.vehicle.execute(command)
        time.sleep(seconds)
        self.vehicle.execute("STP")
        print(f"⏱ {command} {seconds}초 완료 → STP")
        
        return {"executed": command, "duration": seconds, "blocked": False}