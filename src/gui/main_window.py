import webbrowser

from PyQt6.QtWidgets import (
    QMainWindow, QStackedWidget, QWidget,
    QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from gui.scan_panel import ScanPanel
from gui.hero_browser import HeroBrowser
from gui.hero_info_panel import HeroInfoPanel
from gui.sync_panel import SyncPanel
from gui.teamups_panel import TeamUpsPanel
from gui.update_checker import UpdateChecker
from storage.database import Database
from storage.repository import HeroRepository
from version import __version__

# Tab indices — must match order added to QStackedWidget
_TAB_SCAN    = 0
_TAB_HEROES  = 1
_TAB_WIKI    = 2
_TAB_TEAMUPS = 3
_TAB_SYNC    = 4

_TAB_LABELS = ["SCAN", "HEROES", "HERO WIKI", "TEAM-UPS"]


class _NavBar(QWidget):
    tab_clicked = pyqtSignal(int)

    _ACTIVE = (
        "QPushButton {"
        " font-family: Impact, 'Arial Narrow', Arial;"
        " font-size: 13px; letter-spacing: 2px;"
        " color: #ffffff; background: transparent; border: none;"
        " border-bottom: 2px solid #f4d641; padding: 0 14px;"
        " margin-bottom: -1px;"
        "}"
    )
    _INACTIVE = (
        "QPushButton {"
        " font-family: Impact, 'Arial Narrow', Arial;"
        " font-size: 13px; letter-spacing: 2px;"
        " color: #484860; background: transparent; border: none;"
        " padding: 0 14px;"
        "}"
        "QPushButton:hover { color: #9090b8; }"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(
            "background: #080810; border-bottom: 1px solid #1a1a2c;"
        )

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(0)

        logo = QLabel("PROFTRACKER")
        logo.setStyleSheet(
            "font-family: Impact, 'Arial Narrow', Arial;"
            " font-size: 14px; letter-spacing: 4px;"
            " color: #f4d641; padding-right: 28px;"
        )
        row.addWidget(logo)

        self._tab_btns: list[QPushButton] = []
        for i, label in enumerate(_TAB_LABELS):
            if i > 0:
                sep = QLabel("/")
                sep.setStyleSheet("color: #2a2a40; font-size: 15px; padding: 0 2px;")
                row.addWidget(sep)

            btn = QPushButton(label)
            btn.setFlat(True)
            btn.setFixedHeight(44)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self.tab_clicked.emit(idx))
            self._tab_btns.append(btn)
            row.addWidget(btn)

        row.addStretch()

        sync_btn = QPushButton("⟳ SYNC")
        sync_btn.setFixedHeight(28)
        sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sync_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #484860;"
            " border: 1px solid #26263c; border-radius: 3px;"
            " font-size: 11px; letter-spacing: 1px; padding: 0 10px; }"
            " QPushButton:hover { color: #f4d641; border-color: #f4d641; }"
        )
        sync_btn.clicked.connect(lambda: self.tab_clicked.emit(_TAB_SYNC))
        row.addWidget(sync_btn)

        ver = QLabel(f"v{__version__}")
        ver.setStyleSheet("color: #303048; font-size: 11px; padding-left: 10px;")
        row.addWidget(ver)

        self.set_active(1)

    def set_active(self, index: int):
        for i, btn in enumerate(self._tab_btns):
            btn.setStyleSheet(self._ACTIVE if i == index else self._INACTIVE)


class _UpdateBanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._url = ""
        self.setStyleSheet("background: #3a3000; border-bottom: 1px solid #f4d641;")
        self.setFixedHeight(32)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 0, 12, 0)

        self._label = QLabel()
        self._label.setStyleSheet("color: #f4d641; font-size: 12px;")
        row.addWidget(self._label)
        row.addStretch()

        download_btn = QPushButton("Download")
        download_btn.setFixedHeight(22)
        download_btn.setStyleSheet(
            "QPushButton { background: #f4d641; color: #1a1a1a; border: none;"
            " border-radius: 3px; font-size: 11px; font-weight: bold; padding: 0 10px; }"
            " QPushButton:hover { background: #ffe066; }"
        )
        download_btn.clicked.connect(self._open_release)
        row.addWidget(download_btn)

    def show_update(self, new_version: str, url: str):
        self._url = url
        self._label.setText(
            f"Update available: v{new_version}  (you have v{__version__})"
        )
        self.show()

    def _open_release(self):
        if self._url:
            webbrowser.open(self._url)


class MainWindow(QMainWindow):
    def __init__(self, db: Database):
        super().__init__()
        self.setWindowTitle("ProfTracker")
        self.setMinimumSize(900, 600)
        self._db = db

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._update_banner = _UpdateBanner()
        self._update_banner.hide()
        root.addWidget(self._update_banner)

        self._nav = _NavBar()
        self._nav.tab_clicked.connect(self._navigate)
        root.addWidget(self._nav)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: #0c0c14;")

        self._scan_panel   = ScanPanel(db)
        self._hero_browser = HeroBrowser(db)
        self._hero_info    = HeroInfoPanel()
        self._teamups_panel = TeamUpsPanel()
        self._sync_panel   = SyncPanel()

        self._stack.addWidget(self._scan_panel)     # 0 — SCAN
        self._stack.addWidget(self._hero_browser)   # 1 — HEROES
        self._stack.addWidget(self._hero_info)      # 2 — HERO WIKI
        self._stack.addWidget(self._teamups_panel)  # 3 — TEAM-UPS
        self._stack.addWidget(self._sync_panel)     # 4 — SYNC
        root.addWidget(self._stack)

        self.setCentralWidget(central)

        self._scan_panel.scan_complete.connect(self._on_scan_complete)
        self._scan_panel.hwnd_selected.connect(self._hero_browser.set_hwnd)
        self._sync_panel.sync_complete.connect(self._on_sync_complete)
        self._hero_browser.wiki_hero_requested.connect(self._on_wiki_hero_requested)

        heroes = HeroRepository(db).get_all()
        if heroes:
            self._hero_browser.load_heroes(heroes)
            self._navigate(_TAB_HEROES)
        else:
            self._navigate(_TAB_SCAN)

        self._checker = UpdateChecker(self)
        self._checker.update_available.connect(self._update_banner.show_update)
        self._checker.start()

    def _navigate(self, index: int):
        self._stack.setCurrentIndex(index)
        self._nav.set_active(index)

    def _on_scan_complete(self, _heroes: list = None):
        heroes = HeroRepository(self._db).get_all()
        self._hero_browser.load_heroes(heroes)
        self._navigate(_TAB_HEROES)

    def _on_wiki_hero_requested(self, hero_name: str):
        self._navigate(_TAB_WIKI)
        self._hero_info.set_query(f"Tell me about {hero_name}")

    def _on_sync_complete(self):
        import data.heroes as _heroes_mod
        _heroes_mod._reload()

        self._teamups_panel.load()

        heroes = HeroRepository(self._db).get_all()
        if heroes:
            self._hero_browser.load_heroes(heroes)
