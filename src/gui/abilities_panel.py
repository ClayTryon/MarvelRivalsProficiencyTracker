import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QFrame, QPushButton,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from wiki_sync.ability_scraper import ability_icon_path
from gui.colors import (
    GOLD, BLUE_ACCENT, DARK,
    BG_INPUT, BG_HOVER_INPUT, BORDER_INPUT,
    TEXT_NEAR_WHITE, TEXT_LIGHT_GRAY, TEXT_GRAY, TEXT_HOVER_GRAY,
    GRAY_55, GRAY_66,
)


_SECTION_COLORS = {
    "Normal Attack":      TEXT_GRAY,
    "Abilities":          GOLD,
    "Team-Up Abilities":  BLUE_ACCENT,
    "General":            TEXT_GRAY,
}

_BTN_ACTIVE = (
    f"QPushButton {{ background: {GOLD}; color: {DARK}; border: none;"
    " border-radius: 3px; font-size: 11px; font-weight: bold;"
    f" letter-spacing: 1px; padding: 4px 14px; }}"
)
_BTN_INACTIVE = (
    f"QPushButton {{ background: {BG_INPUT}; color: {GRAY_66}; border: 1px solid {BORDER_INPUT};"
    " border-radius: 3px; font-size: 11px; font-weight: bold;"
    f" letter-spacing: 1px; padding: 4px 14px; }}"
    f"QPushButton:hover {{ background: {BG_HOVER_INPUT}; color: {TEXT_HOVER_GRAY}; }}"
)


class _AbilityCard(QFrame):
    def __init__(self, ability: dict, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{ background: {BG_INPUT}; border: 1px solid {BG_HOVER_INPUT};"
            " border-radius: 4px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        layout.addLayout(self._build_header_row(ability))
        self._add_description(layout, ability)
        self._add_stats(layout, ability)

    def _build_header_row(self, ability: dict) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        icon_filename = ability.get("icon", "")
        if icon_filename:
            icon_path = ability_icon_path(icon_filename)
            icon_lbl = QLabel()
            icon_lbl.setFixedSize(32, 32)
            icon_lbl.setStyleSheet(
                "background: #ffffff; border-radius: 4px; padding: 2px;"
            )
            if os.path.exists(icon_path):
                px = QPixmap(icon_path).scaled(
                    28, 28,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                icon_lbl.setPixmap(px)
                icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row.addWidget(icon_lbl)

        name_lbl = QLabel(
            f"{ability['name']}"
            + (f"  <span style='color:{GRAY_55};font-size:10px;'>[{ability['key']}]</span>"
               if ability['key'] else "")
        )
        name_lbl.setTextFormat(Qt.TextFormat.RichText)
        name_lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT_NEAR_WHITE};")
        name_lbl.setWordWrap(True)
        row.addWidget(name_lbl, stretch=1)
        return row

    def _add_description(self, layout: QVBoxLayout, ability: dict):
        if ability.get("description"):
            desc = QLabel(ability["description"])
            desc.setWordWrap(True)
            desc.setStyleSheet(f"font-size: 11px; color: {TEXT_LIGHT_GRAY};")
            layout.addWidget(desc)

    def _add_stats(self, layout: QVBoxLayout, ability: dict):
        for stat_name, stat_val in ability.get("stats", {}).items():
            stat_lbl = QLabel(f"<b>{stat_name}:</b> {stat_val}")
            stat_lbl.setTextFormat(Qt.TextFormat.RichText)
            stat_lbl.setWordWrap(True)
            stat_lbl.setStyleSheet(f"font-size: 10px; color: {TEXT_GRAY};")
            layout.addWidget(stat_lbl)


class AbilitiesPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        # Form selector bar — shown only for multi-form heroes
        self._form_bar = QWidget()
        self._form_bar.setStyleSheet("background: transparent;")
        self._form_bar_layout = QHBoxLayout(self._form_bar)
        self._form_bar_layout.setContentsMargins(0, 0, 0, 0)
        self._form_bar_layout.setSpacing(6)
        self._form_bar_layout.addStretch()
        self._form_bar.hide()
        outer.addWidget(self._form_bar)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("background: transparent;")
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._content)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        self._list_layout.addStretch()

        self._scroll.setWidget(self._content)
        outer.addWidget(self._scroll)

        self._abilities: list[dict] = []
        self._forms: list[str] = []
        self._active_form: str | None = None
        self._form_btns: dict[str, QPushButton] = {}

    def load(self, abilities: list[dict]):
        self._abilities = abilities

        # Collect ordered unique forms
        forms: list[str] = []
        for a in abilities:
            f = a.get("form")
            if f and f not in forms:
                forms.append(f)
        self._forms = forms

        # Rebuild form bar
        while self._form_bar_layout.count() > 1:  # keep trailing stretch
            item = self._form_bar_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._form_btns.clear()

        if len(forms) > 1:
            for i, form in enumerate(forms):
                btn = QPushButton(form.upper())
                btn.setStyleSheet(_BTN_ACTIVE if i == 0 else _BTN_INACTIVE)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda _checked, f=form: self._select_form(f))
                self._form_bar_layout.insertWidget(i, btn)
                self._form_btns[form] = btn
            self._form_bar.show()
            self._active_form = forms[0]
        else:
            self._form_bar.hide()
            self._active_form = forms[0] if forms else None

        self._render(self._active_form)

    def _select_form(self, form: str):
        self._active_form = form
        for f, btn in self._form_btns.items():
            btn.setStyleSheet(_BTN_ACTIVE if f == form else _BTN_INACTIVE)
        self._render(form)
        self._scroll.verticalScrollBar().setValue(0)

    def _render(self, active_form: str | None):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._abilities:
            empty = QLabel("No ability data — run Wiki Sync to download.")
            empty.setStyleSheet(f"color: {GRAY_55}; font-size: 11px;")
            self._list_layout.insertWidget(0, empty)
            return

        if self._forms:
            to_show = [a for a in self._abilities if a.get("form") == active_form]
        else:
            to_show = self._abilities

        current_section = None
        idx = 0

        for ability in to_show:
            section = ability.get("section", "General")
            if section != current_section:
                current_section = section
                color = _SECTION_COLORS.get(section, TEXT_GRAY)
                sec_lbl = QLabel(section.upper())
                sec_lbl.setStyleSheet(
                    f"font-size: 10px; font-weight: bold; color: {color};"
                    " letter-spacing: 1px; padding-top: 6px;"
                )
                self._list_layout.insertWidget(idx, sec_lbl)
                idx += 1

            card = _AbilityCard(ability)
            self._list_layout.insertWidget(idx, card)
            idx += 1

    def clear(self):
        self.load([])
