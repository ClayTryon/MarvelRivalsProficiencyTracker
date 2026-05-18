import sys
import os
import ctypes


# Ensure src/ is on the path when running directly
sys.path.insert(0, os.path.dirname(__file__))

# Declare per-monitor DPI awareness so win32gui and pyautogui
# both operate in physical pixels — prevents misaligned clicks on scaled displays.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ProfTracker.App")
except Exception:
    pass

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from storage.database import Database
from storage.repository import SnapshotRepository
from gui.main_window import MainWindow
from gui.style import APP_STYLESHEET

_ICON_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Icons", "app_icon.ico")
)


def main():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "proficiency_tracker.db")
    db = Database(os.path.normpath(db_path))
    db.connect()
    db.init_schema()
    SnapshotRepository(db).backfill_from_heroes()

    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)
    if os.path.exists(_ICON_PATH):
        app.setWindowIcon(QIcon(_ICON_PATH))
    window = MainWindow(db)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
