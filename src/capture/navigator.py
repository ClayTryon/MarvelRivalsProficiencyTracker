import time
import interception
from capture.window import get_window_rect

_devices_ready = False


def enable():
    global _devices_ready
    if not _devices_ready:
        print("Move your mouse once, then press any key to register devices...")
        interception.auto_capture_devices(keyboard=True, mouse=True)
        _devices_ready = True


def disable():
    global _devices_ready
    _devices_ready = False


def click_at(hwnd: int, rel_x_pct: float, rel_y_pct: float, delay: float = 1.5):
    left, top, right, bottom = get_window_rect(hwnd)
    w, h = right - left, bottom - top
    x = left + int(w * rel_x_pct)
    y = top  + int(h * rel_y_pct)
    interception.move_to(x, y)
    time.sleep(0.05)
    interception.left_click()
    time.sleep(delay)


def scroll_down(hwnd: int, amount: int = 3):
    for _ in range(amount):
        interception.scroll('down')
        time.sleep(0.05)


def press_escape(hwnd: int):
    interception.press('escape')


def press_space(hwnd: int):
    interception.press('space')
