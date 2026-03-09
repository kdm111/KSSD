import dbus
import dbus.service

from ..constants import KEYBOARD_API_PATH, BUS_NAME
from ..hid.services import KeyboardInputReportCharacteristic
from .keymap import HID_MAP

class KeyboardApiService(dbus.service.Object):
    def __init__(self, bus, keyboard_input: KeyboardInputReportCharacteristic):
        self._keyboard_input = keyboard_input
        super().__init__(bus, KEYBOARD_API_PATH)

    @dbus.service.method(dbus_interface=BUS_NAME, in_signature="asyi")
    def press_keys(self, keys: list[str], modifier: dbus.Byte, opt: dbus.Int32):
        hid_keys = [HID_MAP.get(key.lower(), 0) for key in keys]
        self._keyboard_input.send_keys(modifier, hid_keys)

    @dbus.service.method(dbus_interface=BUS_NAME, in_signature="syi")
    def press_key(self, key: str, modifier: dbus.Byte, opt: dbus.Int32):
        hid_keys = [HID_MAP.get(key.lower(), 0), 0, 0, 0, 0, 0]
        self._keyboard_input.send_keys(modifier, hid_keys)

    @dbus.service.method(dbus_interface=BUS_NAME)
    def releas_all(self):
        hid_keys = [0 for _ in range(6)]
        self._modifiers = 0
        self._keyboard_input.send_keys(modifiers=self._modifiers, keys=hid_keys)

    @dbus.service.method(dbus_interface=BUS_NAME, in_signature="syi")
    def sent_string(self, string, modifier: dbus.Byte, opt: dbus.Int32):
        for c in string:
            self.press_key(modifier, c)
