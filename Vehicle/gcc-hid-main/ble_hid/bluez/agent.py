"""Simple pairing agent for development and early testing."""

from __future__ import annotations

import dbus
import dbus.service

from ..constants import AGENT_IFACE


class SimpleAgent(dbus.service.Object):
    def __init__(self, bus: dbus.Bus, path: str):
        super().__init__(bus, path)
        self.bus = bus
        self.path = path

    @dbus.service.method(AGENT_IFACE, in_signature="", out_signature="")
    def Release(self) -> None:
        print("[Agent] Release")

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="s")
    def RequestPinCode(self, device: dbus.ObjectPath) -> str:
        print(f"[Agent] RequestPinCode from {device}")
        return "000000"

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="u")
    def RequestPasskey(self, device: dbus.ObjectPath) -> dbus.UInt32:
        print(f"[Agent] RequestPasskey from {device}")
        return dbus.UInt32(0)

    @dbus.service.method(AGENT_IFACE, in_signature="ou", out_signature="")
    def DisplayPasskey(self, device: dbus.ObjectPath, passkey: int) -> None:
        print(f"[Agent] DisplayPasskey {device}: {passkey:06d}")

    @dbus.service.method(AGENT_IFACE, in_signature="os", out_signature="")
    def DisplayPinCode(self, device: dbus.ObjectPath, pincode: str) -> None:
        print(f"[Agent] DisplayPinCode {device}: {pincode}")

    @dbus.service.method(AGENT_IFACE, in_signature="ou", out_signature="")
    def RequestConfirmation(self, device: dbus.ObjectPath, passkey: int) -> None:
        print(f"[Agent] RequestConfirmation {device}: {passkey:06d}")

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="")
    def RequestAuthorization(self, device: dbus.ObjectPath) -> None:
        print(f"[Agent] RequestAuthorization {device}")

    @dbus.service.method(AGENT_IFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, device: dbus.ObjectPath, uuid: str) -> None:
        print(f"[Agent] AuthorizeService {device}, uuid={uuid}")

    @dbus.service.method(AGENT_IFACE, in_signature="", out_signature="")
    def Cancel(self) -> None:
        print("[Agent] Cancel")
