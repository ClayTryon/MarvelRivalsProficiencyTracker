import json
import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame,
    QPushButton, QStackedWidget, QScrollArea,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMovie, QPixmap
from models.hero import Hero
from data.xp_table import total_xp_earned, TOTAL_XP_FOR_CHAMPION, TOTAL_XP_FOR_LORD
from gui.abilities_panel import AbilitiesPanel, _AbilityCard
from gui.xp_progress import HeroXpChart
from wiki_sync.ability_scraper import load_abilities

if getattr(sys, 'frozen', False):
    _ICONS_DIR = os.path.join(sys._MEIPASS, 'Icons')
    _DATA_DIR  = os.path.join(sys._MEIPASS, 'hero_data')
else:
    _ICONS_DIR = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "Icons")
    )
    _DATA_DIR = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "hero_data")
    )

_ICON_PIXMAP_CACHE: dict[str, "QPixmap"] = {}

_CARD_BG = "#0d1628"
_DIM     = "#484860"
_GOLD    = "#f4d641"
_TEXT    = "#dcdce8"

_TAB_ACTIVE = (
    "QPushButton { background: #f4d641; color: #1a1a1a; border: none;"
    " border-radius: 3px; font-size: 11px; font-weight: bold;"
    " letter-spacing: 1px; padding: 4px 14px; }"
)
_TAB_INACTIVE = (
    "QPushButton { background: #12121e; color: #666; border: 1px solid #2a2a4a;"
    " border-radius: 3px; font-size: 11px; font-weight: bold;"
    " letter-spacing: 1px; padding: 4px 14px; }"
    " QPushButton:hover { background: #1e1e30; color: #bbb; }"
)


def _icon_path(hero_name: str, level: int) -> str | None:
    slug = hero_name.replace(" ", "_").replace("&", "%26")
    if level >= 50:
        for suffix in ("_Animated.webp", "_Animated.gif"):
            c = os.path.join(_ICONS_DIR, f"Champion_Icon_{slug}{suffix}")
            if os.path.exists(c):
                return c
    elif level >= 20:
        for ext in (".webp", ".png"):
            c = os.path.join(_ICONS_DIR, f"Lord_Icon_{slug}{ext}")
            if os.path.exists(c):
                return c
    else:
        for ext in (".webp", ".png"):
            c = os.path.join(_ICONS_DIR, f"Hero_Icon_{slug}{ext}")
            if os.path.exists(c):
                return c
    return None


def _load_teamups_for_hero(hero_name: str) -> list[dict]:
    teamups_path = os.path.join(_DATA_DIR, "team_ups.json")
    if not os.path.exists(teamups_path):
        return []
    try:
        with open(teamups_path, encoding="utf-8") as f:
            all_teamups = json.load(f)
    except Exception:
        return []
    return [
        tu for tu in all_teamups
        if tu.get("anchor") == hero_name or hero_name in tu.get("partners", [])
    ]


