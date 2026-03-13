

## Reqirements

- System pakage 

```bash
sudo apt-get update
sudo apt-get upgrade
sudo apt-get dist-upgrade
sudo apt install python3-dbus libdbus-1-dev libglib2.0-dev pkg-config gcc python3-dev -y

sudo systemctl disable bluetooth
sudo service bluetooth stop
sudo cp ./com.gcc.conf /etc/dbus-1/system.d/
sudo systemctl restart dbus
sudo systemctl restart bluetooth
```



Change  `/lib/systemd/system/bluetooth.service`
```bash
ExecStart=/usr/libexec/bluetooth/bluetoothd
```
to
```bash
ExecStart=/usr/libexec/bluetooth/bluetoothd -P input
```

reboot.
```bash
sudo reboot
```


## install
```bash
pip install -e .
```

## How to use

> First you have to run ble_hid GATT server

```bash
sudo python3 -m ble_hid
```

> Then you can use gcc module!

```python
from gcc import Keyboard

Keyboard.press_key('a')
```

