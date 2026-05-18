"""
Synthetic input via the interception kernel driver.

All clicks and key presses go through interception so they reach the game
even when it is the foreground window. Devices must be registered once per
process via enable() before any input functions are called.

interception is imported lazily so the app starts normally even if the
driver is not installed — it only fails when Auto Scan is actually used.
"""
import time
from capture.window import get_window_rect

_devices_ready = False
_interception = None


def _get_interception():
    global _interception
    if _interception is None:
        try:
            import interception as _ic
            _interception = _ic
        except ImportError:
            raise RuntimeError(
                "The Interception driver is not installed.\n\n"
                "Auto Scan requires the Interception kernel driver.\n"
                "Download it from: github.com/oblitum/Interception\n"
                "Install as Administrator, then reboot."
            )
    return _interception


def enable():
    global _devices_ready
    if not _devices_ready:
        ic = _get_interception()
        print("Move your mouse once, then press any key to register devices...")
        ic.auto_capture_devices(keyboard=True, mouse=True)
        _devices_ready = True


def disable():
    global _devices_ready
    _devices_ready = False


def click_at(hwnd: int, rel_x_pct: float, rel_y_pct: float, delay: float = 1.5):
    ic = _get_interception()
    left, top, right, bottom = get_window_rect(hwnd)
    w, h = right - left, bottom - top
    x = left + int(w * rel_x_pct)
    y = top  + int(h * rel_y_pct)
    ic.move_to(x, y)
    time.sleep(0.05)
    ic.left_click()
    time.sleep(delay)


def scroll_down(amount: int = 3):
    ic = _get_interception()
    for _ in range(amount):
        ic.scroll('down')
        time.sleep(0.05)


def press_escape():
    _get_interception().press('escape')


def press_space():
    _get_interception().press('space')
