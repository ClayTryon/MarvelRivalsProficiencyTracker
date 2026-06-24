import csv
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel,
    QFileDialog, QMessageBox, QScrollArea, QGridLayout, QDialog, QMenu, QLineEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings

from gui.colors import (
    BG_DEEP, BG_SINK, BORDER, BORDER_MID, BORDER_DEEP, BORDER_NAV,
    TEXT_DIM, TEXT_BRONZE,
)
from gui.excel_import import generate_template, import_from_excel
from data.heroes import HERO_RELEASE_DATES
from gui.hero_card import HeroCard
from gui.hero_detail import HeroDetailPanel
from gui.manual_entry_dialog import ManualEntryDialog
from models.hero import Hero
from storage.database import Database
from storage.repository import HeroRepository

_SORT_OPTIONS = {
    "Closest to Lord":     lambda h: (0 if h.level < 20 else 1, 20 - h.level, -(h.xp or 0)),
    "Closest to Champion": lambda h: (0 if h.level < 50 else 1, 50 - h.level, -(h.xp or 0)),
    "Alphabetical":        lambda h: h.name,
    "Level":               lambda h: h.level,
}

_ROLE_FILTERS = {
    "All Roles":  None,
    "Vanguard":   "Vanguard",
    "Duelist":    "Duelist",
    "Strategist": "Strategist",
    "Multi-Role": "Multi-Role",
}

_TIER_LABELS = ["Lord", "Champion", "Normal Hero"]

_ROLE_SECTIONS = [
    ("Tanks — Vanguard",      "Vanguard"),
    ("DPS — Duelist",         "Duelist"),
    ("Supports — Strategist", "Strategist"),
    ("Multi-Role",            "Multi-Role"),
]


def _hero_tier(h: Hero) -> str:
    if h.is_max_level:
        return "Champion"
    if h.level >= 20:
        return "Lord"
    return "Normal Hero"


