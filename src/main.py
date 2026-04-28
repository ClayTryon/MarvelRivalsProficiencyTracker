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

from PyQt6.QtWidgets import QApplication
from storage.database import Database
from gui.main_window import MainWindow


def main():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "proficiency_tracker.db")
    db = Database(os.path.normpath(db_path))
    db.connect()
    db.init_schema()

    app = QApplication(sys.argv)
    window = MainWindow(db)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
