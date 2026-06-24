from datetime import datetime, timezone

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QComboBox, QLabel, QSpinBox, QCheckBox, QMessageBox,
)
from data.heroes import HERO_ROSTER, HERO_ROLES
from data.xp_table import XP_PER_LEVEL
from exceptions import ValidationError
from models.capture_run import CaptureStatus
from models.hero import Hero
from storage.database import Database
from storage.repository import CaptureRunRepository, HeroRepository, SnapshotRepository
from gui.colors import TEXT_LIGHT_GRAY

_MAX_LEVEL = max(XP_PER_LEVEL.keys())  # 70


class ManualEntryDialog(QDialog):
    def __init__(self, db: Database, parent=None, initial_hero: str | None = None):
        super().__init__(parent)
        self._db = db
        self.setWindowTitle("Manual Hero Entry")
        self.setMinimumWidth(380)
        self.setModal(True)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._hero_combo = QComboBox()
        self._hero_combo.addItems(HERO_ROSTER)
        self._hero_combo.currentTextChanged.connect(self._on_hero_changed)
        form.addRow("Hero:", self._hero_combo)

        self._role_lbl = QLabel()
        self._role_lbl.setStyleSheet(f"color: {TEXT_LIGHT_GRAY};")
        form.addRow("Role:", self._role_lbl)

        self._level_spin = QSpinBox()
        self._level_spin.setRange(1, _MAX_LEVEL)
        self._level_spin.valueChanged.connect(self._on_level_changed)
        form.addRow("Level:", self._level_spin)

        self._max_check = QCheckBox(f"Max Level (LV {_MAX_LEVEL})")
        self._max_check.toggled.connect(self._on_max_toggled)
        form.addRow("", self._max_check)

        self._xp_req_lbl = QLabel()
        self._xp_req_lbl.setStyleSheet(f"color: {TEXT_LIGHT_GRAY};")
        form.addRow("XP Required:", self._xp_req_lbl)

        self._xp_spin = QSpinBox()
        self._xp_spin.setRange(0, 0)
        form.addRow("Current XP:", self._xp_spin)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        self._existing: dict[str, Hero] = {
            h.name: h for h in HeroRepository(db).get_all()
        }

        if initial_hero and self._hero_combo.findText(initial_hero) >= 0:
            self._hero_combo.setCurrentText(initial_hero)
        else:
            self._on_hero_changed(self._hero_combo.currentText())

    def _on_hero_changed(self, name: str):
        self._role_lbl.setText(HERO_ROLES.get(name, "Unknown"))
        hero = self._existing.get(name)
        if hero:
            self._max_check.blockSignals(True)
            self._level_spin.blockSignals(True)
            self._max_check.setChecked(hero.is_max_level)
            self._level_spin.setValue(hero.level)
            self._max_check.blockSignals(False)
            self._level_spin.blockSignals(False)
            self._on_max_toggled(hero.is_max_level) if hero.is_max_level else self._on_level_changed(hero.level)
            self._xp_spin.setValue(hero.xp)
        else:
            self._max_check.blockSignals(True)
            self._level_spin.blockSignals(True)
            self._max_check.setChecked(False)
            self._level_spin.setValue(1)
            self._max_check.blockSignals(False)
            self._level_spin.blockSignals(False)
            self._on_level_changed(1)
            self._xp_spin.setValue(0)

    def _on_level_changed(self, level: int):
        if self._max_check.isChecked():
            return
        xp_req = XP_PER_LEVEL.get(level, 0)
        self._xp_req_lbl.setText(str(xp_req))
        self._xp_spin.setMaximum(max(0, xp_req - 1))
        if level == _MAX_LEVEL:
            self._max_check.setChecked(True)

    def _on_max_toggled(self, checked: bool):
        self._xp_spin.setEnabled(not checked)
        self._xp_req_lbl.setEnabled(not checked)
        if checked:
            self._level_spin.blockSignals(True)
            self._level_spin.setValue(_MAX_LEVEL)
            self._level_spin.blockSignals(False)
            self._xp_req_lbl.setText("0")
            self._xp_spin.setValue(0)
        else:
            self._on_level_changed(self._level_spin.value())

    def _save(self):
        name = self._hero_combo.currentText()
        role = HERO_ROLES.get(name, "Unknown")
        level = self._level_spin.value()
        is_max = self._max_check.isChecked()
        xp = 0 if is_max else self._xp_spin.value()
        xp_required = 0 if is_max else XP_PER_LEVEL.get(level, 0)

        # Validate before touching the DB
        draft = Hero(
            name=name, role=role, level=level, xp=xp,
            xp_required=xp_required, is_max_level=is_max,
            capture_run_id=0,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        try:
            draft.validate()
        except ValidationError as e:
            QMessageBox.warning(self, "Validation Error", str(e))
            return

        run_repo = CaptureRunRepository(self._db)
        run = run_repo.create()
        draft.capture_run_id = run.id

        HeroRepository(self._db).upsert(draft)
        SnapshotRepository(self._db).insert(draft)
        run_repo.update_status(run.id, CaptureStatus.COMPLETED, hero_count=1)

        self.accept()
