from __future__ import annotations
import dbus
from enum import IntEnum
from .exception import NoDbusConnectionError, check_type


class Modifier(IntEnum):
    NONE = 0x0
    LCTRL = 1 << 0
    LSHIFT = 1 << 1
    LALT = 1 << 2
    LGUI = 1 << 3

    RCTRL = 1 << 4
    RSHIFT = 1 << 5
    RALT = 1 << 6
    RGUI = 1 << 7


class KeyboardOption(IntEnum):
    HOLD = 0x0
    TAP = 0x1


class Keyboard:
    _iKeyboard: dbus.Interface | None = None

    @staticmethod
    def press_keys(
        keys: list[str],
        modifier: Modifier = Modifier.NONE,
        opt: KeyboardOption = KeyboardOption.TAP,
    ):
        if not Keyboard._iKeyboard:
            raise NoDbusConnectionError()

        check_type(keys, list[str])
        check_type(modifier, Modifier)
        check_type(opt, KeyboardOption)
        Keyboard._iKeyboard.press_keys(keys, dbus.Byte(modifier), dbus.Int32(opt))

    def press_key(
        key: str,
        modifier: Modifier = Modifier.NONE,
        opt: KeyboardOption = KeyboardOption.TAP,
    ):
        if not Keyboard._iKeyboard:
            raise NoDbusConnectionError()
        check_type(key, str)
        check_type(modifier, Modifier)
        check_type(opt, KeyboardOption)
        Keyboard._iKeyboard.press_keys(key, dbus.Byte(modifier), dbus.Int32(opt))

    def releas_all(self):
        if not Keyboard._iKeyboard:
            raise NoDbusConnectionError()
        Keyboard._iKeyboard.press_keys()

    def send_string(
        string: str,
        modifier: Modifier = Modifier.NONE,
        opt: KeyboardOption = KeyboardOption.TAP,
    ):
        if not Keyboard._iKeyboard:
            raise NoDbusConnectionError()
        check_type(string, str)
        check_type(modifier, Modifier)
        check_type(opt, KeyboardOption)
        Keyboard._iKeyboard.press_keys(string, dbus.Byte(modifier), dbus.Int32(opt))
