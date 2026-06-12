"""
Synthetic input via the interception kernel driver.

All clicks and key presses go through interception so they reach the game
even when it is the foreground window. Devices must be registered once per
process via enable() before any input functions are called.

interception is imported lazily so the app starts normally even if the
driver is not installed — it only fails when Auto Scan is actually used.
"""
import time
from capture.window import get_client_bbox, get_window_rect

_devices_ready = False
_ic = None


def _get_ic():
    global _ic
    if _ic is None:
        try:
            import interception.inputs as _inputs
            _ic = _inputs
        except ImportError:
            raise RuntimeError(
                "The interception-python package is not installed.\n\n"
                "Auto Scan requires the Interception kernel driver and its Python wrapper.\n"
                "Run: pip install interception-python\n"
                "Also install the Interception driver from: github.com/oblitum/Interception"
            )
    return _ic


def enable():
    global _devices_ready
    if not _devices_ready:
        ic = _get_ic()
        ic.auto_capture_devices(keyboard=True, mouse=True)
        _devices_ready = True


def disable():
    global _devices_ready
    _devices_ready = False


def click_at(hwnd: int, rel_x_pct: float, rel_y_pct: float, delay: float = 1.5):
    ic = _get_ic()
    left, top, right, bottom = get_client_bbox(hwnd)
    w, h = right - left, bottom - top
    x = left + int(w * rel_x_pct)
    y = top + int(h * rel_y_pct)
    ic.move_to(x, y)
    time.sleep(0.05)
    ic.left_click()
    time.sleep(delay)


def scroll_down(amount: int = 3):
    ic = _get_ic()
    for _ in range(amount):
        ic.scroll('down')
        time.sleep(0.05)


def press_escape():
    _get_ic().press('escape')


def press_space():
    _get_ic().press('space')


def crop_to_client(image, hwnd: int):
    """Crop a window screenshot down to the client area, stripping the title bar.

    If the window is fullscreen (window rect == client rect) the image is returned
    unchanged. Otherwise only the top (title bar height) is removed.
    """
    wx, wy, wr, wb = get_window_rect(hwnd)
    cx, cy, cr, cb = get_client_bbox(hwnd)
    if (wx, wy, wr, wb) == (cx, cy, cr, cb):
        return image
    top = cy - wy
    return image.crop((0, top, image.width, image.height))


def capture_active_window(hwnd: int):
    """Send Alt+PrtScn via interception, then crop the result to the game client area."""
    from PIL import ImageGrab
    from exceptions import CaptureError
    ic = _get_ic()
    with ic.hold_key('alt'):
        ic.press('printscreen')
    time.sleep(0.5)
    image = ImageGrab.grabclipboard()
    if image is None:
        raise CaptureError("Alt+PrtScn clipboard capture returned no image")
    return crop_to_client(image, hwnd)
