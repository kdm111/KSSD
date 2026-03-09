# BLE HID Keyboard + Mouse (Raspberry Pi 5, BlueZ + D-Bus)

## Run

```bash
sudo python3 -m ble_hid.main
```

## Package layout

- `ble_hid/constants.py`: UUID, interface name, D-Bus path constants
- `ble_hid/exceptions.py`: BlueZ-friendly D-Bus exceptions
- `ble_hid/utils.py`: adapter lookup and common helpers
- `ble_hid/bluez/application.py`: ObjectManager root
- `ble_hid/bluez/gatt.py`: generic Service / Characteristic / Descriptor base classes
- `ble_hid/bluez/advertisement.py`: LE advertisement object
- `ble_hid/bluez/agent.py`: pairing agent
- `ble_hid/hid/report_map.py`: HID Report Descriptor bytes
- `ble_hid/hid/services.py`: concrete HID / Battery / Device Info services
- `ble_hid/demo.py`: simple synthetic input generator for testing
- `ble_hid/main.py`: registration sequence and process entrypoint

## Notes

This is a strong skeleton, not a final production implementation. You will likely need host-specific interoperability tuning for macOS / iPadOS / Windows.


# ** 중요!!!!!!!!!!!! **

```shell

bluetoothctl #이걸로 기존 디바이스 싹 다 remove!!

```


device 는 event5, 6 : 아마 keyboard?..
mouse0는 마우스