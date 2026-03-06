#!/usr/bin/python3
"""
Bluetooth HID keyboard emulator DBUS Service

Original idea taken from:
http://yetanotherpointlesstechblog.blogspot.com/2016/04/emulating-bluetooth-keyboard-with.html

Moved to Python 3 and tested with BlueZ 5.43
"""
import os
import sys
import dbus
import dbus.service
import socket
import selectors
import threading
import time


from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop


class HumanInterfaceDeviceProfile(dbus.service.Object):
    """
    BlueZ D-Bus Profile for HID
    """

    fd = -1

    @dbus.service.method("org.bluez.Profile1", in_signature="", out_signature="")
    def Release(self):
        print("Release")
        mainloop.quit()

    @dbus.service.method("org.bluez.Profile1", in_signature="oha{sv}", out_signature="")
    def NewConnection(self, path, fd, properties):
        self.fd = fd.take()
        print("NewConnection({}, {})".format(path, self.fd))
        for key in properties.keys():
            if key == "Version" or key == "Features":
                print("  {} = 0x{:04x}".format(key, properties[key]))
            else:
                print("  {} = {}".format(key, properties[key]))

    @dbus.service.method("org.bluez.Profile1", in_signature="o", out_signature="")
    def RequestDisconnection(self, path):
        print("RequestDisconnection {}".format(path))

        if self.fd > 0:
            os.close(self.fd)
            self.fd = -1


