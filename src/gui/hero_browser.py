import csv
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel,
    QFileDialog, QMessageBox, QScrollArea, QGridLayout, QDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal

from gui.excel_import import generate_template, import_from_excel
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
}


class _HeroDetailDialog(QDialog):
    def __init__(self, hero: Hero, parent=None):
        super().__init__(parent)
        self.setWindowTitle(hero.name)
        self.setMinimumWidth(480)
        self.setModal(True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        panel = HeroDetailPanel()
        panel.set_hero(hero)
        lay.addWidget(panel)


class _HeroGrid(QWidget):
    card_clicked = pyqtSignal(object)

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
            card = HeroCard(hero)
            card.clicked.connect(self.card_clicked)
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
        # Push cards to the top; don't stretch them vertically
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


class HeroBrowser(QWidget):
    def __init__(self, db: Database = None, parent=None):
        super().__init__(parent)
        self._db = db
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 6, 8, 6)
        toolbar.setSpacing(8)

        export_btn = QPushButton("Export CSV")
        export_btn.setFixedWidth(100)
        export_btn.clicked.connect(self._export_csv)
        toolbar.addWidget(export_btn)

        template_btn = QPushButton("Get Template")
        template_btn.setFixedWidth(110)
        template_btn.clicked.connect(self._save_template)
        toolbar.addWidget(template_btn)

        import_btn = QPushButton("Import Excel")
        import_btn.setFixedWidth(110)
        import_btn.clicked.connect(self._import_excel)
        toolbar.addWidget(import_btn)

        manual_btn = QPushButton("+ Manual Entry")
        manual_btn.setFixedWidth(120)
        manual_btn.clicked.connect(self._open_manual_entry)
        toolbar.addWidget(manual_btn)

        toolbar.addWidget(QLabel("Role:"))
        self._role_combo = QComboBox()
        self._role_combo.addItems(_ROLE_FILTERS.keys())
        self._role_combo.setFixedWidth(110)
        self._role_combo.currentIndexChanged.connect(self._apply_sort)
        toolbar.addWidget(self._role_combo)

        toolbar.addWidget(QLabel("Sort:"))
        self._sort_combo = QComboBox()
        self._sort_combo.addItems(_SORT_OPTIONS.keys())
        self._sort_combo.setFixedWidth(160)
        self._sort_combo.currentIndexChanged.connect(self._apply_sort)
        toolbar.addWidget(self._sort_combo)

        self._dir_btn = QPushButton("↑ Asc")
        self._dir_btn.setFixedWidth(60)
        self._dir_btn.setCheckable(True)
        self._dir_btn.clicked.connect(self._toggle_direction)
        toolbar.addWidget(self._dir_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._grid = _HeroGrid()
        self._grid.card_clicked.connect(self._show_detail)
        scroll.setWidget(self._grid)
        layout.addWidget(scroll)

        self._all_heroes: list[Hero] = []
        self._heroes: list[Hero] = []
        self._descending = False

    def load_heroes(self, heroes: list[Hero]):
        self._all_heroes = list(heroes)
        self._apply_sort()

    def _apply_sort(self):
        role_filter = _ROLE_FILTERS[self._role_combo.currentText()]
        filtered = (
            [h for h in self._all_heroes if h.role == role_filter]
            if role_filter else list(self._all_heroes)
        )
        key_fn = _SORT_OPTIONS[self._sort_combo.currentText()]
        filtered.sort(key=key_fn, reverse=self._descending)
        self._heroes = filtered
        self._grid.set_heroes(filtered)

    def _toggle_direction(self):
        self._descending = self._dir_btn.isChecked()
        self._dir_btn.setText("↓ Desc" if self._descending else "↑ Asc")
        self._apply_sort()

    def _show_detail(self, hero: Hero):
        dlg = _HeroDetailDialog(hero, self)
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
