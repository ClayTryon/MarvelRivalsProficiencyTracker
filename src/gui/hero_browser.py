from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QPushButton, QComboBox, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal
from gui.hero_detail import HeroDetailPanel
from models.hero import Hero

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


class HeroBrowser(QWidget):
    new_scan_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 6, 8, 6)
        toolbar.setSpacing(8)

        new_scan_btn = QPushButton("← New Scan")
        new_scan_btn.setFixedWidth(110)
        new_scan_btn.clicked.connect(self.new_scan_requested)
        toolbar.addWidget(new_scan_btn)

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

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._list = QListWidget()
        self._list.setMinimumWidth(200)
        self._detail = HeroDetailPanel()

        self._splitter.addWidget(self._list)
        self._splitter.addWidget(self._detail)
        self._splitter.setSizes([220, 680])
        layout.addWidget(self._splitter)

        self._all_heroes: list[Hero] = []
        self._heroes: list[Hero] = []
        self._descending = False
        self._list.currentRowChanged.connect(self._on_selection_changed)

    def load_heroes(self, heroes: list[Hero]):
        self._all_heroes = list(heroes)
        self._apply_sort()

    def _apply_sort(self):
        role_filter = _ROLE_FILTERS[self._role_combo.currentText()]
        if role_filter:
            filtered = [h for h in self._all_heroes if h.role == role_filter]
        else:
            filtered = list(self._all_heroes)

        key_fn = _SORT_OPTIONS[self._sort_combo.currentText()]
        filtered.sort(key=key_fn, reverse=self._descending)

        selected_name = None
        if 0 <= self._list.currentRow() < len(self._heroes):
            selected_name = self._heroes[self._list.currentRow()].name

        self._heroes = filtered
        self._list.blockSignals(True)
        self._list.clear()
        for hero in self._heroes:
            self._list.addItem(QListWidgetItem(hero.name))
        self._list.blockSignals(False)

        if selected_name:
            for i, h in enumerate(self._heroes):
                if h.name == selected_name:
                    self._list.setCurrentRow(i)
                    return
        if self._heroes:
            self._list.setCurrentRow(0)
        else:
            self._detail.clear()

    def _toggle_direction(self):
        self._descending = self._dir_btn.isChecked()
        self._dir_btn.setText("↓ Desc" if self._descending else "↑ Asc")
        self._apply_sort()

    def _on_selection_changed(self, row: int):
        if 0 <= row < len(self._heroes):
            self._detail.set_hero(self._heroes[row])
        else:
            self._detail.clear()
