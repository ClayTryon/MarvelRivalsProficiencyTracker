"""
Thin wrappers around win32gui for window state queries.
"""
import win32gui


def is_window_alive(hwnd: int) -> bool:
    return bool(win32gui.IsWindow(hwnd))


def get_window_rect(hwnd: int) -> tuple[int, int, int, int]:
    return win32gui.GetWindowRect(hwnd)


def get_client_bbox(hwnd: int) -> tuple[int, int, int, int]:
    """Return the client area in screen coordinates (excludes title bar and borders).

    Uses GetClientRect + ClientToScreen so fractions applied to the captured image
    are relative to game content pixels only, making them resolution-independent.
    """
    cl, ct, cr, cb = win32gui.GetClientRect(hwnd)
    origin_x, origin_y = win32gui.ClientToScreen(hwnd, (0, 0))
    return (origin_x, origin_y, origin_x + cr, origin_y + cb)