def _load_hero_teamup_abilities(hero_name: str) -> list[dict]:
    slug = hero_name.replace(" ", "_").replace("&", "%26")
    path = os.path.join(_DATA_DIR, f"{slug}.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            abilities = json.load(f)
    except Exception:
        return []
    seen: set[str] = set()
    result = []
    for ab in abilities:
        if ab.get("section") != "Team-Up Abilities":
            continue
        name = ab.get("name", "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        result.append(ab)
    return result


def _find_ability_for_teamup(abilities: list[dict], partner_names: list[str]) -> dict | None:
    if not abilities:
        return None
    for ab in abilities:
        desc = ab.get("description", "")
        for partner in partner_names:
            if partner in desc:
                return ab
    return abilities[0]


def _card(parent=None) -> QWidget:
    w = QWidget(parent)
    w.setStyleSheet(f"QWidget {{ background: {_CARD_BG}; border-radius: 6px; }}")
    return w


def _bar(height: int = 8) -> QProgressBar:
    b = QProgressBar()
    b.setMinimum(0)
    b.setMaximum(100)
    b.setFixedHeight(height)
    b.setTextVisible(False)
    return b


class _TeamUpEntry(QFrame):
    def __init__(self, teamup: dict, hero_name: str, ability: dict | None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background: #0d1628; border: 1px solid #1a2a44; border-radius: 4px; }"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)

        # Team-up name + role/partners row
        name_lbl = QLabel(teamup.get("name", "").upper())
        name_lbl.setStyleSheet(
            "font-family: Impact, 'Arial Narrow', Arial;"
            " font-size: 11px; color: #a0c8ff; letter-spacing: 1px;"
            " background: transparent; border: none;"
        )
        lay.addWidget(name_lbl)

        all_heroes = [teamup.get("anchor", "")] + list(teamup.get("partners", []))
        partners = [h for h in all_heroes if h and h != hero_name]
        role = "Anchor" if teamup.get("anchor") == hero_name else "Partner"
        role_color = _GOLD if role == "Anchor" else _DIM

        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)
        role_lbl = QLabel(role)
        role_lbl.setStyleSheet(
            f"font-size: 10px; color: {role_color}; background: transparent; border: none;"
        )
        meta_row.addWidget(role_lbl)
        if partners:
            with_lbl = QLabel("with  " + "  ·  ".join(partners))
            with_lbl.setStyleSheet(
                f"font-size: 10px; color: {_DIM}; background: transparent; border: none;"
            )
            meta_row.addWidget(with_lbl)
        meta_row.addStretch()
        lay.addLayout(meta_row)

        if ability:
            lay.addWidget(_AbilityCard(ability))


class _HeroTeamUpsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        self._inner = QVBoxLayout(self._content)
        self._inner.setContentsMargins(0, 4, 0, 4)
        self._inner.setSpacing(6)

        scroll.setWidget(self._content)
        layout.addWidget(scroll)

    def load(self, hero_name: str):
        while self._inner.count():
            item = self._inner.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        teamups = _load_teamups_for_hero(hero_name)

        if not teamups:
            lbl = QLabel("No team-up data.\nRun Wiki Sync to download.")
            lbl.setStyleSheet(f"color: {_DIM}; font-size: 12px; background: transparent;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._inner.addWidget(lbl)
        else:
            abilities = _load_hero_teamup_abilities(hero_name)
            for tu in teamups:
                all_heroes = [tu.get("anchor", "")] + list(tu.get("partners", []))
                partners = [h for h in all_heroes if h and h != hero_name]
                ability = _find_ability_for_teamup(abilities, partners)
                self._inner.addWidget(_TeamUpEntry(tu, hero_name, ability))

        self._inner.addStretch()


class HeroDetailPanel(QWidget):
    _ICON_SIZE = 88

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db    = db
        self._movie: QMovie | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(10)

        # ── Header card: icon + name/role/level ───────────────────────────
        header = _card()
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(16, 16, 16, 16)
        h_lay.setSpacing(16)

        self._icon_label = QLabel()
        self._icon_label.setFixedSize(self._ICON_SIZE, self._ICON_SIZE)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setStyleSheet("background: #080f1e; border-radius: 4px;")
        self._icon_label.hide()
        h_lay.addWidget(self._icon_label)

        info = QVBoxLayout()
        info.setSpacing(3)
        info.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._name_label = QLabel()
        self._name_label.setStyleSheet(
            "font-family: Impact, 'Arial Narrow', Arial;"
            f" font-size: 20px; letter-spacing: 2px; color: {_TEXT};"
            " background: transparent;"
        )
        info.addWidget(self._name_label)

        self._role_label = QLabel()
        self._role_label.setStyleSheet(f"font-size: 12px; color: {_DIM}; background: transparent;")
        info.addWidget(self._role_label)

        self._level_label = QLabel()
        self._level_label.setStyleSheet(
            "font-family: Impact, 'Arial Narrow', Arial;"
            f" font-size: 16px; letter-spacing: 1px; color: {_GOLD}; background: transparent;"
        )
        info.addWidget(self._level_label)

        h_lay.addLayout(info, stretch=1)
        root.addWidget(header)

        # ── Tracker stats row ─────────────────────────────────────────────
        self._tracker_row = QWidget()
        self._tracker_row.setStyleSheet(f"QWidget {{ background: {_CARD_BG}; border-radius: 6px; }}")
        tracker_lay = QHBoxLayout(self._tracker_row)
        tracker_lay.setContentsMargins(16, 8, 16, 8)
        tracker_lay.setSpacing(0)

        self._stat_chips: list[tuple[QLabel, QLabel]] = []
        for label_text in ("WIN %", "KDA", "MATCHES", "TIME"):
            if self._stat_chips:
                sep = QLabel("·")
                sep.setStyleSheet(f"color: #26263c; font-size: 14px; padding: 0 10px; background: transparent;")
                tracker_lay.addWidget(sep)
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"font-size: 9px; color: {_DIM}; letter-spacing: 1px; background: transparent;")
            val = QLabel("—")
            val.setStyleSheet(f"font-size: 13px; color: {_TEXT}; font-weight: bold; padding-left: 5px; background: transparent;")
            chip = QHBoxLayout()
            chip.setSpacing(0)
            chip.addWidget(lbl)
            chip.addWidget(val)
            tracker_lay.addLayout(chip)
            self._stat_chips.append((lbl, val))

        tracker_lay.addStretch()
        self._tracker_row.hide()
        root.addWidget(self._tracker_row)

        # ── XP card ───────────────────────────────────────────────────────
        self._xp_card = _card()
        xp_lay = QVBoxLayout(self._xp_card)
        xp_lay.setContentsMargins(16, 12, 16, 12)
        xp_lay.setSpacing(5)

        lvl_row = QHBoxLayout()
        lvl_lbl = QLabel("CURRENT LEVEL")
        lvl_lbl.setStyleSheet(f"font-size: 10px; color: {_DIM}; letter-spacing: 1px; background: transparent;")
        lvl_row.addWidget(lvl_lbl)
        lvl_row.addStretch()
        self._xp_detail_label = QLabel()
        self._xp_detail_label.setStyleSheet(f"font-size: 11px; color: {_DIM}; background: transparent;")
        lvl_row.addWidget(self._xp_detail_label)
        xp_lay.addLayout(lvl_row)

        self._progress_bar = _bar(8)
        xp_lay.addWidget(self._progress_bar)

        self._velocity_label = QLabel()
        self._velocity_label.setStyleSheet(f"font-size: 10px; color: {_DIM}; background: transparent;")
        self._velocity_label.hide()
        xp_lay.addWidget(self._velocity_label)

        self._max_label = QLabel("MAX LEVEL")
        self._max_label.setStyleSheet(
            "font-family: Impact, 'Arial Narrow', Arial;"
            f" font-size: 13px; letter-spacing: 3px; color: {_GOLD}; background: transparent;"
        )
        self._max_label.hide()
        xp_lay.addWidget(self._max_label)

        champ_sep = QFrame()
        champ_sep.setFrameShape(QFrame.Shape.HLine)
        champ_sep.setStyleSheet("color: #1a2a44; background: #1a2a44; max-height: 1px;")
        xp_lay.addWidget(champ_sep)
        self._champ_sep = champ_sep

        champ_row = QHBoxLayout()
        champ_lbl = QLabel("CHAMPION PROGRESS")
        champ_lbl.setStyleSheet(f"font-size: 10px; color: {_DIM}; letter-spacing: 1px; background: transparent;")
        champ_row.addWidget(champ_lbl)
        champ_row.addStretch()
        self._total_xp_label = QLabel()
        self._total_xp_label.setStyleSheet(f"font-size: 11px; color: {_DIM}; background: transparent;")
        champ_row.addWidget(self._total_xp_label)
        xp_lay.addLayout(champ_row)

        self._champion_bar = _bar(4)
        xp_lay.addWidget(self._champion_bar)

        root.addWidget(self._xp_card)

        # ── Tab bar ───────────────────────────────────────────────────────
        tab_bar = QHBoxLayout()
        tab_bar.setSpacing(6)
        tab_bar.setContentsMargins(0, 0, 0, 0)

        self._abilities_tab_btn = QPushButton("ABILITIES")
        self._abilities_tab_btn.setStyleSheet(_TAB_ACTIVE)
        self._abilities_tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._abilities_tab_btn.clicked.connect(lambda: self._switch_tab(0))
        tab_bar.addWidget(self._abilities_tab_btn)

        self._xp_tab_btn = QPushButton("XP HISTORY")
        self._xp_tab_btn.setStyleSheet(_TAB_INACTIVE)
        self._xp_tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._xp_tab_btn.clicked.connect(lambda: self._switch_tab(1))
        tab_bar.addWidget(self._xp_tab_btn)

        self._teamups_tab_btn = QPushButton("TEAM-UPS")
        self._teamups_tab_btn.setStyleSheet(_TAB_INACTIVE)
        self._teamups_tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._teamups_tab_btn.clicked.connect(lambda: self._switch_tab(2))
        tab_bar.addWidget(self._teamups_tab_btn)

        tab_bar.addStretch()
        root.addLayout(tab_bar)

        # ── Tab content ───────────────────────────────────────────────────
        self._stack = QStackedWidget()

        self._abilities_panel = AbilitiesPanel()
        self._stack.addWidget(self._abilities_panel)   # index 0

        self._xp_chart = HeroXpChart(db)
        self._stack.addWidget(self._xp_chart)          # index 1

        self._teamups_widget = _HeroTeamUpsWidget()
        self._stack.addWidget(self._teamups_widget)    # index 2

        root.addWidget(self._stack, stretch=1)

    def _switch_tab(self, index: int):
        self._stack.setCurrentIndex(index)
        btns = [self._abilities_tab_btn, self._xp_tab_btn, self._teamups_tab_btn]
        for i, btn in enumerate(btns):
            btn.setStyleSheet(_TAB_ACTIVE if i == index else _TAB_INACTIVE)

    def set_tracker_stats(self, stats: dict | None):
        if not stats:
            self._tracker_row.hide()
            return

        def _fmt_time(secs) -> str:
            if not secs:
                return "—"
            h, rem = divmod(int(secs), 3600)
            m = rem // 60
            return f"{h}h {m}m" if h else f"{m}m"

        mp   = stats.get("matches") or stats.get("matches_played")
        secs = stats.get("time_played_secs")
        time_str = _fmt_time(secs) if secs else (stats.get("time_played") or "—")
        labels = [
            f"{stats['win_pct']:.1f}%"   if stats.get("win_pct")   is not None else "—",
            f"{stats['kda_ratio']:.2f}"  if stats.get("kda_ratio") is not None else "—",
            str(int(mp)) if mp is not None else "—",
            time_str,
        ]
        for (_, val_lbl), text in zip(self._stat_chips, labels):
            val_lbl.setText(text)
        self._tracker_row.show()

    def set_hero(self, hero: Hero):
        self._load_icon(hero.name, hero.level)
        self._name_label.setText(hero.name.upper())
        self._role_label.setText(hero.role or "Unknown Role")
        self._tracker_row.hide()

        earned = total_xp_earned(hero.level, hero.xp)

        if hero.is_max_level:
            self._level_label.setText("CHAMPION")
            self._xp_detail_label.setText("")
            self._progress_bar.hide()
            self._velocity_label.hide()
            self._max_label.show()
            self._champ_sep.hide()
            self._champion_bar.hide()
            self._total_xp_label.setText(f"{earned:,} XP total")
        else:
            self._level_label.setText(f"LEVEL {hero.level}")
            self._xp_detail_label.setText(f"{hero.xp:,} / {hero.xp_required:,} XP")
            self._progress_bar.setValue(int(hero.progress_pct))
            self._progress_bar.show()
            self._max_label.hide()

            pct = min(100, int(earned / TOTAL_XP_FOR_CHAMPION * 100))
            self._champion_bar.setValue(pct)
            self._total_xp_label.setText(f"{earned:,} / {TOTAL_XP_FOR_CHAMPION:,} XP")
            self._champ_sep.show()
            self._champion_bar.show()

            self._update_velocity(hero.name, hero.level, earned)

        self._abilities_panel.load(load_abilities(hero.name))
        self._xp_chart.load(hero.name)
        self._teamups_widget.load(hero.name)
        self._switch_tab(0)

    def _update_velocity(self, hero_name: str, level: int, earned: int):
        if not self._db:
            self._velocity_label.hide()
            return
        try:
            from storage.repository import SnapshotRepository
            velocity = SnapshotRepository(self._db).get_xp_velocity(hero_name)
            if not velocity:
                self._velocity_label.hide()
                return
            if level < 20:
                xp_needed = TOTAL_XP_FOR_LORD - earned
                target = "Lord"
            else:
                xp_needed = TOTAL_XP_FOR_CHAMPION - earned
                target = "Champion"
            days = max(1, round(xp_needed / velocity))
            self._velocity_label.setText(
                f"~{days}d to {target}  ·  {velocity:,.0f} XP/day avg"
            )
            self._velocity_label.show()
        except Exception:
            self._velocity_label.hide()

    def _load_icon(self, hero_name: str, level: int):
        if self._movie:
            self._movie.stop()
            self._movie = None
        self._icon_label.clear()

        path = _icon_path(hero_name, level)
        if path is None:
            self._icon_label.hide()
            return

        if level >= 50:
            movie = QMovie(path)
            movie.setScaledSize(self._icon_label.size())
            self._icon_label.setMovie(movie)
            movie.start()
            self._movie = movie
        else:
            key = f"{path}:{self._ICON_SIZE}"
            if key not in _ICON_PIXMAP_CACHE:
                _ICON_PIXMAP_CACHE[key] = QPixmap(path).scaled(
                    self._ICON_SIZE, self._ICON_SIZE,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            self._icon_label.setPixmap(_ICON_PIXMAP_CACHE[key])

        self._icon_label.show()
