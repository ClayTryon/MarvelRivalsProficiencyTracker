from gui.colors import (
    BG_APP, BG_SINK, BG_CONTROL, BG_HOVER, BG_PRESSED, BG_SELECT,
    BORDER, BORDER_SINK, SCROLL_HANDLE,
    TEXT, TEXT_UI, TEXT_BRIGHT, TEXT_DIALOG, TEXT_MUTED, TEXT_FAINT, TEXT_SUB,
    TEXT_NAV_HOVER,
    GOLD, COMBO_ARROW,
)

APP_STYLESHEET = f"""
/* ── Base windows ── */
QMainWindow {{ background: {BG_APP}; }}
QDialog     {{ background: {BG_APP}; }}

/* ── Scroll areas ── */
QScrollArea                      {{ background: {BG_APP}; border: none; }}
QScrollArea > QWidget > QWidget  {{ background: {BG_APP}; }}
QScrollBar:vertical {{
    background: {BG_APP}; width: 8px; border: none; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {SCROLL_HANDLE}; border-radius: 4px; min-height: 24px;
}}
QScrollBar::handle:vertical:hover    {{ background: {GOLD}; }}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical        {{ height: 0; }}

/* ── Buttons ── */
QPushButton {{
    background: {BG_CONTROL}; color: {TEXT_UI};
    border: 1px solid {BORDER}; border-radius: 3px;
    padding: 5px 14px; font-size: 12px;
}}
QPushButton:hover    {{ background: {BG_HOVER}; color: {TEXT_BRIGHT}; border-color: {GOLD}; }}
QPushButton:pressed  {{ background: {BG_PRESSED}; }}
QPushButton:disabled {{ color: {TEXT_FAINT}; border-color: {BG_CONTROL}; }}

/* ── Combo boxes ── */
QComboBox {{
    background: {BG_CONTROL}; color: {TEXT_UI};
    border: 1px solid {BORDER}; border-radius: 3px;
    padding: 4px 28px 4px 8px; min-height: 24px;
}}
QComboBox:hover {{ border-color: {GOLD}; }}
QComboBox::drop-down  {{ border: none; width: 24px; }}
QComboBox::down-arrow {{
    width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {COMBO_ARROW};
}}
QComboBox::down-arrow:hover,
QComboBox::down-arrow:on {{ border-top-color: {GOLD}; }}
QComboBox QAbstractItemView {{
    background: {BG_CONTROL}; color: {TEXT_UI};
    border: 1px solid {BORDER};
    selection-background-color: {BG_SELECT};
    selection-color: {GOLD};
    outline: none;
}}

/* ── Line edits ── */
QLineEdit {{
    background: {BG_CONTROL}; color: {TEXT_UI};
    border: 1px solid {BORDER}; border-radius: 3px;
    padding: 4px 8px; min-height: 24px;
}}
QLineEdit:hover {{ border-color: {TEXT_NAV_HOVER}; }}
QLineEdit:focus {{ border-color: {GOLD}; }}

/* ── Labels ── */
QLabel {{ background: transparent; color: {TEXT}; }}

/* ── Text edit (log) ── */
QTextEdit {{
    background: {BG_SINK}; color: {TEXT_MUTED};
    border: 1px solid {BORDER_SINK}; border-radius: 3px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px; padding: 4px;
}}

/* ── Spin boxes ── */
QSpinBox {{
    background: {BG_CONTROL}; color: {TEXT_UI};
    border: 1px solid {BORDER}; border-radius: 3px; padding: 4px 8px;
}}
QSpinBox:hover {{ border-color: {GOLD}; }}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 16px; background: {BG_HOVER}; border: none;
}}

/* ── Check boxes ── */
QCheckBox             {{ color: {TEXT_UI}; background: transparent; }}
QCheckBox::indicator  {{
    width: 14px; height: 14px;
    background: {BG_CONTROL}; border: 1px solid {BORDER}; border-radius: 2px;
}}
QCheckBox::indicator:checked {{ background: {GOLD}; border-color: {GOLD}; }}
QCheckBox::indicator:hover   {{ border-color: {GOLD}; }}

/* ── Progress bars ── */
QProgressBar {{
    background: {BG_CONTROL}; border: 1px solid {BORDER};
    border-radius: 3px; text-align: center;
    color: {TEXT_DIALOG}; font-size: 10px;
}}
QProgressBar::chunk {{ background: {GOLD}; border-radius: 2px; }}

/* ── Message boxes ── */
QMessageBox         {{ background: {BG_APP}; }}
QMessageBox QLabel  {{ color: {TEXT}; }}

/* ── Form row labels ── */
QFormLayout QLabel {{ color: {TEXT_SUB}; }}

/* ── Menus ── */
QMenu {{
    background: {BG_CONTROL}; color: {TEXT_UI};
    border: 1px solid {BORDER}; padding: 4px 0;
}}
QMenu::item {{ padding: 6px 20px; }}
QMenu::item:selected {{ background: {BG_SELECT}; color: {GOLD}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 0; }}
"""
