# pip install pynput requests
from pynput import keyboard, mouse
#import requests
#import threading

# ─── 일반 키 매핑 (key.char) ──────────────────────────
CHAR_MAP = {
    # 알파벳
    'a': {'gesture': 'A',           'cmd': 'A'},
    'b': {'gesture': 'B',           'cmd': 'B'},
    'c': {'gesture': 'C',           'cmd': 'C'},
    'd': {'gesture': 'D',           'cmd': 'D'},
    'e': {'gesture': 'E',           'cmd': 'E'},
    'f': {'gesture': 'F',           'cmd': 'F'},
    'g': {'gesture': 'G',           'cmd': 'G'},
    'h': {'gesture': 'H',           'cmd': 'H'},
    'i': {'gesture': 'I',           'cmd': 'I'},
    'j': {'gesture': 'J',           'cmd': 'J'},
    'k': {'gesture': 'K',           'cmd': 'K'},
    'l': {'gesture': 'L',           'cmd': 'L'},
    'm': {'gesture': 'M',           'cmd': 'M'},
    'n': {'gesture': 'N',           'cmd': 'N'},
    'o': {'gesture': 'O',           'cmd': 'O'},
    'p': {'gesture': 'P',           'cmd': 'P'},
    'q': {'gesture': 'Q',           'cmd': 'Q'},
    'r': {'gesture': 'R',           'cmd': 'R'},
    's': {'gesture': 'S',           'cmd': 'S'},
    't': {'gesture': 'T',           'cmd': 'T'},
    'u': {'gesture': 'U',           'cmd': 'U'},
    'v': {'gesture': 'V',           'cmd': 'V'},
    'w': {'gesture': 'W',           'cmd': 'W'},
    'x': {'gesture': 'X',           'cmd': 'X'},
    'y': {'gesture': 'Y',           'cmd': 'Y'},
    'z': {'gesture': 'Z',           'cmd': 'Z'},
    # 숫자
    '0': {'gesture': 'NUM_0',       'cmd': '0'},
    '1': {'gesture': 'NUM_1',       'cmd': '1'},
    '2': {'gesture': 'NUM_2',       'cmd': '2'},
    '3': {'gesture': 'NUM_3',       'cmd': '3'},
    '4': {'gesture': 'NUM_4',       'cmd': '4'},
    '5': {'gesture': 'NUM_5',       'cmd': '5'},
    '6': {'gesture': 'NUM_6',       'cmd': '6'},
    '7': {'gesture': 'NUM_7',       'cmd': '7'},
    '8': {'gesture': 'NUM_8',       'cmd': '8'},
    '9': {'gesture': 'NUM_9',       'cmd': '9'},
    # 특수문자
    ' ': {'gesture': 'SPACE',       'cmd': 'BRAKE'},
    '.': {'gesture': 'DOT',         'cmd': 'DOT'},
    ',': {'gesture': 'COMMA',       'cmd': 'COMMA'},
    '/': {'gesture': 'SLASH',       'cmd': 'SLASH'},
    ';': {'gesture': 'SEMICOLON',   'cmd': 'SEMICOLON'},
    "'": {'gesture': 'QUOTE',       'cmd': 'QUOTE'},
    '[': {'gesture': 'BRACKET_L',   'cmd': 'BRACKET_L'},
    ']': {'gesture': 'BRACKET_R',   'cmd': 'BRACKET_R'},
    '\\':{'gesture': 'BACKSLASH',   'cmd': 'BACKSLASH'},
    '-': {'gesture': 'MINUS',       'cmd': 'MINUS'},
    '=': {'gesture': 'EQUAL',       'cmd': 'EQUAL'},
    '`': {'gesture': 'BACKTICK',    'cmd': 'BACKTICK'},
}

