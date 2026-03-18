import time
import threading


class DriveManager:
    def __init__(self, vehicle, front_sensor=None, rear_sensor=None, cap=None):
        self.vehicle = vehicle
        self.front_sensor = front_sensor
        self.rear_sensor = rear_sensor
        self.cap = cap

        # 연속 안전 감시
        self._monitor_active = False
        self._monitor_thread = None

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 안전 감시 (백그라운드)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def start_safety_monitor(self):
        """수동 제어 중 백그라운드에서 센서를 계속 체크"""
        if self._monitor_active:
            return
        self._monitor_active = True
        self._monitor_thread = threading.Thread(target=self._safety_loop, daemon=True)
        self._monitor_thread.start()
        print("🛡️ 안전 감시 시작")

    def stop_safety_monitor(self):
        self._monitor_active = False
        print("🛡️ 안전 감시 중지")

    def _safety_loop(self):
        """200ms마다 현재 명령 기준으로 센서 체크"""
        while self._monitor_active:
            cmd = self.vehicle.current_command

            # 이동 중일 때만 체크
            if cmd and cmd not in ("STP", "READY", ""):
                ok, reason = self.can_execute(cmd)
                if not ok:
                    print(f"🛡️ 감시 정지: {cmd} → {reason}")
                    self.vehicle.execute("STP")

            time.sleep(0.2)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 안전 체크
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def can_execute(self, command: str) -> tuple:
        """실행 가능 여부 + 이유 반환"""
        if self.vehicle.mock_mode:
            return True, "ok"

        if not self.vehicle.is_connected:
            return False, "vehicle not connected"

        # 전진 → 전방 센서
        if command in ("FOR", "FST"):
            if self.front_sensor and not self.front_sensor.is_safe():
                return False, f"전방 장애물 {self.front_sensor.get_distance():.2f}m"

        # 후진 → 후방 센서
        if command in ("BAK",):
            if self.rear_sensor and not self.rear_sensor.is_safe():
                return False, f"후방 장애물 {self.rear_sensor.get_distance():.2f}m"

        # YOLO 30cm 이내
        if command in ("FOR", "FST") and self.cap:
            detections = self.cap.get_detections()
            for det in detections:
                if det["distance_cm"] < 30:
                    return False, f"yolo: {det['label']} {det['distance_cm']}cm"

        return True, "ok"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 명령 실행
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def execute(self, command: str) -> dict:
        """단발 실행 (제스처/수동). 안전 감시는 별도 스레드에서."""
        ok, reason = self.can_execute(command)

        if not ok:
            print(f"🚫 실행 거부: {command} ({reason})")
            if command in ("FOR", "FST") and ("전방" in reason or "yolo" in reason):
                return self.avoid_obstacle()
            self.vehicle.execute("STP")
            return {"blocked": True, "reason": reason, "command": command}

        result = self.vehicle.execute(command)
        result["blocked"] = False
        return result

    def execute_for(self, command: str, seconds: float) -> dict:
        """시간 지정 실행 (PC). 실행 중에도 센서 계속 체크."""
        ok, reason = self.can_execute(command)
        if not ok:
            print(f"🚫 실행 거부: {command} ({reason})")
            if command in ("FOR", "FST") and ("전방" in reason or "yolo" in reason):
                return self.avoid_obstacle(seconds)
            return {"blocked": True, "reason": reason, "command": command}

        self.vehicle.execute(command)

        # sleep 대신 0.1초 단위로 센서 체크하면서 대기
        elapsed = 0.0
        while elapsed < seconds:
            time.sleep(0.1)
            elapsed += 0.1

            # 실행 중 안전 체크
            ok, reason = self.can_execute(command)
            if not ok:
                print(f"🛡️ 실행 중 정지: {reason} ({elapsed:.1f}/{seconds}s)")
                self.vehicle.execute("STP")
                return {
                    "executed": command,
                    "duration": round(elapsed, 1),
                    "blocked": True,
                    "reason": reason,
                    "completed": False,
                }

        self.vehicle.execute("STP")
        print(f"⏱ {command} {seconds}초 완료 → STP")
        return {
            "executed": command,
            "duration": seconds,
            "blocked": False,
            "completed": True,
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 장애물 우회
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def avoid_obstacle(self, seconds=0.4) -> dict:
        print("🔄 장애물 우회 시작")

        self.vehicle.execute("STP")
        time.sleep(0.3)

        turn_cmd = self._decide_turn_direction()

        self.vehicle.execute(turn_cmd)
        time.sleep(0.4)

        self.vehicle.execute("FOR")
        time.sleep(0.8)

        recover_cmd = "RIT" if turn_cmd == "LFT" else "LFT"
        self.vehicle.execute(recover_cmd)
        time.sleep(0.4)

        remaining = max(0, seconds - 1.6)
        if remaining > 0:
            self.execute_for("FOR", remaining)

        print("✅ 우회 완료")
        return {"avoided": True, "turn": turn_cmd}

    def _decide_turn_direction(self) -> str:
        if not self.cap:
            return "LFT"

        detections = self.cap.get_detections()
        if not detections:
            return "LFT"

        nearest = min(detections, key=lambda d: d["distance_cm"])
        bbox = nearest.get("bbox")
        if not bbox:
            return "LFT"

        cx = (bbox[0] + bbox[2]) / 2
        return "RIT" if cx < 160 else "LFT"