class BTKbDevice:
    """
    create a bluetooth device to emulate a HID keyboard
    """

    MY_DEV_NAME = "BT_HID_Keyboard"
    # Service port - must match port configured in SDP record
    P_CTRL = 17
    # Service port - must match port configured in SDP record#Interrrupt port
    P_INTR = 19
    # BlueZ dbus
    PROFILE_DBUS_PATH = "/bluez/yaptb/btkb_profile"
    ADAPTER_IFACE = "org.bluez.Adapter1"
    DEVICE_INTERFACE = "org.bluez.Device1"
    DBUS_PROP_IFACE = "org.freedesktop.DBus.Properties"
    DBUS_OM_IFACE = "org.freedesktop.DBus.ObjectManager"

    # file path of the sdp record to laod
    install_dir = os.path.dirname(os.path.realpath(__file__))
    SDP_RECORD_PATH = os.path.join(install_dir, "sdp_record.xml")
    # UUID for HID service (1124)
    # https://www.bluetooth.com/specifications/assigned-numbers/service-discovery
    UUID = "00001124-0000-1000-8000-00805f9b34fb"

    def __init__(self, hci=0):
        self.scontrol = None
        self.ccontrol = None  # Socket object for control
        self.sinterrupt = None
        self.cinterrupt = None  # Socket object for interrupt
        self.sock_lock = threading.Lock()
        self.listener_thread = None
        self.dev_path = "/org/bluez/hci{}".format(hci)
        print("Setting up BT device")
        self.bus = dbus.SystemBus()
        self.adapter_methods = dbus.Interface(
            self.bus.get_object("org.bluez", self.dev_path), self.ADAPTER_IFACE
        )
        self.adapter_property = dbus.Interface(
            self.bus.get_object("org.bluez", self.dev_path), self.DBUS_PROP_IFACE
        )

        self.bus.add_signal_receiver(
            self.interfaces_added,
            dbus_interface=self.DBUS_OM_IFACE,
            signal_name="InterfacesAdded",
        )

        self.bus.add_signal_receiver(
            self._properties_changed,
            dbus_interface=self.DBUS_PROP_IFACE,
            signal_name="PropertiesChanged",
            arg0=self.DEVICE_INTERFACE,
            path_keyword="path",
        )

        print("Configuring for name {}".format(BTKbDevice.MY_DEV_NAME))

        self.config_hid_profile()

        # set the Bluetooth device configuration
        self.powered = True
        self.alias = BTKbDevice.MY_DEV_NAME
        self.discoverabletimeout = 0
        self.pairabletimeout = 0
        self.discoverable = True
        self.pairable = True

    def interfaces_added(self, *args, **kwargs):
        pass

    def _properties_changed(self, interface, changed, invalidated, path):
        if "Connected" in changed:
            print(f"Device state changed: {path} Connected={changed['Connected']}")
            if (not changed["Connected"]) and self.cinterrupt is not None:
                self.on_disconnect()
        if "Paired" in changed:
            print(f"Device state changed: {path} Paired={changed['Paired']}")

    def on_disconnect(self):
        print("The client has been disconnect")
        self.close_sockets()
        self.start_listener()

    def start_listener(self):
        if self.listener_thread is not None and self.listener_thread.is_alive():
            return
        self.listener_thread = threading.Thread(target=self._listener_loop, daemon=True)
        self.listener_thread.start()

    def _listener_loop(self):
        while True:
            try:
                self.listen()
                return
            except OSError as exc:
                print(f"Listener retry after socket error: {exc}")
                self.close_sockets()
                time.sleep(1)

    @property
    def address(self):
        """Return the adapter MAC address."""
        return self.adapter_property.Get(self.ADAPTER_IFACE, "Address")

    @property
    def powered(self):
        """
        power state of the Adapter.
        """
        return self.adapter_property.Get(self.ADAPTER_IFACE, "Powered")

    @powered.setter
    def powered(self, new_state):
        self.adapter_property.Set(self.ADAPTER_IFACE, "Powered", new_state)

    @property
    def alias(self):
        return self.adapter_property.Get(self.ADAPTER_IFACE, "Alias")

    @alias.setter
    def alias(self, new_alias):
        self.adapter_property.Set(self.ADAPTER_IFACE, "Alias", new_alias)

    @property
    def discoverabletimeout(self):
        """Discoverable timeout of the Adapter."""
        return self.adapter_property.Get(self.ADAPTER_IFACE, "DiscoverableTimeout")

    @discoverabletimeout.setter
    def discoverabletimeout(self, new_timeout):
        self.adapter_property.Set(
            self.ADAPTER_IFACE, "DiscoverableTimeout", dbus.UInt32(new_timeout)
        )

    @property
    def discoverable(self):
        """Discoverable state of the Adapter."""
        return self.adapter_property.Get(self.ADAPTER_IFACE, "Discoverable")

    @discoverable.setter
    def discoverable(self, new_state):
        self.adapter_property.Set(self.ADAPTER_IFACE, "Discoverable", new_state)

    @property
    def pairabletimeout(self):
        """Pairable timeout of the Adapter."""
        return self.adapter_property.Get(self.ADAPTER_IFACE, "PairableTimeout")

    @pairabletimeout.setter
    def pairabletimeout(self, new_timeout):
        self.adapter_property.Set(
            self.ADAPTER_IFACE, "PairableTimeout", dbus.UInt32(new_timeout)
        )

    @property
    def pairable(self):
        """Pairable state of the Adapter."""
        return self.adapter_property.Get(self.ADAPTER_IFACE, "Pairable")

    @pairable.setter
    def pairable(self, new_state):
        self.adapter_property.Set(self.ADAPTER_IFACE, "Pairable", new_state)

    def config_hid_profile(self):
        """
        Setup and register HID Profile
        """

        print("Configuring Bluez Profile")
        service_record = self.read_sdp_service_record()

        opts = {
            "Role": "server",
            "RequireAuthentication": False,
            "RequireAuthorization": False,
            "AutoConnect": True,
            "ServiceRecord": service_record,
        }

        manager = dbus.Interface(
            self.bus.get_object("org.bluez", "/org/bluez"), "org.bluez.ProfileManager1"
        )

        HumanInterfaceDeviceProfile(self.bus, BTKbDevice.PROFILE_DBUS_PATH)

        print("f")
        manager.RegisterProfile(BTKbDevice.PROFILE_DBUS_PATH, BTKbDevice.UUID, opts)
        print("e")

        print("Profile registered ")

    @staticmethod
    def read_sdp_service_record():
        """
        Read and return SDP record from a file
        :return: (string) SDP record
        """
        print("Reading service record")
        try:
            fh = open(BTKbDevice.SDP_RECORD_PATH, "r")
        except OSError as e:
            sys.exit(f"{e}: Could not open the sdp record. Exiting...")

        return fh.read()

    def listen(self):
        """
        Listen for connections coming from HID client
        """

        print("[listen] start")
        self.close_sockets()
        print("[listen] Waiting for connections")
        print(f"[listen] adapter={self.address} ctrl_psm={self.P_CTRL} intr_psm={self.P_INTR}")

        print("[listen] creating control socket")
        scontrol = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP
        )
        scontrol.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        print("[listen] creating interrupt socket")
        sinterrupt = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP
        )
        sinterrupt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        print("[listen] binding control socket")
        scontrol.bind((self.address, self.P_CTRL))
        print("[listen] binding interrupt socket")
        sinterrupt.bind((self.address, self.P_INTR))

        # Start listening on the server sockets
        print("[listen] control listen(1)")
        scontrol.listen(1)  # Limit of 1 connection
        print("[listen] interrupt listen(1)")
        sinterrupt.listen(1)

        ccontrol = None
        cinterrupt = None
        selector = selectors.DefaultSelector()
        selector.register(scontrol, selectors.EVENT_READ, "control")
        selector.register(sinterrupt, selectors.EVENT_READ, "interrupt")

        print("[listen] waiting for control/interrupt accept() in any order")
        try:
            while ccontrol is None or cinterrupt is None:
                events = selector.select(timeout=5)
                if not events:
                    print(
                        "[listen] still waiting: "
                        f"control={'ok' if ccontrol else 'pending'} "
                        f"interrupt={'ok' if cinterrupt else 'pending'}"
                    )
                    print(
                        "[listen] adapter state: "
                        f"powered={self.powered} "
                        f"discoverable={self.discoverable} "
                        f"pairable={self.pairable}"
                    )
                    continue

                for key, _ in events:
                    role = key.data
                    if role == "control" and ccontrol is None:
                        ccontrol, cinfo = scontrol.accept()
                        print("[listen] {} connected on the control socket".format(cinfo[0]))
                        selector.unregister(scontrol)
                    elif role == "interrupt" and cinterrupt is None:
                        cinterrupt, cinfo = sinterrupt.accept()
                        print("[listen] {} connected on the interrupt channel".format(cinfo[0]))
                        selector.unregister(sinterrupt)
        finally:
            selector.close()

        with self.sock_lock:
            self.scontrol = scontrol
            self.sinterrupt = sinterrupt
            self.ccontrol = ccontrol
            self.cinterrupt = cinterrupt

        print("[listen] sockets stored, HID channel ready")

    def close_sockets(self):
        with self.sock_lock:
            sockets = [self.ccontrol, self.cinterrupt, self.scontrol, self.sinterrupt]
            self.ccontrol = None
            self.cinterrupt = None
            self.scontrol = None
            self.sinterrupt = None

        for sock in sockets:
            if sock is None:
                continue
            try:
                sock.close()
            except OSError:
                pass

    def send(self, msg):
        """
        Send HID message
        :param msg: (bytes) HID packet to send
        """
        with self.sock_lock:
            interrupt_sock = self.cinterrupt
        if interrupt_sock is None:
            raise ConnectionError("Interrupt channel is not connected")
        interrupt_sock.sendall(bytes(bytearray(msg)))


class BTKbService(dbus.service.Object):
    """
    Setup of a D-Bus service to recieve HID messages from other
    processes.
    Send the recieved HID messages to the Bluetooth HID server to send
    """

    def __init__(self):
        print("Setting up service")

        bus_name = dbus.service.BusName("org.yaptb.btkbservice", bus=dbus.SystemBus())
        dbus.service.Object.__init__(self, bus_name, "/org/yaptb/btkbservice")

        # create and setup our device
        self.device = BTKbDevice()

        # start listening for socket connections in background
        self.device.start_listener()

    @dbus.service.method("org.yaptb.btkbservice", in_signature="ay")
    def send_keys(self, cmd):
        try:
            self.device.send(cmd)
        except (BrokenPipeError, ConnectionResetError, ConnectionError, OSError) as exc:
            print(f"send_keys failed ({exc}), reconnecting")
            self.device.close_sockets()
            self.device.start_listener()


if __name__ == "__main__":
    # The sockets require root permission
    if not os.geteuid() == 0:
        sys.exit("Only root can run this script")

    DBusGMainLoop(set_as_default=True)
    myservice = BTKbService()
    mainloop = GLib.MainLoop()
    mainloop.run()
