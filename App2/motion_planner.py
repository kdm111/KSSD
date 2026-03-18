"""
MotionPlanner
━━━━━━━━━━━━
세션의 CommandLog를 기반으로 자율 행동 계획을 생성하고 실행.

API:
    planner.return_home()                  # 전체 역추적 귀환
    planner.replay()                       # 전체 재실행
    planner.undo_command(cmd_log_dict)      # 명령 1개 되돌리기
    planner.redo_command(cmd_log_dict)      # 명령 1개 다시 실행
    planner.cancel()                       # 실행 중 취소
"""
import time
import threading
from DB.repository import get_session_commands, record_command


REVERSE_MAP = {
    "FOR": "BAK",
    "BAK": "FOR",
    "LFT": "RIT",
    "RIT": "LFT",
    "SPN": "SPN",
}

SKIP_COMMANDS = {"STP", "READY", ""}


class MotionPlanner:

    def __init__(self, device_id: str, session_id: str, send_fn):
        self.device_id = device_id
        self.session_id = session_id
        self.send_fn = send_fn

        self.is_running = False
        self.is_cancelled = False
        self.current_step = 0
        self.total_steps = 0
        self._thread = None

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 공개 API
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def return_home(self, callback=None) -> bool:
        """전체 세션 역추적 귀환"""
        commands = self._get_move_commands()
        if not commands:
            if callback: callback("EMPTY", "실행할 명령 없음")
            return False

        commands.reverse()
        plan = []
        for cmd in commands:
            rev = REVERSE_MAP.get(cmd["command"])
            dur = self._get_duration(cmd)
            if rev and dur > 0:
                plan.append({"command": rev, "duration": dur, "speed": cmd["speed"]})

        return self.start_plan(plan, "RETURN_HOME", callback)

    def replay(self, callback=None) -> bool:
        """전체 세션 재실행"""
        commands = self._get_move_commands()
        if not commands:
            if callback: callback("EMPTY", "실행할 명령 없음")
            return False

        plan = []
        for cmd in commands:
            dur = self._get_duration(cmd)
            if dur > 0:
                plan.append({"command": cmd["command"], "duration": dur, "speed": cmd["speed"]})

        return self.start_plan(plan, "REPLAY", callback)

    def undo_command(self, cmd_log: dict, callback=None) -> bool:
        """
        명령 1개를 반대로 실행 (UNDO).
        cmd_log: CommandLog의 dict (command, speed, duration, actual_duration, source)
        """
        rev_cmd = REVERSE_MAP.get(cmd_log.get("command"))
        duration = self._get_duration(cmd_log)

        if not rev_cmd or duration <= 0:
            if callback: callback("INVALID", f"되돌릴 수 없는 명령: {cmd_log.get('command')}")
            return False

        plan = [{"command": rev_cmd, "duration": duration, "speed": cmd_log.get("speed", 0.5)}]
        return self.start_plan(plan, "UNDO", callback)

    def redo_command(self, cmd_log: dict, callback=None) -> bool:
        """
        명령 1개를 그대로 재실행 (DO/REDO).
        cmd_log: CommandLog의 dict
        """
        cmd = cmd_log.get("command")
        duration = self._get_duration(cmd_log)

        if not cmd or cmd in SKIP_COMMANDS or duration <= 0:
            if callback: callback("INVALID", f"재실행 불가: {cmd}")
            return False

        plan = [{"command": cmd, "duration": duration, "speed": cmd_log.get("speed", 0.5)}]
        return self.start_plan(plan, "REDO", callback)

    def cancel(self):
        self.is_cancelled = True
        self.send_fn("STP", 0)
        print("🛑 플랜 취소")

    def get_status(self) -> dict:
        return {
            "is_running": self.is_running,
            "is_cancelled": self.is_cancelled,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
        }

    def get_preview(self, plan_type: str = "RETURN_HOME") -> list:
        commands = self._get_move_commands()
        if not commands:
            return []

        if plan_type == "RETURN_HOME":
            commands.reverse()
            return [
                {"command": REVERSE_MAP.get(c["command"], c["command"]),
                 "duration": self._get_duration(c), "speed": c["speed"],
                 "original": c["command"]}
                for c in commands
                if REVERSE_MAP.get(c["command"]) and self._get_duration(c) > 0
            ]
        else:
            return [
                {"command": c["command"], "duration": self._get_duration(c), "speed": c["speed"]}
                for c in commands if self._get_duration(c) > 0
            ]

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 실행 엔진 (공통)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def start_plan(self, plan: list, plan_type: str, callback=None) -> bool:
        """명령 시퀀스를 별도 스레드에서 순차 실행"""
        if self.is_running:
            if callback: callback("BUSY", "이미 실행 중")
            return False
        if not plan:
            if callback: callback("EMPTY", "실행할 명령 없음")
            return False

        self.total_steps = len(plan)
        self.current_step = 0
        self.is_running = True
        self.is_cancelled = False

        def run():
            print(f"🚀 {plan_type} 시작 ({self.total_steps}단계)")

            for i, step in enumerate(plan):
                if self.is_cancelled:
                    print(f"❌ {plan_type} 취소 (step {i+1})")
                    if callback: callback("CANCELLED", f"step {i+1}에서 취소")
                    break

                self.current_step = i + 1
                cmd = step["command"]
                dur = step["duration"]
                spd = step["speed"]

                ok = self.send_fn(cmd, dur)
                if not ok:
                    self.send_fn("STP", 0)
                    print(f"❌ 전송 실패 (step {i+1})")
                    if callback: callback("FAILED", f"step {i+1} 전송 실패")
                    break

                print(f"  [{i+1}/{self.total_steps}] {cmd} × {dur:.1f}s (spd={spd})")

                # 대기 (0.1초 단위로 취소 체크)
                waited = 0.0
                while waited < dur:
                    if self.is_cancelled:
                        break
                    time.sleep(min(0.1, dur - waited))
                    waited += 0.1
            else:
                self.send_fn("STP", 0)
                print(f"✅ {plan_type} 완료")
                if callback: callback("COMPLETED", "정상 완료")

            self.is_running = False

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
        return True

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 내부
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _get_move_commands(self) -> list:
        all_cmds = get_session_commands(self.session_id)
        return [c for c in all_cmds if c["command"] not in SKIP_COMMANDS]

    def _get_duration(self, cmd: dict) -> float:
        if cmd.get("source") == "PC":
            return cmd.get("duration", 0)
        else:
            ad = cmd.get("actual_duration")
            return ad if ad and ad > 0 else 0