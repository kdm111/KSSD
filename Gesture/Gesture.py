import numpy as np
import threading
from time import time, sleep
from gcc import Keyboard, Mouse

_RAW_TO_GESTURE = {
    # reset
    0b0000000: 0,
    # thumbs ~ little
    0b1000000: 1,
    0b1100000: 2,
    0b1110000: 3,
    0b1111000: 4,
    0b1111100: 5,
    0b0111100: 6,
    # 따로따로 손피는거
    0b0100000: 7,
    0b0010000: 8,
    0b0001000: 9,
    0b0000100: 10,
}

_DATA_HEADER = [
    "th1",
    "th2",
    "th3",
    "in1",
    "in2",
    "in3",
    "mi1",
    "mi2",
    "mi3",
    "ri1",
    "ri2",
    "ri3",
    "pi1",
    "pi2",
    "pi3",
    "hand_side",
]

_LABEL_HEADER = [
    "th_open",
    "in_open",
    "mi_open",
    "ri_open",
    "pi_open",
    "ti_touch",
    "tm_touch",
]


class GestureController:
    def __init__(self):
        self._l_value = np.array([0.0] * len(_LABEL_HEADER))
        self._r_value = np.array([0.0] * len(_LABEL_HEADER))

        self._l_key = 0
        self._r_key = 0
        self._l_used = False
        self._r_used = False
        self._d_pos = np.array([0.0, 0.0, 0.0])
        self._wait = 0
        self.sensitive = 0.1
        self.mouse_sensitive = 100
        self._before = time()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._mouse_thread = None

        self._hysteresis_band = (0.2, 0.8)
        self._center = None

        self.start_mouse()

        self.alphabet_map = {
            1: ["A", "B", "C", "D", "E", "F"],
            2: ["G", "H", "I", "J", "K", "L"],
            3: ["M", "N", "O", "P", "Q", "R"],
            4: ["S", "T", "U", "V", "W", "X"],
            5: ["Y", "Z", "1", "2", "3", "4"],
            6: ["5", "6", "7", "8", "9", "0"],
        }

    def _temporal_smoothing(
        self,
        new: np.ndarray,
        old: np.ndarray,
        dt: float,
        tau: float = 0.12,
    ) -> np.ndarray:
        """
        dt-aware exponential smoothing (continuous-time EMA)

        Parameters
        ----------
        new : np.ndarray
            Current observation.
        old : np.ndarray
            Previous smoothed output.
        dt : float
            Time delta in seconds.
        tau : float
            Time constant in seconds.
            Larger tau => smoother but slower response.
        """
        if dt <= 0:
            return old

        alpha = 1.0 - np.exp(-dt / tau)
        return old + alpha * (new - old)

    def probs_to_int(self, probs, old):
        if old is None:
            return

        and_value = 0
        or_value = 0
        for p in probs:
            and_value = (and_value << 1) | int(0 if p < self._hysteresis_band[0] else 1)
            or_value = (or_value << 1) | int(1 if p > self._hysteresis_band[1] else 0)

        old &= and_value
        old |= or_value
        return old

    def keyboard(self):
        if self._wait > self.sensitive:
            if self._l_used and self._r_used:
                return None
            
            self._l_used = self._r_used = True
            print(self._l_key, self._r_key)
            tmp = self.alphabet_map.get(_RAW_TO_GESTURE.get(self._l_key, None), None)
            if tmp is not None:
                key = tmp[_RAW_TO_GESTURE.get(self._r_key, None) - 1]
                if key is not None:
                    Keyboard.press_key(key)

        return None

    def mouse_work_process(self):
        while not self._stop_event.is_set():
            with self._lock:
                d_pos = self._d_pos.copy()
                if not self._r_key & 0b0001100:
                    Mouse.mouse(0, 0, 0)
                    self._d_pos = np.zeros((3,))
                    sleep(0.05)
                    continue
            dx = d_pos[0].astype(int)
            dy = d_pos[1].astype(int)

            Mouse.mouse(
                1 if self._r_key & 0b10 else 0,
                -dx,
                -dy,
            )

            sleep(0.01)  # 10ms = 100Hz

    def start_mouse(self):
        if self._mouse_thread is None or not self._mouse_thread.is_alive():
            self._stop_event.clear()
            self._mouse_thread = threading.Thread(
                target=self.mouse_work_process, daemon=True
            )
            self._mouse_thread.start()

    def stop_mouse(self):
        self._stop_event.set()
        if self._mouse_thread is not None:
            self._mouse_thread.join()

    def mouse(self, center: np.ndarray, dt):
        if self._center is None or self._r_key == 0b0:
            self._center = center

        d_pos = (self._center - center) * self.mouse_sensitive
        self._d_pos = self._temporal_smoothing(d_pos, self._d_pos, dt)
        # self._d_pos = d_pos

        # print((d_pos[0] * 254).astype(int), (d_pos[1] * 254).astype(int))
        self._center = center

    """
    Return:
        keyboard key
    """

    def update(self, gesture_results: dict, center: np.ndarray) -> int:
        current = time()
        dt = current - self._before
        self._before = current
        self._wait += dt

        l_value = gesture_results.get("left", None)
        if l_value is not None:
            new_l_value = self._temporal_smoothing(l_value, self._l_value, dt)
            self._l_value = new_l_value
            new_key = self.probs_to_int(new_l_value, self._l_key)
            if self._l_key != new_key:
                self._l_used = False
                self._wait = 0
            self._l_key = new_key

        else:
            self._l_value = np.array([0.0] * len(_LABEL_HEADER))
            self._l_key = 0b0

        r_value = gesture_results.get("right", None)
        if r_value is not None:
            new_r_value = self._temporal_smoothing(r_value, self._r_value, dt)
            self._r_value = new_r_value
            new_key = self.probs_to_int(new_r_value, self._r_key)
            if self._r_key != new_key:
                self._r_used = False
                self._wait = 0
            self._r_key = new_key
        else:
            self._r_value = np.array([0.0] * len(_LABEL_HEADER))
            self._r_key = 0b0

        # Keyboard
        if l_value is not None and r_value is not None:
            return self.keyboard()

        # Control
        if r_value is None and l_value is not None:
            # TODO
            pass

        # Mouse
        if r_value is not None and l_value is None and center is not None:
            self.mouse(center, dt)

        # print(self._wait, self.sensitive)
