from PyQt6.QtWidgets import QMainWindow, QStackedWidget
from gui.scan_panel import ScanPanel
from gui.hero_browser import HeroBrowser
from storage.database import Database
from storage.repository import HeroRepository


class MainWindow(QMainWindow):
    def __init__(self, db: Database):
        super().__init__()
        self.setWindowTitle("ProfTracker")
        self.setMinimumSize(900, 600)
        self._db = db

        self._stack = QStackedWidget()
        self._scan_panel = ScanPanel(db)
        self._hero_browser = HeroBrowser()

        self._stack.addWidget(self._scan_panel)   # index 0
        self._stack.addWidget(self._hero_browser)  # index 1
        self.setCentralWidget(self._stack)

        self._scan_panel.scan_complete.connect(self._show_browser)
        self._scan_panel.back_requested.connect(self._show_browser_no_reload)
        self._hero_browser.new_scan_requested.connect(self._show_scan_panel)

        heroes = HeroRepository(db).get_all()
        if heroes:
            self._hero_browser.load_heroes(heroes)
            self._scan_panel.set_has_results(True)
            self._stack.setCurrentIndex(1)

    def _show_browser(self, _heroes: list = None):
        heroes = HeroRepository(self._db).get_all()
        self._hero_browser.load_heroes(heroes)
        self._scan_panel.set_has_results(bool(heroes))
        self._stack.setCurrentIndex(1)

    def _show_browser_no_reload(self):
        self._stack.setCurrentIndex(1)

    def _show_scan_panel(self):
        self._stack.setCurrentIndex(0)
