"""Utility functions shared across the package."""

from __future__ import annotations

from typing import Any, Optional

import dbus

from .constants import ADAPTER_IFACE, BLUEZ_SERVICE_NAME, DBUS_OM_IFACE, DBUS_PROP_IFACE


def to_dbus_byte_array(data: bytes) -> dbus.Array:
    return dbus.Array([dbus.Byte(b) for b in data], signature="y")


# TODO Optimization

def find_adapter(bus: dbus.Bus, required_ifaces: Optional[list[str]] = None) -> str:
    """Return /org/bluez/hciX path that exposes all required interfaces."""
    required_ifaces = required_ifaces or []

    obj = bus.get_object(BLUEZ_SERVICE_NAME, "/")
    om = dbus.Interface(obj, DBUS_OM_IFACE)
    managed_objects = om.GetManagedObjects()

    for path, ifaces in managed_objects.items():
        if ADAPTER_IFACE not in ifaces:
            continue
        if all(req in ifaces for req in required_ifaces):
            return path

    raise RuntimeError(f"No adapter found with interfaces: {required_ifaces}")


def set_adapter_property(bus: dbus.Bus, adapter_path: str, prop: str, value: Any) -> None:
    adapter_obj = bus.get_object(BLUEZ_SERVICE_NAME, adapter_path)
    props = dbus.Interface(adapter_obj, DBUS_PROP_IFACE)
    props.Set(ADAPTER_IFACE, prop, value)
