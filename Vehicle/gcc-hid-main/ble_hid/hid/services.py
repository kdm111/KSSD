"""Concrete HID, Battery, and Device Information services."""

from __future__ import annotations

from typing import Any

import dbus

from ..bluez.gatt import Characteristic, Descriptor, Service
from ..constants import (
    REPORT_TYPE_INPUT,
    REPORT_TYPE_OUTPUT,
    UUID_BATTERY_LEVEL,
    UUID_BATTERY_SERVICE,
    UUID_DEVICE_INFO_SERVICE,
    UUID_HID_CONTROL_POINT,
    UUID_HID_INFORMATION,
    UUID_HID_SERVICE,
    UUID_MANUFACTURER_NAME,
    UUID_MODEL_NUMBER,
    UUID_PNP_ID,
    UUID_PROTOCOL_MODE,
    UUID_REPORT,
    UUID_REPORT_MAP,
    UUID_REPORT_REFERENCE_DESC,
)
from ..exceptions import FailedException, InvalidValueLengthException
from .report_map import build_hid_report_map


class ReportReferenceDescriptor(Descriptor):
    def __init__(self, bus: dbus.Bus, index: int, characteristic: Characteristic, report_id: int, report_type: int):
        super().__init__(bus, index, UUID_REPORT_REFERENCE_DESC, ["read"], characteristic)
        self.value = bytes([report_id, report_type])


class HIDInformationCharacteristic(Characteristic):
    def __init__(self, bus: dbus.Bus, index: int, service: Service):
        super().__init__(bus, index, UUID_HID_INFORMATION, ["read"], service)
        self.value = bytes([0x11, 0x01, 0x00, 0x02])


class ReportMapCharacteristic(Characteristic):
    def __init__(self, bus: dbus.Bus, index: int, service: Service):
        super().__init__(bus, index, UUID_REPORT_MAP, ["read"], service)
        self.value = build_hid_report_map()


class ProtocolModeCharacteristic(Characteristic):
    def __init__(self, bus: dbus.Bus, index: int, service: Service):
        super().__init__(bus, index, UUID_PROTOCOL_MODE, ["read", "write-without-response"], service)
        self.value = bytes([0x01])

    def WriteValue(self, value: list[int], options: dict[str, Any]) -> None:
        if len(value) != 1:
            raise InvalidValueLengthException()
        mode = int(value[0])
        if mode not in (0x00, 0x01):
            raise FailedException("Invalid protocol mode")
        self.value = bytes([mode])
        print(f"[HID] Protocol Mode -> {'BOOT' if mode == 0x00 else 'REPORT'}")


class HIDControlPointCharacteristic(Characteristic):
    def __init__(self, bus: dbus.Bus, index: int, service: Service):
        super().__init__(bus, index, UUID_HID_CONTROL_POINT, ["write-without-response"], service)
        self.value = bytes([0x01])

    def WriteValue(self, value: list[int], options: dict[str, Any]) -> None:
        if len(value) != 1:
            raise InvalidValueLengthException()
        self.value = bytes([int(value[0])])
        print(f"[HID] Control Point -> {self.value[0]}")


class KeyboardInputReportCharacteristic(Characteristic):
    REPORT_ID = 0x01
    # REPORT_ID = 0xA1

    def __init__(self, bus: dbus.Bus, index: int, service: Service):
        super().__init__(bus, index, UUID_REPORT, ["read", "notify"], service)
        self.value = bytes([0x00, 0x00, 0, 0, 0, 0, 0, 0])
        self.add_descriptor(ReportReferenceDescriptor(bus, 0, self, self.REPORT_ID, REPORT_TYPE_INPUT))

    def send_keys(self, modifiers: int = 0, keys: list[int] | None = None) -> None:
        keys = keys or []
        keys = keys[:6] + [0] * (6 - len(keys))
        report = bytes([modifiers & 0xFF, 0x00] + keys)
        self.set_value(report, notify=True)
        print(f"[HID] Keyboard report sent: {report.hex()}")

    def release_all(self) -> None:
        self.send_keys(0, [])


class KeyboardOutputReportCharacteristic(Characteristic):
    REPORT_ID = 0x01

    def __init__(self, bus: dbus.Bus, index: int, service: Service):
        super().__init__(bus, index, UUID_REPORT, ["read", "write", "write-without-response"], service)
        self.value = bytes([self.REPORT_ID, 0x00])
        self.led_state = 0x00
        self.add_descriptor(ReportReferenceDescriptor(bus, 0, self, self.REPORT_ID, REPORT_TYPE_OUTPUT))

    def WriteValue(self, value: list[int], options: dict[str, Any]) -> None:
        if len(value) < 1:
            raise InvalidValueLengthException()

        raw = bytes(value)
        if len(raw) == 1:
            self.led_state = raw[0]
            self.value = bytes([self.REPORT_ID, self.led_state])
        else:
            self.led_state = raw[-1]
            self.value = raw

        print(f"[HID] Keyboard LED Output -> 0x{self.led_state:02x}")


