import os
import numpy as np
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from PIL import Image, ImageDraw

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel,
    QDialog, QScrollArea, QCheckBox,
)

from storage.database import Database
from storage.repository import SnapshotRepository

_ICONS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'Icons')
)
_icon_cache: dict[str, np.ndarray] = {}

_TIME_OPTIONS = {
    "7 days":  7,
    "14 days": 14,
    "30 days": 30,
    "90 days": 90,
    "All time": None,
}

_DEFAULT_RANGE = "30 days"
_ICON_SIZE = 96

_C_BG       = '#0c0c14'
_C_AX_BG    = '#0a0a12'
_C_TEXT     = '#dcdce8'
_C_SUBTEXT  = '#606078'
_C_SPINE    = '#1a1a2c'
_C_GRID     = '#1a1a2c'

# Background ring colors per tier (RGBA)
_BG_HERO    = (50,  55,  75,  220)
_BG_LORD    = (170, 130, 20,  230)
_BG_CHAMPION = (110, 25, 170, 230)


def _icon_filename(hero_name: str, level: int) -> str:
    safe = hero_name.replace(' ', '_').replace('&', '%26')
    if level >= 50:
        return f"Champion_Icon_{safe}_Animated.webp"
    if level >= 20:
        return f"Lord_Icon_{safe}.webp"
    return f"Hero_Icon_{safe}.webp"


def _bg_color(level: int) -> tuple:
    if level >= 50:
        return _BG_CHAMPION
    if level >= 20:
        return _BG_LORD
    return _BG_HERO


