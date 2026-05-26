import random

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap

from models.hero import Hero
from data.xp_table import TOTAL_XP_FOR_LORD, total_xp_earned
from gui.hero_detail import _icon_path

_LORD_LEVEL   = 20
_ICON_SIZE    = 160

_ROLE_OPTIONS = ["All Roles", "Vanguard", "Duelist", "Strategist"]

_ROLE_COLORS = {
    "Vanguard":   "#4a90d9",
    "Duelist":    "#d94a4a",
    "Strategist": "#4ad98a",
    "Multi-Role": "#d9a44a",
}

_MULTI_ROLE_HERO = "Deadpool"

_FAST_TICKS        = 25
_SLOW_TICKS        = 7
_FAST_INTERVAL_MS  = 50


class TrainingPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_heroes: list[Hero] = []
        self._filtered:   list[Hero] = []
        self._spin_tick   = 0
        self._spin_target: Hero | None = None
        self._pixmaps:    dict[str, QPixmap] = {}

        self._spin_timer = QTimer(self)
        self._spin_timer.timeout.connect(self._on_spin_tick)

        self._build_ui()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        title = QLabel("RANDOM HERO TRAINING")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "font-family: Impact, 'Arial Narrow', Arial;"
            " font-size: 20px; letter-spacing: 4px; color: #f4d641;"
        )
        root.addWidget(title)

        root.addSpacing(4)

        subtitle = QLabel("Pick a random hero that hasn't earned Lord (LV20) yet")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #484860; font-size: 12px;")
        root.addWidget(subtitle)

        root.addSpacing(24)

        # Role filter
        filter_row = QHBoxLayout()
        filter_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        filter_row.setSpacing(10)

        role_lbl = QLabel("ROLE")
        role_lbl.setStyleSheet(
            "font-family: Impact, 'Arial Narrow', Arial;"
            " font-size: 11px; letter-spacing: 2px; color: #606078;"
        )
        filter_row.addWidget(role_lbl)

        self._role_combo = QComboBox()
        self._role_combo.addItems(_ROLE_OPTIONS)
        self._role_combo.setFixedWidth(160)
        self._role_combo.currentTextChanged.connect(self._on_role_changed)
        filter_row.addWidget(self._role_combo)

        root.addLayout(filter_row)

        root.addSpacing(24)

        # Icon display
        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(_ICON_SIZE, _ICON_SIZE)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_lbl.setStyleSheet(
            "background: #080810; border: 1px solid #1a1a2c; border-radius: 6px;"
        )

        icon_row = QHBoxLayout()
        icon_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_row.addWidget(self._icon_lbl)
        root.addLayout(icon_row)

        root.addSpacing(14)

        # Hero name (shown after spin settles)
        self._name_lbl = QLabel("—")
        self._name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_lbl.setStyleSheet(self._name_style("#363650"))
        root.addWidget(self._name_lbl)

        root.addSpacing(4)

        self._role_result_lbl = QLabel("")
        self._role_result_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._role_result_lbl.setStyleSheet(
            "font-family: Impact, 'Arial Narrow', Arial;"
            " font-size: 12px; letter-spacing: 2px; color: #363650;"
        )
        root.addWidget(self._role_result_lbl)

        self._xp_lbl = QLabel("")
        self._xp_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._xp_lbl.setStyleSheet("font-size: 12px; color: #363650;")
        root.addWidget(self._xp_lbl)

        root.addSpacing(20)

        # Spin button
        self._spin_btn = QPushButton("SPIN")
        self._spin_btn.setFixedSize(160, 48)
        self._spin_btn.setStyleSheet(
            "QPushButton {"
            " font-family: Impact, 'Arial Narrow', Arial;"
            " font-size: 18px; letter-spacing: 4px;"
            " background: #f4d641; color: #0c0c14;"
            " border: none; border-radius: 4px;"
            "}"
            "QPushButton:hover   { background: #ffe066; }"
            "QPushButton:pressed { background: #c8b030; }"
            "QPushButton:disabled { background: #1a1a2c; color: #363650; }"
        )
        self._spin_btn.clicked.connect(self._start_spin)
        self._spin_btn.setEnabled(False)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_row.addWidget(self._spin_btn)
        root.addLayout(btn_row)

        root.addSpacing(10)

        self._pool_lbl = QLabel("")
        self._pool_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pool_lbl.setStyleSheet("color: #363650; font-size: 11px;")
        root.addWidget(self._pool_lbl)

        root.addStretch()

    # ── Public API ───────────────────────────────────────────────────────────

    def load_heroes(self, heroes: list[Hero]):
        self._all_heroes = heroes
        self._cache_pixmaps(heroes)
        self._on_role_changed(self._role_combo.currentText())

    # ── Internals ────────────────────────────────────────────────────────────

    def _cache_pixmaps(self, heroes: list[Hero]):
        self._pixmaps.clear()
        for h in heroes:
            path = _icon_path(h.name, h.level)
            if path:
                px = QPixmap(path).scaled(
                    _ICON_SIZE, _ICON_SIZE,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._pixmaps[h.name] = px

    def _on_role_changed(self, role: str):
        self._filtered = [
            h for h in self._all_heroes
            if h.level < _LORD_LEVEL
            and (role == "All Roles" or h.role == role or h.name == _MULTI_ROLE_HERO)
        ]
        n = len(self._filtered)
        if n == 0:
            self._pool_lbl.setText("No eligible heroes — scan first or all heroes already have Lord")
            self._spin_btn.setEnabled(False)
        else:
            self._pool_lbl.setText(f"{n} eligible hero{'es' if n != 1 else ''} in pool")
            self._spin_btn.setEnabled(not self._spin_timer.isActive())

    def _start_spin(self):
        if not self._filtered:
            return

        self._spin_target = random.choice(self._filtered)
        self._spin_tick = 0

        self._spin_btn.setEnabled(False)
        self._name_lbl.setText("")
        self._name_lbl.setStyleSheet(self._name_style("#363650"))
        self._role_result_lbl.setText("")
        self._xp_lbl.setText("")
        self._icon_lbl.clear()
        self._icon_lbl.setStyleSheet(
            "background: #080810; border: 1px solid #1a1a2c; border-radius: 6px;"
        )
        self._spin_timer.start(_FAST_INTERVAL_MS)

    def _on_spin_tick(self):
        self._spin_tick += 1
        t = self._spin_tick

        self._set_icon(random.choice(self._filtered).name)

        if t <= _FAST_TICKS:
            self._spin_timer.setInterval(_FAST_INTERVAL_MS)
        elif t <= _FAST_TICKS + _SLOW_TICKS:
            self._spin_timer.setInterval(_FAST_INTERVAL_MS + (t - _FAST_TICKS) * 40)
        else:
            self._spin_timer.stop()
            self._show_result(self._spin_target)

    def _set_icon(self, hero_name: str):
        px = self._pixmaps.get(hero_name)
        if px:
            self._icon_lbl.setPixmap(px)
        else:
            self._icon_lbl.clear()

    def _show_result(self, hero: Hero):
        self._set_icon(hero.name)
        self._icon_lbl.setStyleSheet(
            "background: #080810;"
            " border: 2px solid #f4d641; border-radius: 6px;"
        )

        self._name_lbl.setText(hero.name)
        self._name_lbl.setStyleSheet(self._name_style("#f4d641"))

        role_color = _ROLE_COLORS.get(hero.role, "#a8a8c0")
        self._role_result_lbl.setText(hero.role.upper())
        self._role_result_lbl.setStyleSheet(
            f"font-family: Impact, 'Arial Narrow', Arial;"
            f" font-size: 12px; letter-spacing: 2px; color: {role_color};"
        )

        xp = total_xp_earned(hero.level, hero.xp)
        pct = min(100, round(xp / TOTAL_XP_FOR_LORD * 100, 1))
        self._xp_lbl.setText(
            f"LV {hero.level}  ·  {xp:,} / {TOTAL_XP_FOR_LORD:,} XP to Lord  ({pct}%)"
        )
        self._xp_lbl.setStyleSheet("font-size: 12px; color: #7878a0;")

        self._spin_btn.setEnabled(True)

    @staticmethod
    def _name_style(color: str) -> str:
        return (
            "font-family: Impact, 'Arial Narrow', Arial;"
            f" font-size: 28px; letter-spacing: 3px; color: {color};"
        )
