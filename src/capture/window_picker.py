import win32gui
import win32con
from PyQt6.QtWidgets import QWidget, QLabel, QApplication
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QPainter, QColor


class WindowPickerOverlay(QWidget):
    window_selected = pyqtSignal(int, str)
    cancelled = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        label = QLabel("Click the Marvel Rivals window to select it.  Press Escape to cancel.", self)
        label.setStyleSheet(
            "color: white; background: rgba(0,0,0,180); font-size: 18px; padding: 12px;"
        )
        label.adjustSize()
        label.move(screen.width() // 2 - label.width() // 2, 20)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

    def mousePressEvent(self, event):
        pos = event.globalPosition().toPoint()

        # Hide the overlay before resolving the window — otherwise WindowFromPoint
        # returns this overlay's own HWND since it is the topmost window at the cursor.
        self.hide()
        QApplication.processEvents()

        hwnd = win32gui.WindowFromPoint((pos.x(), pos.y()))
        # Walk to the true root ancestor (top-level window, not desktop)
        root = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
        if root:
            hwnd = root

        title = win32gui.GetWindowText(hwnd)
        self.window_selected.emit(hwnd, title)
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()


def pick_window(parent=None) -> tuple[int, str] | None:
    result = {}

    overlay = WindowPickerOverlay()
    overlay.window_selected.connect(lambda hwnd, title: result.update({"hwnd": hwnd, "title": title}))
    overlay.cancelled.connect(lambda: result.update({"cancelled": True}))
    overlay.show()

    loop = QApplication.instance()
    while overlay.isVisible():
        loop.processEvents()

    if result.get("cancelled"):
        return None
    if "hwnd" in result:
        return result["hwnd"], result["title"]
    return None
