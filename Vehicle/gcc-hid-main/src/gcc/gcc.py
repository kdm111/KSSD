import dbus
import dbus.bus

from .constants import BUS_NAME, KEYBOARD_INTERFACE, KEYBOARD_OBJECT_PATH
from .keyboard import Keyboard


class GCC:
    def __init__(self):
        bus = dbus.SystemBus()

        self._iKeyboard = dbus.Interface(
            bus.get_object(BUS_NAME, KEYBOARD_OBJECT_PATH), KEYBOARD_INTERFACE
        )
        Keyboard._iKeyboard = self._iKeyboard

