import dbus

HID_DBUS = "org.yaptb.btkbservice"
HID_SRVC = "/org/yaptb/btkbservice"


class BluetoothSender:
    """
    A class to send a given string as HID messages over Bluetooth via D-Bus.
    """

    def __init__(self):
        self.bus = dbus.SystemBus()
        self.btkobject = self.bus.get_object(HID_DBUS, HID_SRVC)
        self.btk_service = dbus.Interface(self.btkobject, HID_DBUS)

    def send_string(self, text: str):
        """
        Sends a given string as a HID message over Bluetooth.
        :param text: The string to send
        """
        import time

        for char in text:
            hid_code = self.char_to_hid(char)
            if hid_code:
                # Send key press
                print(char)
                self.btk_service.send_keys([0xA1, 0x01, 0, 0, hid_code, 0, 0, 0, 0, 0])
                time.sleep(0.3)
                # Send key release (all zeros except header)
                self.btk_service.send_keys([0xA1, 0x01, 0, 0, 0, 0, 0, 0, 0, 0])
                time.sleep(0.3)

    def send_rsht(self):
        import time

        self.btk_service.send_keys([0xA1, 0x01, 0x20, 0, 0, 0, 0, 0, 0, 0])
        time.sleep(0.3)
        # Send key release (all zeros except header)
        self.btk_service.send_keys([0xA1, 0x01, 0, 0, 0, 0, 0, 0, 0, 0])
        time.sleep(0.3)

    def char_to_hid(self, char: str):
        """
        Converts a character to its corresponding HID key code.
        :param char: The character to convert
        :return: The HID key code
        """
        hid_map = {
            "a": 0x04,
            "b": 0x05,
            "c": 0x06,
            "d": 0x07,
            "e": 0x08,
            "f": 0x09,
            "g": 0x0A,
            "h": 0x0B,
            "i": 0x0C,
            "j": 0x0D,
            "k": 0x0E,
            "l": 0x0F,
            "m": 0x10,
            "n": 0x11,
            "o": 0x12,
            "p": 0x13,
            "q": 0x14,
            "r": 0x15,
            "s": 0x16,
            "t": 0x17,
            "u": 0x18,
            "v": 0x19,
            "w": 0x1A,
            "x": 0x1B,
            "y": 0x1C,
            "z": 0x1D,
            "1": 0x1E,
            "2": 0x1F,
            "3": 0x20,
            "4": 0x21,
            "5": 0x22,
            "6": 0x23,
            "7": 0x24,
            "8": 0x25,
            "9": 0x26,
            "0": 0x27,
            "\n": 0x28,
            " ": 0x2C,
            ".": 0x37,
            ",": 0x36,
            "-": 0x2D,
            "=": 0x2E,
            "[": 0x2F,
            "]": 0x30,
            ";": 0x33,
            "\\": 0x31,
            "/": 0x38,
            "`": 0x35,
        }
        return hid_map.get(char.lower())


if __name__ == "__main__":
    sender = BluetoothSender()
    text = input("Enter the string to send over Bluetooth: ")
    sender.send_string(text + "\n")
    # sender.send_string("/")
    # sender.send_rsht()
