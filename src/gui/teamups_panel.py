import json
import os
import sys
from glob import glob

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap

if getattr(sys, 'frozen', False):
    _DATA_DIR = os.path.join(sys._MEIPASS, 'hero_data')
    _ICONS_DIR = os.path.join(sys._MEIPASS, 'Icons')
else:
    _DATA_DIR = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "hero_data")
    )
    _ICONS_DIR = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "Icons")
    )

_PORTRAIT = 52


def _hero_icon_path(hero_name: str) -> str | None:
    slug = hero_name.replace(" ", "_").replace("&", "%26")
    for ext in (".webp", ".png"):
        p = os.path.join(_ICONS_DIR, f"Hero_Icon_{slug}{ext}")
        if os.path.exists(p):
            return p
    return None


def _collect_teamups() -> list[dict]:
    """
    Build team-up entries from hero_data/team_ups.json (written by wiki sync)
    and individual hero ability JSONs.

    Returns sorted list of {"name", "anchor": entry, "partners": [entry, ...]},
    where each entry has {"hero", "ability_name", "key", "description", "stats"}.
    """
    teamups_path = os.path.join(_DATA_DIR, "team_ups.json")
    if not os.path.exists(teamups_path):
        return []
    try:
        with open(teamups_path, encoding="utf-8") as f:
            pairings = json.load(f)
    except Exception:
        return []

    # Hero name → list of team-up ability entries
    hero_tu: dict[str, list[dict]] = {}
    for json_path in sorted(glob(os.path.join(_DATA_DIR, "*.json"))):
        if os.path.basename(json_path) == "team_ups.json":
            continue
        slug = os.path.basename(json_path)[:-5]
        hero_name = slug.replace("_", " ").replace("%26", "&")
        try:
            with open(json_path, encoding="utf-8") as f:
                abilities = json.load(f)
        except Exception:
            continue
        seen: set[str] = set()
        for ability in abilities:
            if ability.get("section") != "Team-Up Abilities":
                continue
            aname = ability.get("name", "").strip()
            if not aname or aname in seen:
                continue
            seen.add(aname)
            hero_tu.setdefault(hero_name, []).append({
                "hero": hero_name,
                "ability_name": aname,
                "key": ability.get("key", ""),
                "description": ability.get("description", ""),
                "stats": ability.get("stats", {}),
            })

    def _entry(hero: str, all_heroes: list[str]) -> dict:
        """Pick the most contextually relevant team-up ability for this hero."""
        abilities = hero_tu.get(hero, [])
        if not abilities:
            return {"hero": hero, "ability_name": "", "key": "", "description": "", "stats": {}}
        others = [h for h in all_heroes if h != hero]
        for ab in abilities:
            for other in others:
                if other in ab["description"]:
                    return ab
        return abilities[0]

    result = []
    for pairing in pairings:
        anchor = pairing["anchor"]
        partners = pairing["partners"]
        all_heroes = [anchor] + partners
        result.append({
            "name": pairing["name"],
            "anchor": _entry(anchor, all_heroes),
            "partners": [_entry(p, all_heroes) for p in partners],
        })

    return sorted(result, key=lambda t: t["name"])


# ---------------------------------------------------------------------------
# Portrait button
# ---------------------------------------------------------------------------

