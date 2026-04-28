import os
import sys
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMovie, QPixmap
from models.hero import Hero
from data.xp_table import total_xp_earned, TOTAL_XP_FOR_CHAMPION

if getattr(sys, 'frozen', False):
    _ICONS_DIR = os.path.join(sys._MEIPASS, 'Icons')
else:
    _ICONS_DIR = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "Icons")
    )


def _icon_path(hero_name: str, level: int) -> str | None:
    slug = hero_name.replace(" ", "_").replace("&", "%26")
    if level >= 50:
        candidate = os.path.join(_ICONS_DIR, f"Champion_Icon_{slug}_Animated.webp")
    elif level >= 20:
        candidate = os.path.join(_ICONS_DIR, f"Lord_Icon_{slug}.webp")
    else:
        candidate = os.path.join(_ICONS_DIR, f"Hero_Icon_{slug}.webp")
    return candidate if os.path.exists(candidate) else None


class HeroDetailPanel(QWidget):
    _ICON_SIZE = 128

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 20, 20, 20)

        self._icon_label = QLabel()
        self._icon_label.setFixedSize(self._ICON_SIZE, self._ICON_SIZE)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._icon_label.hide()
        self._movie: QMovie | None = None

        self._name_label = QLabel()
        self._name_label.setStyleSheet("font-size: 22px; font-weight: bold;")

        self._role_label = QLabel()
        self._role_label.setStyleSheet("font-size: 14px; color: #888;")

        self._level_label = QLabel()
        self._level_label.setStyleSheet("font-size: 14px;")

        self._xp_label = QLabel()
        self._xp_label.setStyleSheet("font-size: 13px;")

        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setStyleSheet(
            "QProgressBar { color: black; }"
            "QProgressBar::chunk { background-color: #f4d641; }"
        )

        self._max_label = QLabel("MAX LEVEL")
        self._max_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #FFD700;"
        )
        self._max_label.hide()

        self._total_xp_label = QLabel()
        self._total_xp_label.setStyleSheet("font-size: 13px; color: #aaa;")

        self._champion_label = QLabel("Progress to Champion (LV50)")
        self._champion_label.setStyleSheet("font-size: 12px; color: #aaa;")

        self._champion_bar = QProgressBar()
        self._champion_bar.setMinimum(0)
        self._champion_bar.setMaximum(100)
        self._champion_bar.setTextVisible(True)
        self._champion_bar.setStyleSheet(
            "QProgressBar { color: black; }"
            "QProgressBar::chunk { background-color: #f4d641; }"
        )

        for w in (self._icon_label, self._name_label, self._role_label,
                  self._level_label, self._xp_label, self._progress_bar,
                  self._max_label, self._total_xp_label,
                  self._champion_label, self._champion_bar):
            layout.addWidget(w)

    def set_hero(self, hero: Hero):
        self._load_icon(hero.name, hero.level)

        self._name_label.setText(hero.name)
        self._role_label.setText(hero.role or "Unknown Role")
        self._level_label.setText(f"Level {hero.level}")

        if hero.is_max_level:
            self._xp_label.setText("XP: MAX")
            self._progress_bar.hide()
            self._max_label.show()
        else:
            self._xp_label.setText(f"{hero.xp:,} / {hero.xp_required:,} XP")
            self._progress_bar.setValue(int(hero.progress_pct))
            self._progress_bar.show()
            self._max_label.hide()

        earned = total_xp_earned(hero.level, hero.xp)
        self._total_xp_label.setText(f"Total XP: {earned:,}")

        if hero.level >= 50:
            self._champion_label.hide()
            self._champion_bar.hide()
        else:
            pct = min(100, int(earned / TOTAL_XP_FOR_CHAMPION * 100))
            self._champion_bar.setValue(pct)
            self._champion_label.show()
            self._champion_bar.show()

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
            pixmap = QPixmap(path).scaled(
                self._ICON_SIZE, self._ICON_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._icon_label.setPixmap(pixmap)

        self._icon_label.show()

    def clear(self):
        if self._movie:
            self._movie.stop()
            self._movie = None
        self._icon_label.clear()
        self._icon_label.hide()
        for label in (self._name_label, self._role_label, self._level_label,
                      self._xp_label, self._total_xp_label, self._champion_label):
            label.setText("")
        self._progress_bar.setValue(0)
        self._champion_bar.setValue(0)
        self._max_label.hide()
        self._progress_bar.show()
        self._champion_bar.show()
