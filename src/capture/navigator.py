"""
Synthetic input via the interception kernel driver.

All clicks and key presses go through interception so they reach the game
even when it is the foreground window. Devices must be registered once per
process via enable() before any input functions are called.
"""
import time
import interception
from capture.window import get_window_rect

_devices_ready = False


def enable():
    """Register keyboard and mouse devices. Blocks until the user moves the mouse and presses a key."""
    global _devices_ready
    if not _devices_ready:
        print("Move your mouse once, then press any key to register devices...")
        interception.auto_capture_devices(keyboard=True, mouse=True)
        _devices_ready = True


def disable():
    """Reset device registration state so enable() will prompt again next session."""
    global _devices_ready
    _devices_ready = False


def click_at(hwnd: int, rel_x_pct: float, rel_y_pct: float, delay: float = 1.5):
    """Move to a position expressed as fractions of the window rect, click, then wait delay seconds."""
    left, top, right, bottom = get_window_rect(hwnd)
    w, h = right - left, bottom - top
    x = left + int(w * rel_x_pct)
    y = top  + int(h * rel_y_pct)
    interception.move_to(x, y)
    time.sleep(0.05)
    interception.left_click()
    time.sleep(delay)


def scroll_down(amount: int = 3):
    for _ in range(amount):
        interception.scroll('down')
        time.sleep(0.05)


def press_escape():
    interception.press('escape')


def press_space():
    interception.press('space')
