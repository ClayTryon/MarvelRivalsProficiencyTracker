from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QMenu, QProgressBar
from PyQt6.QtCore import Qt, pyqtSignal, QRect
from PyQt6.QtGui import QMovie, QPixmap, QCursor, QPainter, QColor, QFont
from models.hero import Hero
from gui.hero_detail import _icon_path
from gui.colors import (
    GOLD, GOLD_MAX, DARK, BG_ICON, PROGRESS_BG,
    TEXT_NEAR_WHITE, TEXT_GRAY, TEXT_DIALOG,
)

_PIXMAP_CACHE: dict[str, QPixmap] = {}


def _get_pixmap(path: str, size: int) -> QPixmap:
    key = f"{path}:{size}"
    if key not in _PIXMAP_CACHE:
        _PIXMAP_CACHE[key] = QPixmap(path).scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    return _PIXMAP_CACHE[key]


def _apply_upcoming_overlay(pixmap: QPixmap, date_str: str) -> QPixmap:
    result = QPixmap(pixmap.size())
    result.fill(Qt.GlobalColor.transparent)
    p = QPainter(result)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.drawPixmap(0, 0, pixmap)
    p.fillRect(result.rect(), QColor(0, 0, 0, 155))
    w, h = pixmap.width(), pixmap.height()
    mid = h // 2
    font_up = QFont("Impact", 12)
    font_up.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
    p.setFont(font_up)
    p.setPen(QColor(GOLD))
    p.drawText(QRect(2, mid - 22, w - 4, 22), Qt.AlignmentFlag.AlignCenter, "UPCOMING")
    font_dt = QFont("Arial", 8)
    font_dt.setBold(True)
    p.setFont(font_dt)
    p.setPen(QColor(TEXT_DIALOG))
    p.drawText(QRect(2, mid + 2, w - 4, 20), Qt.AlignmentFlag.AlignCenter, date_str)
    p.end()
    return result


class HeroCard(QFrame):
    clicked                  = pyqtSignal(object)
    edit_requested           = pyqtSignal(object)
    wiki_requested           = pyqtSignal(object)
    clipboard_scan_requested = pyqtSignal(object)

    W = 155
    H = 210
    ICON = 140

    def __init__(self, hero: Hero, release_date: str | None = None, parent=None):
        super().__init__(parent)
        self._hero = hero
        self._movie: QMovie | None = None
        self._release_date = release_date

        self.setFixedSize(self.W, self.H)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._set_border(False)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(5, 5, 5, 8)
        lay.setSpacing(4)

        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(self.ICON, self.ICON)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_lbl.setStyleSheet(f"background: {BG_ICON}; border-radius: 4px;")
        lay.addWidget(self._icon_lbl, alignment=Qt.AlignmentFlag.AlignHCenter)

        name_lbl = QLabel(hero.name)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setWordWrap(True)
        name_lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {TEXT_NEAR_WHITE};")
        lay.addWidget(name_lbl)

        if hero.is_max_level:
            level_text, level_color = "MAX", GOLD_MAX
        else:
            level_text, level_color = f"LV {hero.level}", GOLD
        level_lbl = QLabel(level_text)
        level_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        level_lbl.setStyleSheet(f"font-size: 11px; color: {level_color}; font-weight: bold;")
        lay.addWidget(level_lbl)

        if not hero.is_max_level:
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(hero.progress_pct))
            bar.setFixedHeight(4)
            bar.setTextVisible(False)
            bar.setStyleSheet(
                f"QProgressBar {{ background: {PROGRESS_BG}; border: none; border-radius: 2px; }}"
                f"QProgressBar::chunk {{ background: {GOLD}; border-radius: 2px; }}"
            )
            lay.addWidget(bar)

            xp_lbl = QLabel(f"{hero.xp:,} / {hero.xp_required:,}")
            xp_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            xp_lbl.setStyleSheet(f"font-size: 9px; color: {TEXT_GRAY};")
            lay.addWidget(xp_lbl)

        self._load_icon(hero.name, hero.level, release_date)

    def _set_border(self, hovered: bool):
        border = GOLD if hovered else PROGRESS_BG
        self.setStyleSheet(f"""
            HeroCard {{
                background: {DARK};
                border: 2px solid {border};
                border-radius: 6px;
            }}
        """)

    def _load_icon(self, name: str, level: int, release_date: str | None = None):
        from wiki_sync.ability_scraper import is_future_release
        path = _icon_path(name, level)
        if path is None:
            return
        upcoming = bool(release_date and is_future_release(release_date))
        if level >= 50 and not upcoming:
            movie = QMovie(path)
            movie.setScaledSize(self._icon_lbl.size())
            self._icon_lbl.setMovie(movie)
            movie.start()
            self._movie = movie
        else:
            px = _get_pixmap(path, self.ICON)
            if upcoming:
                px = _apply_upcoming_overlay(px, release_date)
            self._icon_lbl.setPixmap(px)

    def enterEvent(self, event):
        self._set_border(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._set_border(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._hero)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("Edit manually", lambda: self.edit_requested.emit(self._hero))
        menu.addSeparator()
        menu.addAction("Scan from Clipboard", lambda: self.clipboard_scan_requested.emit(self._hero))
        menu.addSeparator()
        menu.addAction("View Wiki", lambda: self.wiki_requested.emit(self._hero))
        menu.exec(event.globalPos())
