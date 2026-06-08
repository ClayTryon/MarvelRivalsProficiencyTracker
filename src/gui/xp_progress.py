import os
import sys
import numpy as np
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from PIL import Image, ImageDraw

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel

from storage.repository import SnapshotRepository

if getattr(sys, 'frozen', False):
    _ICONS_DIR = os.path.join(sys._MEIPASS, 'Icons')
else:
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


class HeroXpChart(QWidget):
    """Single-hero XP history chart — embedded in HeroDetailPanel."""

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._hero_name: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        ctrl_row = QHBoxLayout()
        range_lbl = QLabel("RANGE")
        range_lbl.setStyleSheet("color: #484860; font-size: 10px; letter-spacing: 1px;")
        ctrl_row.addWidget(range_lbl)
        self._range_combo = QComboBox()
        self._range_combo.addItems(_TIME_OPTIONS.keys())
        self._range_combo.setCurrentText(_DEFAULT_RANGE)
        self._range_combo.setFixedWidth(100)
        self._range_combo.currentIndexChanged.connect(self._refresh)
        ctrl_row.addWidget(self._range_combo)
        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)

        self._fig = Figure(figsize=(6, 4), facecolor=_C_BG)
        self._canvas = FigureCanvasQTAgg(self._fig)
        self._canvas.setStyleSheet(f"background: {_C_BG}; border: none;")
        layout.addWidget(self._canvas)

    def load(self, hero_name: str):
        self._hero_name = hero_name
        self._refresh()

    def _refresh(self):
        self._fig.clear()
        self._fig.patch.set_facecolor(_C_BG)
        ax = self._fig.add_subplot(111)
        ax.set_facecolor(_C_AX_BG)
        for spine in ax.spines.values():
            spine.set_edgecolor(_C_SPINE)
        ax.tick_params(colors=_C_SUBTEXT, which='both')
        ax.xaxis.label.set_color(_C_TEXT)
        ax.yaxis.label.set_color(_C_TEXT)

        def _no_data(msg: str):
            ax.text(0.5, 0.5, msg, ha='center', va='center',
                    transform=ax.transAxes, fontsize=12, color=_C_SUBTEXT)
            ax.set_axis_off()
            self._canvas.draw()

        if not self._db or not self._hero_name:
            return _no_data("No data available.")

        days = _TIME_OPTIONS[self._range_combo.currentText()]
        history = SnapshotRepository(self._db).get_xp_history(days)
        points = history.get(self._hero_name, [])

        if not points:
            return _no_data("No scan history yet.\nRun a scan to start tracking XP.")

        dates = [p[0] for p in points]
        xp_values = [p[1] for p in points]
        last_level = points[-1][2]

        ax.plot(dates, xp_values, color='#a0c8ff', linewidth=2, zorder=2)
        ax.fill_between(dates, xp_values, alpha=0.12, color='#a0c8ff')

        icon_arr = _load_icon(self._hero_name, last_level)
        if icon_arr is not None:
            imagebox = OffsetImage(icon_arr, zoom=0.38)
            ab = AnnotationBbox(
                imagebox,
                (mdates.date2num(dates[-1]), xp_values[-1]),
                frameon=False, box_alignment=(0.5, 0.5), zorder=3,
            )
            ax.add_artist(ab)
        else:
            ax.plot(dates[-1:], xp_values[-1:], 'o', color='#a0c8ff', markersize=8, zorder=3)

        unique_dates = sorted({p[0].date() for p in points})
        ax.xaxis.set_major_locator(
            mticker.FixedLocator([mdates.date2num(d) for d in unique_dates])
        )
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        self._fig.autofmt_xdate()
        ax.set_xlabel("Date")
        ax.set_ylabel("Total XP Earned")
        ax.grid(True, color=_C_GRID, linewidth=0.6, alpha=0.6)
        self._fig.tight_layout()
        self._canvas.draw()


