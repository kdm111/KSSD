"""Generic GATT building blocks: Service, Characteristic, Descriptor."""

from __future__ import annotations

from typing import Any

import dbus
import dbus.service

from ..constants import DBUS_PROP_IFACE, GATT_CHRC_IFACE, GATT_DESC_IFACE, GATT_SERVICE_IFACE
from ..exceptions import InvalidArgsException, NotSupportedException
from ..utils import to_dbus_byte_array


class Service(dbus.service.Object):
    def __init__(self, bus: dbus.Bus, index: int, uuid: str, primary: bool, app_path: str):
        self.path = f"{app_path}/service{index}"
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics: list[Characteristic] = []
        super().__init__(bus, self.path)

    def get_properties(self) -> dict[str, dict[str, Any]]:
        return {
            GATT_SERVICE_IFACE: {
                "UUID": self.uuid,
                "Primary": dbus.Boolean(self.primary),
                "Characteristics": dbus.Array([ch.get_path() for ch in self.characteristics], signature="o"),
            }
        }

    def get_path(self) -> dbus.ObjectPath:
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, characteristic: "Characteristic") -> None:
        self.characteristics.append(characteristic)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface: str) -> dict[str, Any]:
        if interface != GATT_SERVICE_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[GATT_SERVICE_IFACE]


class Characteristic(dbus.service.Object):
    def __init__(self, bus: dbus.Bus, index: int, uuid: str, flags: list[str], service: Service):
        self.path = f"{service.path}/char{index}"
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.service = service
        self.descriptors: list[Descriptor] = []
        self.notifying = False
        self.value = bytes()
        super().__init__(bus, self.path)

    def get_properties(self) -> dict[str, dict[str, Any]]:
        return {
            GATT_CHRC_IFACE: {
                "Service": self.service.get_path(),
                "UUID": self.uuid,
                "Flags": dbus.Array(self.flags, signature="s"),
                "Descriptors": dbus.Array([desc.get_path() for desc in self.descriptors], signature="o"),
            }
        }

    def get_path(self) -> dbus.ObjectPath:
        return dbus.ObjectPath(self.path)

    def add_descriptor(self, descriptor: "Descriptor") -> None:
        self.descriptors.append(descriptor)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface: str) -> dict[str, Any]:
        if interface != GATT_CHRC_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE, in_signature="a{sv}", out_signature="ay")
    def ReadValue(self, options: dict[str, Any]) -> dbus.Array:
        return to_dbus_byte_array(self.value)

    @dbus.service.method(GATT_CHRC_IFACE, in_signature="aya{sv}", out_signature="")
    def WriteValue(self, value: list[int], options: dict[str, Any]) -> None:
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE, in_signature="", out_signature="")
    def StartNotify(self) -> None:
        if self.notifying:
            return
        self.notifying = True
        print(f"[Notify] StartNotify: {self.path}")

    @dbus.service.method(GATT_CHRC_IFACE, in_signature="", out_signature="")
    def StopNotify(self) -> None:
        if not self.notifying:
            return
        self.notifying = False
        print(f"[Notify] StopNotify: {self.path}")

    @dbus.service.signal(DBUS_PROP_IFACE, signature="sa{sv}as")
    def PropertiesChanged(self, interface: str, changed: dict[str, Any], invalidated: list[str]):
        pass

    def set_value(self, value: bytes, notify: bool = True) -> None:
        self.value = value
        if notify and self.notifying:
            self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": to_dbus_byte_array(self.value)}, [])


class Descriptor(dbus.service.Object):
    def __init__(self, bus: dbus.Bus, index: int, uuid: str, flags: list[str], characteristic: Characteristic):
        self.path = f"{characteristic.path}/desc{index}"
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.chrc = characteristic
        self.value = bytes()
        super().__init__(bus, self.path)

    def get_properties(self) -> dict[str, dict[str, Any]]:
        return {
            GATT_DESC_IFACE: {
                "Characteristic": self.chrc.get_path(),
                "UUID": self.uuid,
                "Flags": dbus.Array(self.flags, signature="s"),
            }
        }

    def get_path(self) -> dbus.ObjectPath:
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface: str) -> dict[str, Any]:
        if interface != GATT_DESC_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[GATT_DESC_IFACE]

    @dbus.service.method(GATT_DESC_IFACE, in_signature="a{sv}", out_signature="ay")
    def ReadValue(self, options: dict[str, Any]) -> dbus.Array:
        return to_dbus_byte_array(self.value)

    @dbus.service.method(GATT_DESC_IFACE, in_signature="aya{sv}", out_signature="")
    def WriteValue(self, value: list[int], options: dict[str, Any]) -> None:
        raise NotSupportedException()
