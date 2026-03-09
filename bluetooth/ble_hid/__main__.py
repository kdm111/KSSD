"""Executable entry point for registering the BLE HID peripheral."""

from __future__ import annotations

import os
import signal
import sys

import dbus
import dbus.bus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib

from .api.api import ApiService

from .bluez.advertisement import Advertisement
from .bluez.agent import SimpleAgent
from .bluez.application import Application
from .constants import (
    BUS_NAME,
    DEVICE_NAME,
    ADV_PATH,
    AGENT_IFACE,
    AGENT_MGR_IFACE,
    AGENT_PATH,
    APP_PATH,
    BLUEZ_SERVICE_NAME,
    GATT_MGR_IFACE,
    LE_ADVERTISING_MGR_IFACE,
    UUID_BATTERY_SERVICE,
    UUID_DEVICE_INFO_SERVICE,
    UUID_HID_SERVICE,
)
from .demo import DemoInputDriver
from .hid.services import BatteryService, DeviceInfoService, HIDService
from .utils import find_adapter, set_adapter_property


mainloop: GLib.MainLoop | None = None


def register_app_cb() -> None:
    print("[BlueZ] GATT application registered")


def register_app_error_cb(error) -> None:
    print(f"[BlueZ] Failed to register application: {error}")
    if mainloop is not None:
        mainloop.quit()


def register_ad_cb() -> None:
    print("[BlueZ] Advertisement registered")


def register_ad_error_cb(error) -> None:
    print(f"[BlueZ] Failed to register advertisement: {error}")
    if mainloop is not None:
        mainloop.quit()


def main() -> None:
    global mainloop

    if os.geteuid() != 0:
        print("This program usually needs root privileges.")
        sys.exit(1)

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    adapter_path = find_adapter(
        bus, required_ifaces=[GATT_MGR_IFACE, LE_ADVERTISING_MGR_IFACE]
    )
    print(f"[BlueZ] Using adapter: {adapter_path}")

    set_adapter_property(bus, adapter_path, "Powered", dbus.Boolean(True))
    set_adapter_property(bus, adapter_path, "Pairable", dbus.Boolean(True))
    set_adapter_property(bus, adapter_path, "Discoverable", dbus.Boolean(True))
    try:
        set_adapter_property(bus, adapter_path, "Alias", dbus.String(DEVICE_NAME))
    except Exception as exc:
        print(f"[BlueZ] Warning: failed to set Alias: {exc}")

    adapter_obj = bus.get_object(BLUEZ_SERVICE_NAME, adapter_path)
    service_manager = dbus.Interface(adapter_obj, GATT_MGR_IFACE)
    advertising_manager = dbus.Interface(adapter_obj, LE_ADVERTISING_MGR_IFACE)

    agent_mgr_obj = bus.get_object(BLUEZ_SERVICE_NAME, "/org/bluez")
    agent_manager = dbus.Interface(agent_mgr_obj, AGENT_MGR_IFACE)

    _agent = SimpleAgent(bus, AGENT_PATH)
    agent_manager.RegisterAgent(AGENT_PATH, "NoInputNoOutput")
    agent_manager.RequestDefaultAgent(AGENT_PATH)
    print("[BlueZ] Agent registered")

    app = Application(bus, APP_PATH)
    hid_service = HIDService(bus, 0, APP_PATH)
    battery_service = BatteryService(bus, 1, APP_PATH)
    device_info_service = DeviceInfoService(bus, 2, APP_PATH)
    _api = ApiService(bus, hid_service)

    app.add_service(hid_service)
    app.add_service(battery_service)
    app.add_service(device_info_service)

    adv = Advertisement(bus, ADV_PATH, adv_type="peripheral")
    # TODO Have to remove? It dosen't need anymore
    # adv.local_name = "Pi5 BLE HID"
    # adv.appearance = 0x03C0
    adv.service_uuids = [
        UUID_HID_SERVICE,
        UUID_BATTERY_SERVICE,
        UUID_DEVICE_INFO_SERVICE,
    ]

    service_manager.RegisterApplication(
        app.get_path(),
        {},
        reply_handler=register_app_cb,
        error_handler=register_app_error_cb,
    )
    advertising_manager.RegisterAdvertisement(
        adv.get_path(),
        {},
        reply_handler=register_ad_cb,
        error_handler=register_ad_error_cb,
    )

    # TODO Delete
    # demo = DemoInputDriver(hid_service)
    # GLib.timeout_add_seconds(1, demo.tick)

    def handle_signal(_sig, _frame) -> None:
        print("\n[Main] Caught signal, cleaning up...")
        try:
            advertising_manager.UnregisterAdvertisement(adv.get_path())
            print("[BlueZ] Advertisement unregistered")
        except Exception as exc:
            print(f"[BlueZ] Advertisement unregister warning: {exc}")
        try:
            agent_manager.UnregisterAgent(AGENT_PATH)
            print("[BlueZ] Agent unregistered")
        except Exception as exc:
            print(f"[BlueZ] Agent unregister warning: {exc}")
        if mainloop is not None:
            mainloop.quit()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    print("[Main] Running main loop")
    mainloop = GLib.MainLoop()
    mainloop.run()


if __name__ == "__main__":
    main()
