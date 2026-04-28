"""
Thin wrappers around win32gui for window state queries.
"""
import win32gui


def is_window_alive(hwnd: int) -> bool:
    return bool(win32gui.IsWindow(hwnd))


def get_window_rect(hwnd: int) -> tuple[int, int, int, int]:
    return win32gui.GetWindowRect(hwnd)