def _make_circular(img: Image.Image, bg: tuple) -> np.ndarray:
    size = _ICON_SIZE
    img = img.resize((size, size), Image.LANCZOS).convert('RGBA')

    # Solid circle background
    result = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(result)
    draw.ellipse([0, 0, size - 1, size - 1], fill=bg)

    # Circular mask for the icon
    mask = Image.new('L', (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    icon_clipped = img.copy()
    icon_clipped.putalpha(mask)

    result.paste(icon_clipped, (0, 0), icon_clipped)
    return np.array(result)


def _tier_key(level: int) -> str:
    if level >= 50:
        return 'champion'
    if level >= 20:
        return 'lord'
    return 'hero'


def _load_icon(hero_name: str, level: int) -> np.ndarray | None:
    cache_key = f"{hero_name}:{_tier_key(level)}"
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]

    filename = _icon_filename(hero_name, level)
    path = os.path.join(_ICONS_DIR, filename)
    if not os.path.exists(path):
        _icon_cache[cache_key] = None
        return None

    try:
        img = Image.open(path)
        # For animated webp, grab the first frame
        img.seek(0)
        img = img.copy()
    except EOFError:
        pass

    arr = _make_circular(img, _bg_color(level))
    _icon_cache[cache_key] = arr
    return arr


class _HeroPickerDialog(QDialog):
    def __init__(self, all_heroes: list[str], hidden: set[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Heroes")
        self.setMinimumWidth(280)
        self.setMinimumHeight(420)

        layout = QVBoxLayout(self)

        btn_row = QHBoxLayout()
        all_btn = QPushButton("All")
        none_btn = QPushButton("None")
        all_btn.clicked.connect(self._select_all)
        none_btn.clicked.connect(self._select_none)
        btn_row.addWidget(all_btn)
        btn_row.addWidget(none_btn)
        layout.addLayout(btn_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        check_layout = QVBoxLayout(container)
        check_layout.setSpacing(2)
        check_layout.setContentsMargins(8, 4, 8, 4)
        scroll.setWidget(container)
        layout.addWidget(scroll)

        self._checkboxes: dict[str, QCheckBox] = {}
        for name in sorted(all_heroes):
            cb = QCheckBox(name)
            cb.setChecked(name not in hidden)
            check_layout.addWidget(cb)
            self._checkboxes[name] = cb
        check_layout.addStretch()

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

    def _select_all(self):
        for cb in self._checkboxes.values():
            cb.setChecked(True)

    def _select_none(self):
        for cb in self._checkboxes.values():
            cb.setChecked(False)

    def hidden_heroes(self) -> set[str]:
        return {name for name, cb in self._checkboxes.items() if not cb.isChecked()}


class XpProgressPage(QWidget):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self._db = db
        self._hidden_heroes: set[str] = set()
        self._all_hero_names: list[str] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 6, 8, 6)
        toolbar.setSpacing(8)

        toolbar.addWidget(QLabel("Time range:"))
        self._range_combo = QComboBox()
        self._range_combo.addItems(_TIME_OPTIONS.keys())
        self._range_combo.setCurrentText(_DEFAULT_RANGE)
        self._range_combo.setFixedWidth(100)
        self._range_combo.currentIndexChanged.connect(self._refresh)
        toolbar.addWidget(self._range_combo)

        self._heroes_btn = QPushButton("Heroes…")
        self._heroes_btn.setFixedWidth(90)
        self._heroes_btn.clicked.connect(self._pick_heroes)
        toolbar.addWidget(self._heroes_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._fig = Figure(figsize=(10, 6), facecolor=_C_BG)
        self._canvas = FigureCanvasQTAgg(self._fig)
        self._canvas.setStyleSheet(f"background: {_C_BG}; border: none;")
        layout.addWidget(self._canvas)

    def refresh(self):
        _icon_cache.clear()
        self._refresh()

    def _pick_heroes(self):
        dlg = _HeroPickerDialog(self._all_hero_names, self._hidden_heroes, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._hidden_heroes = dlg.hidden_heroes()
            self._update_heroes_btn_label()
            self._refresh()

    def _update_heroes_btn_label(self):
        total = len(self._all_hero_names)
        visible = total - len(self._hidden_heroes & set(self._all_hero_names))
        if total == 0 or visible == total:
            self._heroes_btn.setText("Heroes…")
        else:
            self._heroes_btn.setText(f"Heroes ({visible}/{total})")

    def _refresh(self):
        days = _TIME_OPTIONS[self._range_combo.currentText()]
        history = SnapshotRepository(self._db).get_xp_history(days)

        if history:
            new_names = sorted(history.keys())
            if new_names != self._all_hero_names:
                # Drop hidden entries that no longer exist in this time range
                self._hidden_heroes &= set(new_names)
                self._all_hero_names = new_names
                self._update_heroes_btn_label()
            history = {k: v for k, v in history.items() if k not in self._hidden_heroes}

        self._fig.clear()
        self._fig.patch.set_facecolor(_C_BG)
        ax = self._fig.add_subplot(111)
        ax.set_facecolor(_C_AX_BG)

        for spine in ax.spines.values():
            spine.set_edgecolor(_C_SPINE)
        ax.tick_params(colors=_C_SUBTEXT, which='both')
        ax.xaxis.label.set_color(_C_TEXT)
        ax.yaxis.label.set_color(_C_TEXT)
        ax.title.set_color(_C_TEXT)

        if not history:
            if self._hidden_heroes and self._all_hero_names:
                msg = "All heroes are hidden.\nClick \"Heroes…\" to show some."
            else:
                msg = "No scan history yet.\nRun a scan to start tracking XP over time."
            ax.text(
                0.5, 0.5, msg,
                ha='center', va='center', transform=ax.transAxes,
                fontsize=14, color=_C_SUBTEXT,
            )
            ax.set_axis_off()
            self._canvas.draw()
            return

        n = len(history)
        try:
            cmap = matplotlib.colormaps['hsv'].resampled(n + 1)
        except AttributeError:
            import matplotlib.cm as cm
            cmap = cm.get_cmap('hsv', n + 1)

        for i, (hero_name, points) in enumerate(sorted(history.items())):
            dates     = [p[0] for p in points]
            xp_values = [p[1] for p in points]
            last_level = points[-1][2]
            color = cmap(i / max(n - 1, 1))

            ax.plot(dates, xp_values, color=color, linewidth=1.5, zorder=2)

            icon_arr = _load_icon(hero_name, last_level)
            if icon_arr is not None:
                imagebox = OffsetImage(icon_arr, zoom=0.35)
                ab = AnnotationBbox(
                    imagebox,
                    (mdates.date2num(dates[-1]), xp_values[-1]),
                    frameon=False,
                    box_alignment=(0.5, 0.5),
                    zorder=3,
                )
                ax.add_artist(ab)
            else:
                ax.plot(dates[-1:], xp_values[-1:], 'o', color=color, markersize=6, zorder=3)

        unique_dates = sorted({p[0].date() for pts in history.values() for p in pts})
        ax.xaxis.set_major_locator(mticker.FixedLocator([mdates.date2num(d) for d in unique_dates]))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        self._fig.autofmt_xdate()

        ax.set_xlabel("Date")
        ax.set_ylabel("Total XP Earned")
        ax.set_title("Hero XP Progression")
        ax.grid(True, color=_C_GRID, linewidth=0.6, alpha=0.6)

        self._fig.tight_layout()
        self._canvas.draw()
