import webbrowser

from PyQt6.QtWidgets import (
    QMainWindow, QStackedWidget, QWidget,
    QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal

from gui.colors import (
    BG_APP, BG_DEEP, BORDER, BORDER_MID, BORDER_NAV,
    TEXT_DIM, TEXT_NAV_HOVER, TEXT_VER,
    GOLD, GOLD_HOVER, DARK, UPDATE_BG,
)
from gui.scan_panel import ScanPanel
from gui.hero_browser import HeroBrowser
from gui.hero_info_panel import HeroInfoPanel
from gui.sync_panel import SyncPanel
from gui.training_panel import TrainingPanel
from gui.update_checker import UpdateChecker
from storage.database import Database
from storage.repository import HeroRepository
from version import __version__

_TAB_HEROES = 0
_TAB_SCAN   = 1
_TAB_WIKI   = 2
_TAB_SYNC   = 3  # hidden from nav bar — reachable only via ⟳ SYNC button

_TAB_LABELS = ["HEROES", "SCAN", "WIKI"]


class _NavBar(QWidget):
    tab_clicked = pyqtSignal(int)

    _ACTIVE = (
        "QPushButton {"
        " font-family: Impact, 'Arial Narrow', Arial;"
        " font-size: 13px; letter-spacing: 2px;"
        f" color: #ffffff; background: transparent; border: none;"
        f" border-bottom: 2px solid {GOLD}; padding: 0 14px;"
        " margin-bottom: -1px;"
        "}"
    )
    _INACTIVE = (
        "QPushButton {"
        " font-family: Impact, 'Arial Narrow', Arial;"
        " font-size: 13px; letter-spacing: 2px;"
        f" color: {TEXT_DIM}; background: transparent; border: none;"
        " padding: 0 14px;"
        "}"
        f"QPushButton:hover {{ color: {TEXT_NAV_HOVER}; }}"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(
            f"background: {BG_DEEP}; border-bottom: 1px solid {BORDER_MID};"
        )

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(0)

        logo = QLabel("PROFTRACKER")
        logo.setStyleSheet(
            "font-family: Impact, 'Arial Narrow', Arial;"
            " font-size: 14px; letter-spacing: 4px;"
            f" color: {GOLD}; padding-right: 28px;"
        )
        row.addWidget(logo)

        self._tab_btns: list[QPushButton] = []
        for i, label in enumerate(_TAB_LABELS):
            if i > 0:
                sep = QLabel("/")
                sep.setStyleSheet(f"color: {BORDER_NAV}; font-size: 15px; padding: 0 2px;")
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
            f"QPushButton {{ background: transparent; color: {TEXT_DIM};"
            f" border: 1px solid {BORDER}; border-radius: 3px;"
            f" font-size: 11px; letter-spacing: 1px; padding: 0 10px; }}"
            f" QPushButton:hover {{ color: {GOLD}; border-color: {GOLD}; }}"
        )
        sync_btn.clicked.connect(lambda: self.tab_clicked.emit(_TAB_SYNC))
        row.addWidget(sync_btn)

        ver = QLabel(f"v{__version__}")
        ver.setStyleSheet(f"color: {TEXT_VER}; font-size: 11px; padding-left: 10px;")
        row.addWidget(ver)

        self.set_active(0)

    def set_active(self, index: int):
        for i, btn in enumerate(self._tab_btns):
            btn.setStyleSheet(self._ACTIVE if i == index else self._INACTIVE)


class _UpdateBanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._url = ""
        self.setStyleSheet(f"background: {UPDATE_BG}; border-bottom: 1px solid {GOLD};")
        self.setFixedHeight(32)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 0, 12, 0)

        self._label = QLabel()
        self._label.setStyleSheet(f"color: {GOLD}; font-size: 12px;")
        row.addWidget(self._label)
        row.addStretch()

        download_btn = QPushButton("Download")
        download_btn.setFixedHeight(22)
        download_btn.setStyleSheet(
            f"QPushButton {{ background: {GOLD}; color: {DARK}; border: none;"
            " border-radius: 3px; font-size: 11px; font-weight: bold; padding: 0 10px; }"
            f" QPushButton:hover {{ background: {GOLD_HOVER}; }}"
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


class _WikiTab(QWidget):
    """WIKI top-level tab: sub-tabs for Hero Wiki (RAG chat) and Training."""

    _SUB_ACTIVE = (
        "QPushButton {"
        " font-family: Impact, 'Arial Narrow', Arial;"
        " font-size: 11px; letter-spacing: 2px;"
        f" color: #ffffff; background: transparent; border: none;"
        f" border-bottom: 2px solid {GOLD}; padding: 0 12px;"
        " margin-bottom: -1px;"
        "}"
    )
    _SUB_INACTIVE = (
        "QPushButton {"
        " font-family: Impact, 'Arial Narrow', Arial;"
        " font-size: 11px; letter-spacing: 2px;"
        f" color: {TEXT_DIM}; background: transparent; border: none;"
        " padding: 0 12px;"
        "}"
        f"QPushButton:hover {{ color: {TEXT_NAV_HOVER}; }}"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sub_bar = QWidget()
        sub_bar.setStyleSheet(
            f"background: {BG_DEEP}; border-bottom: 1px solid {BORDER_MID};"
        )
        sub_bar.setFixedHeight(36)
        sub_row = QHBoxLayout(sub_bar)
        sub_row.setContentsMargins(16, 0, 16, 0)
        sub_row.setSpacing(0)

        self._wiki_btn = QPushButton("HERO WIKI")
        self._wiki_btn.setFlat(True)
        self._wiki_btn.setFixedHeight(36)
        self._wiki_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._wiki_btn.clicked.connect(lambda: self._switch(0))
        sub_row.addWidget(self._wiki_btn)

        sep = QLabel("/")
        sep.setStyleSheet(f"color: {BORDER_NAV}; font-size: 15px; padding: 0 4px;")
        sub_row.addWidget(sep)

        self._train_btn = QPushButton("TRAINING")
        self._train_btn.setFlat(True)
        self._train_btn.setFixedHeight(36)
        self._train_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._train_btn.clicked.connect(lambda: self._switch(1))
        sub_row.addWidget(self._train_btn)
        sub_row.addStretch()
        root.addWidget(sub_bar)

        self._stack = QStackedWidget()
        self._hero_info = HeroInfoPanel()
        self._training = TrainingPanel()
        self._stack.addWidget(self._hero_info)
        self._stack.addWidget(self._training)
        root.addWidget(self._stack, stretch=1)

        self._switch(0)

    def _switch(self, index: int):
        self._stack.setCurrentIndex(index)
        self._wiki_btn.setStyleSheet(self._SUB_ACTIVE if index == 0 else self._SUB_INACTIVE)
        self._train_btn.setStyleSheet(self._SUB_ACTIVE if index == 1 else self._SUB_INACTIVE)

    def set_query(self, text: str):
        self._switch(0)
        self._hero_info.set_query(text)

    def load_heroes(self, heroes):
        self._training.load_heroes(heroes)


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
        self._stack.setStyleSheet(f"background: {BG_APP};")

        self._hero_browser = HeroBrowser(db)
        self._scan_panel   = ScanPanel(db)
        self._wiki_tab     = _WikiTab()
        self._sync_panel   = SyncPanel()

        self._stack.addWidget(self._hero_browser)  # 0 — HEROES
        self._stack.addWidget(self._scan_panel)    # 1 — SCAN
        self._stack.addWidget(self._wiki_tab)      # 2 — WIKI
        self._stack.addWidget(self._sync_panel)    # 3 — SYNC (hidden from nav)
        root.addWidget(self._stack)

        self.setCentralWidget(central)

        self._scan_panel.scan_complete.connect(self._on_scan_complete)
        self._scan_panel.hwnd_selected.connect(self._hero_browser.set_hwnd)
        self._sync_panel.sync_complete.connect(self._on_sync_complete)
        self._hero_browser.wiki_hero_requested.connect(self._on_wiki_hero_requested)

        heroes = HeroRepository(db).get_all()
        if heroes:
            self._hero_browser.load_heroes(heroes)
            self._wiki_tab.load_heroes(heroes)
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
        self._wiki_tab.load_heroes(heroes)
        self._navigate(_TAB_HEROES)

    def _on_wiki_hero_requested(self, hero_name: str):
        self._navigate(_TAB_WIKI)
        self._wiki_tab.set_query(f"Tell me about {hero_name}")

    def _on_sync_complete(self):
        import data.heroes as _heroes_mod
        from storage.repository import seed_default_heroes
        _heroes_mod._reload()
        seed_default_heroes(self._db)

        heroes = HeroRepository(self._db).get_all()
        if heroes:
            self._hero_browser.load_heroes(heroes)
            self._wiki_tab.load_heroes(heroes)
