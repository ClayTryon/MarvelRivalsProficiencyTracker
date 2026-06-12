import sys
import os
import ctypes
import logging
from logging.handlers import RotatingFileHandler


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
from storage.repository import HeroRepository, SnapshotRepository, seed_default_heroes
from gui.main_window import MainWindow
from gui.style import APP_STYLESHEET

_ICON_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Icons", "app_icon.ico")
)


def _setup_logging(app_data: str):
    log_path = os.path.join(app_data, "proftracker.log")
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def main():
    app_data = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ProficiencyTracker")
    os.makedirs(app_data, exist_ok=True)
    _setup_logging(app_data)
    db = Database(os.path.join(app_data, "proficiency_tracker.db"))
    db.connect()
    db.init_schema()
    db.migrate_schema()
    SnapshotRepository(db).backfill_from_heroes()

    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)
    if os.path.exists(_ICON_PATH):
        app.setWindowIcon(QIcon(_ICON_PATH))

    if not HeroRepository(db).get_all():
        from gui.first_run_dialog import FirstRunDialog
        import data.heroes as _heroes_mod
        FirstRunDialog().exec()
        _heroes_mod._reload()
        seed_default_heroes(db)

    window = MainWindow(db)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