# ─── 특수 키 매핑 (key 객체 직접 비교) ───────────────
SPECIAL_MAP = {
    keyboard.Key.space      : {'gesture': 'SPACE',      'cmd': 'BRAKE'},
    keyboard.Key.enter      : {'gesture': 'ENTER',      'cmd': 'ENTER'},
    keyboard.Key.backspace  : {'gesture': 'BACKSPACE',  'cmd': 'BACKSPACE'},
    keyboard.Key.tab        : {'gesture': 'TAB',        'cmd': 'TAB'},
    keyboard.Key.esc        : {'gesture': 'ESC',        'cmd': 'EMERGENCY_STOP'},
    keyboard.Key.delete     : {'gesture': 'DELETE',     'cmd': 'DELETE'},
    keyboard.Key.insert     : {'gesture': 'INSERT',     'cmd': 'INSERT'},
    keyboard.Key.home       : {'gesture': 'HOME',       'cmd': 'HOME'},
    keyboard.Key.end        : {'gesture': 'END',        'cmd': 'END'},
    keyboard.Key.page_up    : {'gesture': 'PAGE_UP',    'cmd': 'PAGE_UP'},
    keyboard.Key.page_down  : {'gesture': 'PAGE_DOWN',  'cmd': 'PAGE_DOWN'},
    # 방향키
    keyboard.Key.up         : {'gesture': 'ARROW_UP',   'cmd': 'FORWARD'},
    keyboard.Key.down       : {'gesture': 'ARROW_DOWN', 'cmd': 'BACKWARD'},
    keyboard.Key.left       : {'gesture': 'ARROW_LEFT', 'cmd': 'LEFT'},
    keyboard.Key.right      : {'gesture': 'ARROW_RIGHT','cmd': 'RIGHT'},
    # F키
    keyboard.Key.f1         : {'gesture': 'F1',         'cmd': 'F1'},
    keyboard.Key.f2         : {'gesture': 'F2',         'cmd': 'F2'},
    keyboard.Key.f3         : {'gesture': 'F3',         'cmd': 'F3'},
    keyboard.Key.f4         : {'gesture': 'F4',         'cmd': 'F4'},
    keyboard.Key.f5         : {'gesture': 'F5',         'cmd': 'F5'},
    keyboard.Key.f6         : {'gesture': 'F6',         'cmd': 'F6'},
    keyboard.Key.f7         : {'gesture': 'F7',         'cmd': 'F7'},
    keyboard.Key.f8         : {'gesture': 'F8',         'cmd': 'F8'},
    keyboard.Key.f9         : {'gesture': 'F9',         'cmd': 'F9'},
    keyboard.Key.f10        : {'gesture': 'F10',        'cmd': 'F10'},
    keyboard.Key.f11        : {'gesture': 'F11',        'cmd': 'F11'},
    keyboard.Key.f12        : {'gesture': 'F12',        'cmd': 'F12'},
    # 수정자 키
    keyboard.Key.shift      : {'gesture': 'SHIFT',      'cmd': 'SHIFT'},
    keyboard.Key.shift_r    : {'gesture': 'SHIFT_R',    'cmd': 'SHIFT'},
    keyboard.Key.ctrl       : {'gesture': 'CTRL',       'cmd': 'CTRL'},
    keyboard.Key.ctrl_r     : {'gesture': 'CTRL_R',     'cmd': 'CTRL'},
    keyboard.Key.alt        : {'gesture': 'ALT',        'cmd': 'ALT'},
    keyboard.Key.alt_r      : {'gesture': 'ALT_R',      'cmd': 'ALT'},
    keyboard.Key.cmd        : {'gesture': 'WIN',        'cmd': 'WIN'},
    keyboard.Key.caps_lock  : {'gesture': 'CAPS_LOCK',  'cmd': 'CAPS_LOCK'},
    keyboard.Key.num_lock   : {'gesture': 'NUM_LOCK',   'cmd': 'NUM_LOCK'},
    keyboard.Key.scroll_lock: {'gesture': 'SCROLL_LOCK','cmd': 'SCROLL_LOCK'},
    keyboard.Key.print_screen:{'gesture': 'PRINT_SCR',  'cmd': 'PRINT_SCR'},
    keyboard.Key.pause      : {'gesture': 'PAUSE',      'cmd': 'PAUSE'},
    keyboard.Key.menu       : {'gesture': 'MENU',       'cmd': 'MENU'},
}

# ─── 마우스 버튼 매핑 ─────────────────────────────────
MOUSE_MAP = {
    mouse.Button.left   : {'gesture': 'MOUSE_LEFT',   'cmd': 'MOUSE_LEFT'},
    mouse.Button.right  : {'gesture': 'MOUSE_RIGHT',  'cmd': 'MOUSE_RIGHT'},
    mouse.Button.middle : {'gesture': 'MOUSE_MIDDLE', 'cmd': 'MOUSE_MIDDLE'},
}

# ─── 전송 ─────────────────────────────────────────────
import socketio

sio = socketio.Client()
sio.connect('http://localhost:5000')

def send_async(data):
    try:
        requests.post('http://localhost:5000/api/data', json=data, timeout=1)
    except:
        pass

def emit(payload):
    # HTTP 없이 Socket.IO 직접 전송
    sio.emit('gesture', payload)
    print(f"[INPUT] {payload['key']} → {payload['cmd']}")

# ─── 키보드 리스너 ────────────────────────────────────
def on_key_press(key):
    # 일반 문자 키
    try:
        k = key.char
        info = CHAR_MAP.get(k)
        if info:
            emit({'key': k, 'gesture': info['gesture'], 'cmd': info['cmd'], 'type': 'keyboard'})
        return
    except AttributeError:
        pass

    # 특수 키
    info = SPECIAL_MAP.get(key)
    if info:
        emit({'key': str(key), 'gesture': info['gesture'], 'cmd': info['cmd'], 'type': 'keyboard'})

# ─── 마우스 리스너 ────────────────────────────────────
def on_mouse_click(x, y, button, pressed):
    if pressed:
        info = MOUSE_MAP.get(button)
        if info:
            emit({
                'key'    : str(button),
                'gesture': info['gesture'],
                'cmd'    : info['cmd'],
                'type'   : 'mouse',
                'x'      : x,
                'y'      : y,
            })

def on_scroll(x, y, dx, dy):
    direction = 'SCROLL_UP' if dy > 0 else 'SCROLL_DOWN'
    emit({
        'key'    : 'scroll',
        'gesture': direction,
        'cmd'    : direction,
        'type'   : 'mouse',
        'x'      : x,
        'y'      : y,
    })

# ─── 실행 ─────────────────────────────────────────────
kb_listener    = keyboard.Listener(on_press=on_key_press)
mouse_listener = mouse.Listener(on_click=on_mouse_click, on_scroll=on_scroll)

kb_listener.start()
mouse_listener.start()

print("[HID] 키보드 + 마우스 리스너 시작")
print("[HID] 종료하려면 Ctrl+C")
try:
    kb_listener.join()
except KeyboardInterrupt:
    print("\n[HID] 종료 중...")
    kb_listener.stop()
    mouse_listener.stop()
    sio.disconnect()
    print("[HID] 종료 완료")