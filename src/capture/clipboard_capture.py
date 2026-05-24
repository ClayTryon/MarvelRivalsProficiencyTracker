import time
import win32gui
import win32con
import win32process
import win32api


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