class _HeroDetailDialog(QDialog):
    def __init__(self, hero: Hero, db=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(hero.name)
        self.setMinimumSize(560, 680)
        self.setModal(True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        self.panel = HeroDetailPanel(db)
        self.panel.set_hero(hero)
        lay.addWidget(self.panel)


class _HeroGrid(QWidget):
    card_clicked                  = pyqtSignal(object)
    card_edit_requested           = pyqtSignal(object)
    card_wiki_requested           = pyqtSignal(object)
    card_clipboard_scan_requested = pyqtSignal(object)

    _GAP = 10
    _PAD = 16

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: list[HeroCard] = []
        self._cols = 5

        self._lay = QGridLayout(self)
        self._lay.setSpacing(self._GAP)
        self._lay.setContentsMargins(self._PAD, self._PAD, self._PAD, self._PAD)

    def set_heroes(self, heroes: list[Hero]):
        for card in self._cards:
            self._lay.removeWidget(card)
            card.deleteLater()
        self._cards = []

        for hero in heroes:
            card = HeroCard(hero, release_date=HERO_RELEASE_DATES.get(hero.name))
            card.clicked.connect(self.card_clicked)
            card.edit_requested.connect(self.card_edit_requested)
            card.wiki_requested.connect(self.card_wiki_requested)
            card.clipboard_scan_requested.connect(self.card_clipboard_scan_requested)
            self._cards.append(card)

        self._cols = self._calc_cols(self.width())
        self._place_cards()

    def _calc_cols(self, w: int) -> int:
        if w <= 0:
            return 5
        usable = w - 2 * self._PAD
        return max(1, (usable + self._GAP) // (HeroCard.W + self._GAP))

    def _place_cards(self):
        while self._lay.count():
            self._lay.takeAt(0)
        for i, card in enumerate(self._cards):
            row, col = divmod(i, self._cols)
            self._lay.addWidget(card, row, col)
        bottom_row = (len(self._cards) + self._cols - 1) // self._cols if self._cards else 0
        self._lay.setRowStretch(bottom_row, 1)

    def minimumSizeHint(self):
        from PyQt6.QtCore import QSize
        return QSize(HeroCard.W + 2 * self._PAD, 0)

    def resizeEvent(self, event):
        new_cols = self._calc_cols(event.size().width())
        if new_cols != self._cols and self._cards:
            self._cols = new_cols
            self._place_cards()
        super().resizeEvent(event)


class _ShowAllDialog(QDialog):
    _HEADER_STYLE = (
        f"color: {TEXT_BRONZE}; font-size: 13px; font-weight: bold;"
        f" padding: 6px 0 4px; border-bottom: 1px solid {BORDER_NAV};"
    )
    _EMPTY_STYLE = f"color: {TEXT_DIM}; font-size: 11px; padding: 4px 12px;"

    def __init__(self, tier: str, heroes: list[Hero], db=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"All {tier} Heroes")
        self.setMinimumSize(860, 560)
        self._db = db
        self._build_ui(tier, heroes)

    def _build_ui(self, tier: str, heroes: list[Hero]):
        tier_heroes = [h for h in heroes if _hero_tier(h) == tier]

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        if not tier_heroes:
            lbl = QLabel(f"No {tier} heroes found.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px; padding: 40px;")
            outer.addWidget(lbl)
            return

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(14)

        for section_label, role_key in _ROLE_SECTIONS:
            role_heroes = [h for h in tier_heroes if h.role == role_key]
            header = QLabel(f"{section_label}  ({len(role_heroes)})")
            header.setStyleSheet(self._HEADER_STYLE)
            lay.addWidget(header)

            if role_heroes:
                grid = _HeroGrid()
                grid.set_heroes(role_heroes)
                grid.card_clicked.connect(self._on_card_clicked)
                lay.addWidget(grid)
            else:
                no_lbl = QLabel("None")
                no_lbl.setStyleSheet(self._EMPTY_STYLE)
                lay.addWidget(no_lbl)

        lay.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _on_card_clicked(self, hero: Hero):
        dlg = _HeroDetailDialog(hero, self._db, self)
        dlg.exec()


class HeroBrowser(QWidget):
    wiki_hero_requested = pyqtSignal(str)

    def __init__(self, db: Database = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._hwnd: int | None = None
        self._settings = QSettings("ProfTracker", "HeroBrowser")
        self._all_heroes: list[Hero] = []
        self._heroes: list[Hero] = []
        self._descending = False
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._build_toolbar()
        self._build_stats_bar()
        self._build_grid()
        self._load_settings()

    def _build_toolbar(self):
        toolbar_widget = QWidget()
        toolbar_widget.setStyleSheet(
            f"QWidget {{ background: {BG_DEEP}; border-bottom: 1px solid {BORDER_MID}; }}"
        )
        toolbar = QHBoxLayout(toolbar_widget)
        toolbar.setContentsMargins(14, 8, 14, 8)
        toolbar.setSpacing(8)

        manual_btn = QPushButton("+ Add Hero")
        manual_btn.clicked.connect(self._open_manual_entry)
        toolbar.addWidget(manual_btn)

        more_btn = QPushButton("⋯")
        more_btn.setFixedWidth(36)
        more_menu = QMenu(more_btn)
        more_menu.addAction("Export CSV", self._export_csv)
        more_menu.addSeparator()
        more_menu.addAction("Import Excel", self._import_excel)
        more_menu.addAction("Get Template", self._save_template)
        more_btn.setMenu(more_menu)
        toolbar.addWidget(more_btn)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search heroes...")
        self._search.setFixedWidth(180)
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._apply_sort)
        toolbar.addWidget(self._search)

        toolbar.addStretch()

        tier_lbl = QLabel("TIER")
        tier_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; letter-spacing: 1px;")
        toolbar.addWidget(tier_lbl)
        self._tier_combo = QComboBox()
        self._tier_combo.addItems(_TIER_LABELS)
        self._tier_combo.setFixedWidth(110)
        toolbar.addWidget(self._tier_combo)

        show_all_btn = QPushButton("Show All")
        show_all_btn.clicked.connect(self._open_show_all)
        toolbar.addWidget(show_all_btn)

        _sep = QLabel("|")
        _sep.setStyleSheet(f"color: {BORDER}; padding: 0 2px;")
        toolbar.addWidget(_sep)

        role_lbl = QLabel("ROLE")
        role_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; letter-spacing: 1px;")
        toolbar.addWidget(role_lbl)
        self._role_combo = QComboBox()
        self._role_combo.addItems(_ROLE_FILTERS.keys())
        self._role_combo.setFixedWidth(110)
        self._role_combo.currentIndexChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self._role_combo)

        sort_lbl = QLabel("SORT")
        sort_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; letter-spacing: 1px;")
        toolbar.addWidget(sort_lbl)
        self._sort_combo = QComboBox()
        self._sort_combo.addItems(_SORT_OPTIONS.keys())
        self._sort_combo.setFixedWidth(160)
        self._sort_combo.currentIndexChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self._sort_combo)

        self._dir_btn = QPushButton("↑")
        self._dir_btn.setFixedWidth(32)
        self._dir_btn.setCheckable(True)
        self._dir_btn.clicked.connect(self._toggle_direction)
        toolbar.addWidget(self._dir_btn)

        self._layout.addWidget(toolbar_widget)

    def _build_stats_bar(self):
        self._stats_bar = QLabel()
        self._stats_bar.setStyleSheet(
            f"background: {BG_SINK}; color: {TEXT_DIM}; font-size: 10px;"
            f" padding: 3px 14px; border-bottom: 1px solid {BORDER_DEEP};"
        )
        self._layout.addWidget(self._stats_bar)

    def _build_grid(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._grid = _HeroGrid()
        self._grid.card_clicked.connect(self._show_detail)
        self._grid.card_edit_requested.connect(self._edit_hero)
        self._grid.card_wiki_requested.connect(
            lambda hero: self.wiki_hero_requested.emit(hero.name)
        )
        self._grid.card_clipboard_scan_requested.connect(self._clipboard_scan)
        scroll.setWidget(self._grid)
        self._layout.addWidget(scroll)

    def _load_settings(self):
        saved_sort = self._settings.value("sort_key", "")
        saved_role = self._settings.value("role_filter", "")
        saved_dir  = self._settings.value("descending", False, type=bool)

        idx = self._sort_combo.findText(saved_sort)
        if idx >= 0:
            self._sort_combo.blockSignals(True)
            self._sort_combo.setCurrentIndex(idx)
            self._sort_combo.blockSignals(False)

        idx = self._role_combo.findText(saved_role)
        if idx >= 0:
            self._role_combo.blockSignals(True)
            self._role_combo.setCurrentIndex(idx)
            self._role_combo.blockSignals(False)

        if saved_dir:
            self._descending = True
            self._dir_btn.setChecked(True)
            self._dir_btn.setText("↓")

    def load_heroes(self, heroes: list[Hero]):
        self._all_heroes = list(heroes)
        self._apply_sort()

    def _apply_sort(self):
        search = self._search.text().strip().lower()
        role_filter = _ROLE_FILTERS[self._role_combo.currentText()]
        filtered = [
            h for h in self._all_heroes
            if (not role_filter or h.role == role_filter)
            and (not search or search in h.name.lower())
        ]
        key_fn = _SORT_OPTIONS[self._sort_combo.currentText()]
        filtered.sort(key=key_fn, reverse=self._descending)
        self._heroes = filtered
        self._grid.set_heroes(filtered)

        lord  = sum(1 for h in self._all_heroes if 20 <= h.level < 50 and not h.is_max_level)
        champ = sum(1 for h in self._all_heroes if h.is_max_level)
        total = len(self._all_heroes)
        shown = len(filtered)
        count_str = f"{shown} of {total}" if search or role_filter else str(total)
        self._stats_bar.setText(
            f"{count_str} heroes  ·  {lord} Lord  ·  {champ} Champion"
        )

    def _on_filter_changed(self):
        self._apply_sort()
        self._settings.setValue("sort_key", self._sort_combo.currentText())
        self._settings.setValue("role_filter", self._role_combo.currentText())
        self._settings.setValue("descending", self._descending)

    def _toggle_direction(self):
        self._descending = self._dir_btn.isChecked()
        self._dir_btn.setText("↓" if self._descending else "↑")
        self._apply_sort()
        self._settings.setValue("descending", self._descending)

    def _open_show_all(self):
        tier = self._tier_combo.currentText()
        dlg = _ShowAllDialog(tier, self._all_heroes, self._db, self)
        dlg.exec()

    def _show_detail(self, hero: Hero):
        dlg = _HeroDetailDialog(hero, self._db, self)
        if self._db:
            uid    = self._settings.value("tracker_uid", "").strip() or None
            season = int(self._settings.value("tracker_season", "0") or "0")
            from storage.repository import TrackerRepository
            summary = TrackerRepository(self._db).get_stats_for_mode(uid, season, "all")
            dlg.panel.set_tracker_stats(summary.get(hero.name))
        dlg.exec()

    def _save_template(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Template", "ProfTracker_Template.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not path:
            return
        try:
            generate_template(path)
            QMessageBox.information(self, "Template Saved", f"Template saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save template:\n{e}")

    def _import_excel(self):
        if not self._db:
            QMessageBox.warning(self, "Import Excel", "No database connection available.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Excel", "", "Excel Files (*.xlsx)"
        )
        if not path:
            return
        try:
            success, errors = import_from_excel(path, self._db)
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"Could not read file:\n{e}")
            return

        self.load_heroes(HeroRepository(self._db).get_all())

        msg = f"Imported {success} hero{'es' if success != 1 else ''}."
        if errors:
            msg += f"\n\n{len(errors)} row(s) skipped:\n" + "\n".join(f"• {e}" for e in errors)
            QMessageBox.warning(self, "Import Complete", msg)
        else:
            QMessageBox.information(self, "Import Complete", msg)

    def set_hwnd(self, hwnd: int):
        self._hwnd = hwnd

    def _clipboard_scan(self, hero: Hero):
        if not self._db:
            return
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QImage
        from PIL import Image
        from storage.repository import CaptureRunRepository
        from models.capture_run import CaptureStatus

        qimg = QApplication.instance().clipboard().image()
        if qimg.isNull():
            QMessageBox.warning(self, "Clipboard Scan", "Clipboard is empty or contains no image.")
            return

        qimg = qimg.convertToFormat(QImage.Format.Format_RGBA8888)
        ptr = qimg.bits()
        ptr.setsize(qimg.height() * qimg.width() * 4)
        pil_image = Image.frombytes('RGBA', (qimg.width(), qimg.height()), bytes(ptr))

        if self._hwnd:
            from capture.navigator import crop_to_client
            pil_image = crop_to_client(pil_image, self._hwnd)

        try:
            from capture.pipeline import capture_one_hero_from_image
            run = CaptureRunRepository(self._db).create()
            result = capture_one_hero_from_image(pil_image, self._db, run.id, hero.name)
            CaptureRunRepository(self._db).update_status(run.id, CaptureStatus.COMPLETED, hero_count=1)
            self.load_heroes(HeroRepository(self._db).get_all())
            xp_str = "MAX" if result.is_max_level else f"{result.xp:,} / {result.xp_required:,} XP"
            QMessageBox.information(self, "Scan Complete", f"{result.name}  LV{result.level}  {xp_str}")
        except Exception as e:
            QMessageBox.critical(self, "Scan Failed", str(e))

    def _edit_hero(self, hero: Hero):
        if not self._db:
            return
        dlg = ManualEntryDialog(self._db, self, initial_hero=hero.name)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_heroes(HeroRepository(self._db).get_all())

    def _open_manual_entry(self):
        if not self._db:
            QMessageBox.warning(self, "Manual Entry", "No database connection available.")
            return
        dlg = ManualEntryDialog(self._db, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_heroes(HeroRepository(self._db).get_all())

    def _export_csv(self):
        if not self._heroes:
            QMessageBox.information(self, "Export CSV", "No heroes to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", "proficiency.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "role", "level", "xp", "xp_required", "is_max_level"])
            for h in self._heroes:
                writer.writerow([h.name, h.role, h.level, h.xp, h.xp_required, h.is_max_level])
        QMessageBox.information(self, "Export CSV", f"Exported {len(self._heroes)} heroes to:\n{path}")
