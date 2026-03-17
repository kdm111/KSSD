from typing import NamedTuple

import numpy as np
from time import time, sleep

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
        self._before = time()

        self._hysteresis_band = (0.2, 0.8)
        self._center = None

    def _temporal_smoothing(
        self,
        new: np.ndarray,
        old: np.ndarray,
        dt: float,
        tau: float = 0.08,
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
                self._l_used = self._r_used = True
                return self._l_key, self._r_key
        return None
    
    def mouse(self, center: np.ndarray, dt):
        if self._center is None:
            self._center = center

        d_pos = self._center - center
        self._d_pos = self._temporal_smoothing(d_pos, self._d_pos, dt)

        print((d_pos[0] * 254).astype(int), (d_pos[1] * 254).astype(int))
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
            

        if r_value is None:
            self._center = None



        # print(self._wait, self.sensitive)