import time
import ctypes
import win32gui
import win32con
import win32process
import win32api
from PIL import ImageGrab
from exceptions import CaptureError


def focus_window(hwnd: int):
    """Bring hwnd to foreground using thread-input attachment to bypass Windows restrictions."""
    try:
        fg = win32gui.GetForegroundWindow()
        fg_tid, _ = win32process.GetWindowThreadProcessId(fg)
        my_tid = win32api.GetCurrentThreadId()
        if fg_tid != my_tid:
            win32process.AttachThreadInput(fg_tid, my_tid, True)
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        if fg_tid != my_tid:
            win32process.AttachThreadInput(fg_tid, my_tid, False)
    except Exception:
        pass
    time.sleep(0.3)


def capture_window(hwnd: int):
    """Directly grab the window's bounding rect from the screen."""
    rect = win32gui.GetWindowRect(hwnd)
    if rect == (0, 0, 0, 0):
        raise CaptureError("Could not get window rect — is the window minimized?")
    image = ImageGrab.grab(bbox=rect, all_screens=True)
    if image is None:
        raise CaptureError("Screen grab returned no image")
    return image
