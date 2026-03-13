"""Application root implementing ObjectManager for BlueZ GATT registration."""

from __future__ import annotations

from typing import Any

import dbus
import dbus.service

from ..constants import DBUS_OM_IFACE


class Application(dbus.service.Object):
    """GATT application root exported to BlueZ."""

    def __init__(self, bus: dbus.Bus, path: str):
        super().__init__(bus, path)
        self.bus = bus
        self.path = path
        self.services: list[Any] = []

    def add_service(self, service: Any) -> None:
        self.services.append(service)

    def get_path(self) -> dbus.ObjectPath:
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_OM_IFACE, out_signature="a{oa{sa{sv}}}")
    def GetManagedObjects(self) -> dict[dbus.ObjectPath, dict[str, dict[str, Any]]]:
        response: dict[dbus.ObjectPath, dict[str, dict[str, Any]]] = {}

        for service in self.services:
            response[service.get_path()] = service.get_properties()
            for chrc in service.characteristics:
                response[chrc.get_path()] = chrc.get_properties()
                for desc in chrc.descriptors:
                    response[desc.get_path()] = desc.get_properties()

        return response
