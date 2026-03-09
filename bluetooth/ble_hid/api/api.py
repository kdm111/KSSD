from __future__ import annotations
import dbus
import dbus.bus
import dbus.service

from .keyboard import KeyboardApiService
from ..constants import API_PATH, BUS_NAME
from ..hid.services import HIDService


class ApiService(dbus.service.Object):


    def __init__(self, bus: dbus.bus, hid_service: HIDService):
        bus_name = dbus.service.BusName(BUS_NAME, bus=bus)
        # TODO Fix !!
        self.keyboard_api = KeyboardApiService(bus_name.get_bus(), hid_service.keyboard_input)
        super().__init__(bus_name, API_PATH)
