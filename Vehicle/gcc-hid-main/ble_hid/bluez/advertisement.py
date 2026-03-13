"""LE advertisement object exported to BlueZ."""

from __future__ import annotations

from typing import Any

import dbus
import dbus.service

from ..constants import DBUS_PROP_IFACE, LE_ADVERTISEMENT_IFACE, DEVICE_NAME, GENERIC_HID_DEVICE_APPR
from ..exceptions import InvalidArgsException


class Advertisement(dbus.service.Object):
    def __init__(self, bus: dbus.Bus, path: str, adv_type: str = "peripheral"):
        super().__init__(bus, path)
        self.bus = bus
        self.path = path
        self.adv_type = adv_type
        self.service_uuids: list[str] = []
        self.local_name: str | None = DEVICE_NAME
        self.appearance: int | None = GENERIC_HID_DEVICE_APPR
        self.include_tx_power = True
        self.manufacturer_data: dict[int, bytes] = {}
        self.solicit_uuids: list[str] = []
        self.service_data: dict[str, bytes] = {}

    def get_properties(self) -> dict[str, dict[str, Any]]:
        props: dict[str, Any] = {"Type": self.adv_type}

        if self.service_uuids:
            props["ServiceUUIDs"] = dbus.Array(self.service_uuids, signature="s")
        if self.local_name is not None:
            props["LocalName"] = dbus.String(self.local_name)
        if self.appearance is not None:
            props["Appearance"] = dbus.UInt16(self.appearance)
        if self.include_tx_power:
            props["Includes"] = dbus.Array(["tx-power"], signature="s")
        if self.manufacturer_data:
            props["ManufacturerData"] = dbus.Dictionary(
                {dbus.UInt16(k): dbus.Array([dbus.Byte(b) for b in v], signature="y") for k, v in self.manufacturer_data.items()},
                signature="qv",
            )
        if self.solicit_uuids:
            props["SolicitUUIDs"] = dbus.Array(self.solicit_uuids, signature="s")
        if self.service_data:
            props["ServiceData"] = dbus.Dictionary(
                {dbus.String(k): dbus.Array([dbus.Byte(b) for b in v], signature="y") for k, v in self.service_data.items()},
                signature="sv",
            )

        return {LE_ADVERTISEMENT_IFACE: props}

    def get_path(self) -> dbus.ObjectPath:
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface: str) -> dict[str, Any]:
        if interface != LE_ADVERTISEMENT_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]

    @dbus.service.method(LE_ADVERTISEMENT_IFACE, in_signature="", out_signature="")
    def Release(self) -> None:
        print("[Advertisement] Released")
