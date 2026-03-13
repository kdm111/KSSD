"""Simple demo input generator used before connecting gesture/CV pipeline."""

from __future__ import annotations

from .hid.services import HIDService


a = 4


class DemoInputDriver:
    def __init__(self, hid_service: HIDService):
        self.hid = hid_service
        self._phase = 0

    def tick(self) -> bool:
        global a
        if not (self.hid.keyboard_input.notifying or self.hid.mouse_input.notifying):
            return True

        if self._phase == 0:
            # self.hid.keyboard_input.send_keys(modifiers=0x00, keys=[0x04])
            self.hid.keyboard_input.send_keys(modifiers=0x00, keys=[a])
            a += 1
        elif self._phase == 1:
            self.hid.keyboard_input.release_all()
        # elif self._phase == 0:
        #     # self.hid.mouse_input.send_mouse(buttons=0, dx=0, dy=0, wheel=100)
        #     self.hid.mouse_input.send_mouse(buttons=0, dx=a, dy=a, wheel=0)
        # elif self._phase == 1:
        #     self.hid.mouse_input.send_mouse(buttons=0, dx=0, dy=0, wheel=0)
        else:
            self._phase = -1

        self._phase += 1
        return True
