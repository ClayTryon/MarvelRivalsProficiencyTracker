from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QMenu, QProgressBar
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMovie, QPixmap, QCursor
from models.hero import Hero
from gui.hero_detail import _ICONS_DIR, _icon_path


class HeroCard(QFrame):
    clicked                  = pyqtSignal(object)
    edit_requested           = pyqtSignal(object)
    wiki_requested           = pyqtSignal(object)
    clipboard_scan_requested = pyqtSignal(object)

    W = 155
    H = 210
    ICON = 140

    def __init__(self, hero: Hero, parent=None):
        super().__init__(parent)
        self._hero = hero
        self._movie: QMovie | None = None

        self.setFixedSize(self.W, self.H)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._set_border(False)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(5, 5, 5, 8)
        lay.setSpacing(4)

        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(self.ICON, self.ICON)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_lbl.setStyleSheet("background: #141414; border-radius: 4px;")
        lay.addWidget(self._icon_lbl, alignment=Qt.AlignmentFlag.AlignHCenter)

        name_lbl = QLabel(hero.name)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setWordWrap(True)
        name_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #e8e8e8;")
        lay.addWidget(name_lbl)

        if hero.is_max_level:
            level_text, level_color = "MAX", "#FFD700"
        else:
            level_text, level_color = f"LV {hero.level}", "#f4d641"
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
                "QProgressBar { background: #2a2a2a; border: none; border-radius: 2px; }"
                "QProgressBar::chunk { background: #f4d641; border-radius: 2px; }"
            )
            lay.addWidget(bar)

            xp_lbl = QLabel(f"{hero.xp:,} / {hero.xp_required:,}")
            xp_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            xp_lbl.setStyleSheet("font-size: 9px; color: #888888;")
            lay.addWidget(xp_lbl)

        self._load_icon(hero.name, hero.level)

    def _set_border(self, hovered: bool):
        border = "#f4d641" if hovered else "#2a2a2a"
        self.setStyleSheet(f"""
            HeroCard {{
                background: #1a1a1a;
                border: 2px solid {border};
                border-radius: 6px;
            }}
        """)

    def _load_icon(self, name: str, level: int):
        path = _icon_path(name, level)
        if path is None:
            return
        if level >= 50:
            movie = QMovie(path)
            movie.setScaledSize(self._icon_lbl.size())
            self._icon_lbl.setMovie(movie)
            movie.start()
            self._movie = movie
        else:
            px = QPixmap(path).scaled(
                self.ICON, self.ICON,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
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