class MouseInputReportCharacteristic(Characteristic):
    REPORT_ID = 0x02

    def __init__(self, bus: dbus.Bus, index: int, service: Service):
        super().__init__(bus, index, UUID_REPORT, ["read", "notify"], service)
        self.value = bytes([0x00, 0x00, 0x00, 0x00])
        self.add_descriptor(ReportReferenceDescriptor(bus, 0, self, self.REPORT_ID, REPORT_TYPE_INPUT))

    @staticmethod
    def _s8(v: int) -> int:
        v = max(-127, min(127, v))
        return v & 0xFF

    def send_mouse(self, buttons: int = 0, dx: int = 0, dy: int = 0, wheel: int = 0) -> None:
        report = bytes([buttons & 0x07, self._s8(dx), self._s8(dy), self._s8(wheel)])
        self.set_value(report, notify=True)
        print(f"[HID] Mouse report sent: {report}")

    def release_buttons(self) -> None:
        self.send_mouse(buttons=0, dx=0, dy=0, wheel=0)


class BatteryLevelCharacteristic(Characteristic):
    def __init__(self, bus: dbus.Bus, index: int, service: Service):
        super().__init__(bus, index, UUID_BATTERY_LEVEL, ["read", "notify"], service)
        self.level = 100
        self.value = bytes([self.level])

    def set_level(self, level: int) -> None:
        self.level = max(0, min(100, level))
        self.set_value(bytes([self.level]), notify=True)
        print(f"[Battery] level={self.level}")


class StringCharacteristic(Characteristic):
    def __init__(self, bus: dbus.Bus, index: int, service: Service, uuid: str, text: str):
        super().__init__(bus, index, uuid, ["read"], service)
        self.value = text.encode("utf-8")


class PnPIDCharacteristic(Characteristic):
    def __init__(self, bus: dbus.Bus, index: int, service: Service):
        super().__init__(bus, index, UUID_PNP_ID, ["read"], service)
        vendor_id_source = 0x02
        vendor_id = 0xFFFF
        product_id = 0x0001
        product_version = 0x0001
        self.value = bytes([
            vendor_id_source,
            vendor_id & 0xFF,
            (vendor_id >> 8) & 0xFF,
            product_id & 0xFF,
            (product_id >> 8) & 0xFF,
            product_version & 0xFF,
            (product_version >> 8) & 0xFF,
        ])


class HIDService(Service):
    def __init__(self, bus: dbus.Bus, index: int, app_path: str):
        super().__init__(bus, index, UUID_HID_SERVICE, True, app_path)
        self.hid_info = HIDInformationCharacteristic(bus, 0, self)
        self.report_map = ReportMapCharacteristic(bus, 1, self)
        self.protocol_mode = ProtocolModeCharacteristic(bus, 2, self)
        self.keyboard_input = KeyboardInputReportCharacteristic(bus, 3, self)
        self.keyboard_output = KeyboardOutputReportCharacteristic(bus, 4, self)
        self.mouse_input = MouseInputReportCharacteristic(bus, 5, self)
        self.control_point = HIDControlPointCharacteristic(bus, 6, self)

        for ch in [
            self.hid_info,
            self.report_map,
            self.protocol_mode,
            self.keyboard_input,
            self.keyboard_output,
            self.mouse_input,
            self.control_point,
        ]:
            self.add_characteristic(ch)


class BatteryService(Service):
    def __init__(self, bus: dbus.Bus, index: int, app_path: str):
        super().__init__(bus, index, UUID_BATTERY_SERVICE, True, app_path)
        self.battery_level = BatteryLevelCharacteristic(bus, 0, self)
        self.add_characteristic(self.battery_level)


class DeviceInfoService(Service):
    def __init__(self, bus: dbus.Bus, index: int, app_path: str):
        super().__init__(bus, index, UUID_DEVICE_INFO_SERVICE, True, app_path)
        self.manufacturer = StringCharacteristic(bus, 0, self, UUID_MANUFACTURER_NAME, "Bomin Labs")
        self.model = StringCharacteristic(bus, 1, self, UUID_MODEL_NUMBER, "Pi5 BLE HID")
        self.pnp_id = PnPIDCharacteristic(bus, 2, self)

        for ch in [self.manufacturer, self.model, self.pnp_id]:
            self.add_characteristic(ch)
