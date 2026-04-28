import win32gui


def is_window_alive(hwnd: int) -> bool:
    return bool(win32gui.IsWindow(hwnd))


def get_window_title(hwnd: int) -> str:
    return win32gui.GetWindowText(hwnd)


def get_window_rect(hwnd: int) -> tuple[int, int, int, int]:
    return win32gui.GetWindowRect(hwnd)