class _PortraitBtn(QWidget):
    """Clickable hero portrait with an optional gold anchor pip."""

    clicked = pyqtSignal()

    _ANCHOR_COLOR   = "#f4d641"
    _SELECTED_COLOR = "#a0c8ff"
    _DEFAULT_BG     = "#0d1628"

    def __init__(self, hero_name: str, is_anchor: bool = False, parent=None):
        super().__init__(parent)
        self._is_anchor = is_anchor
        self._active = is_anchor
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(_PORTRAIT + 20)

        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(3)
        col.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(_PORTRAIT, _PORTRAIT)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._refresh_border()

        path = _hero_icon_path(hero_name)
        if path:
            px = QPixmap(path).scaled(
                _PORTRAIT - 4, _PORTRAIT - 4,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._icon_lbl.setPixmap(px)

        self._pip = QLabel()
        self._pip.setFixedSize(_PORTRAIT, 5)
        self._pip.setStyleSheet(
            f"background: {self._ANCHOR_COLOR}; border-radius: 2px;"
            if is_anchor else "background: transparent;"
        )

        name_lbl = QLabel(hero_name)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        name_lbl.setWordWrap(True)
        name_lbl.setFixedWidth(_PORTRAIT + 16)
        name_lbl.setStyleSheet("font-size: 8px; color: #556;")

        col.addWidget(self._icon_lbl)
        col.addWidget(self._pip)
        col.addWidget(name_lbl)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def _refresh_border(self):
        if self._is_anchor and self._active:
            color = self._ANCHOR_COLOR
        elif not self._is_anchor and self._active:
            color = self._SELECTED_COLOR
        else:
            color = "#1e2a42"
        self._icon_lbl.setStyleSheet(
            f"background: {self._DEFAULT_BG}; border: 2px solid {color}; border-radius: 4px;"
        )

    def set_active(self, active: bool):
        self._active = active
        self._refresh_border()


# ---------------------------------------------------------------------------
# Team-up card
# ---------------------------------------------------------------------------

class _TeamUpCard(QFrame):
    def __init__(self, teamup: dict, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background: #0d1628; border: 1px solid #1a2a44;"
            " border-radius: 6px; }"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top section: name left, portraits right ───────────────────────
        top = QWidget()
        top.setStyleSheet("background: transparent;")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(16, 14, 16, 10)
        top_layout.setSpacing(16)

        # Left: team-up name
        name_lbl = QLabel(teamup["name"].upper())
        name_lbl.setStyleSheet(
            "font-family: Impact, 'Arial Narrow', Arial;"
            " font-size: 16px; letter-spacing: 2px; color: #a0c8ff;"
        )
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        top_layout.addWidget(name_lbl, stretch=1)

        # Right: portraits — anchor always leftmost, partners follow
        portraits = QHBoxLayout()
        portraits.setSpacing(8)
        portraits.setContentsMargins(0, 0, 0, 0)

        anchor_entry = teamup["anchor"]
        self._anchor_btn = _PortraitBtn(anchor_entry["hero"], is_anchor=True)
        self._anchor_btn.clicked.connect(self._select_anchor)
        portraits.addWidget(self._anchor_btn)  # leftmost

        self._partner_btns: list[tuple[_PortraitBtn, dict]] = []
        for entry in teamup["partners"]:
            btn = _PortraitBtn(entry["hero"], is_anchor=False)
            btn.set_active(False)
            btn.clicked.connect(lambda _=False, e=entry, b=btn: self._select_partner(e, b))
            portraits.addWidget(btn)
            self._partner_btns.append((btn, entry))

        top_layout.addLayout(portraits)
        root.addWidget(top)

        # ── Bottom section: description bar ──────────────────────────────
        bottom = QWidget()
        bottom.setStyleSheet("background: #080f1e; border-radius: 0 0 6px 6px;")
        bot_layout = QVBoxLayout(bottom)
        bot_layout.setContentsMargins(16, 8, 16, 10)
        bot_layout.setSpacing(3)

        self._ability_name_lbl = QLabel()
        self._ability_name_lbl.setStyleSheet("font-size: 10px; color: #4a5a78; letter-spacing: 1px;")
        bot_layout.addWidget(self._ability_name_lbl)

        self._desc_lbl = QLabel()
        self._desc_lbl.setWordWrap(True)
        self._desc_lbl.setStyleSheet("font-size: 11px; color: #8a9ab8;")
        bot_layout.addWidget(self._desc_lbl)

        self._stats_lbl = QLabel()
        self._stats_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._stats_lbl.setWordWrap(True)
        self._stats_lbl.setStyleSheet("font-size: 10px; color: #556;")
        bot_layout.addWidget(self._stats_lbl)

        root.addWidget(bottom)

        self._anchor_entry = anchor_entry
        self._select_anchor()

    def _display(self, entry: dict):
        aname = entry.get("ability_name", "")
        self._ability_name_lbl.setText(aname.upper() if aname else "")
        self._ability_name_lbl.setVisible(bool(aname))
        self._desc_lbl.setText(entry.get("description", ""))
        stats = entry.get("stats", {})
        self._stats_lbl.setText(
            "   ".join(f"<b style='color:#667'>{k}:</b> {v}" for k, v in stats.items())
        )
        self._stats_lbl.setVisible(bool(stats))

    def _select_anchor(self):
        self._anchor_btn.set_active(True)
        for btn, _ in self._partner_btns:
            btn.set_active(False)
        self._display(self._anchor_entry)

    def _select_partner(self, entry: dict, active_btn: _PortraitBtn):
        self._anchor_btn.set_active(False)
        for btn, _ in self._partner_btns:
            btn.set_active(btn is active_btn)
        self._display(entry)


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------

class TeamUpsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(12)

        title = QLabel("TEAM-UP ABILITIES")
        title.setStyleSheet(
            "font-family: Impact, 'Arial Narrow', Arial;"
            " font-size: 20px; letter-spacing: 4px; color: #a0c8ff;"
        )
        outer.addWidget(title)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("background: transparent;")
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._content)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(8)
        self._list_layout.addStretch()

        self._scroll.setWidget(self._content)
        outer.addWidget(self._scroll)

        self.load()

    def load(self):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        teamups = _collect_teamups()
        if not teamups:
            empty = QLabel("No team-up data — run Wiki Sync to download.")
            empty.setStyleSheet("color: #555; font-size: 12px;")
            self._list_layout.insertWidget(0, empty)
            return

        for i, teamup in enumerate(teamups):
            self._list_layout.insertWidget(i, _TeamUpCard(teamup))
