APP_STYLESHEET = """
/* ── Base windows ── */
QMainWindow { background: #0c0c14; }
QDialog     { background: #0c0c14; }

/* ── Scroll areas ── */
QScrollArea                      { background: #0c0c14; border: none; }
QScrollArea > QWidget > QWidget  { background: #0c0c14; }
QScrollBar:vertical {
    background: #0c0c14; width: 8px; border: none; margin: 0;
}
QScrollBar::handle:vertical {
    background: #26263a; border-radius: 4px; min-height: 24px;
}
QScrollBar::handle:vertical:hover    { background: #f4d641; }
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical        { height: 0; }

/* ── Buttons ── */
QPushButton {
    background: #16162a; color: #a8a8c0;
    border: 1px solid #26263c; border-radius: 3px;
    padding: 5px 14px; font-size: 12px;
}
QPushButton:hover    { background: #1e1e34; color: #e0e0f0; border-color: #f4d641; }
QPushButton:pressed  { background: #0c0c1c; }
QPushButton:disabled { color: #363650; border-color: #16162a; }

/* ── Combo boxes ── */
QComboBox {
    background: #16162a; color: #a8a8c0;
    border: 1px solid #26263c; border-radius: 3px;
    padding: 4px 8px; min-height: 24px;
}
QComboBox:hover { border-color: #f4d641; }
QComboBox::drop-down  { border: none; width: 20px; }
QComboBox::down-arrow { image: none; }
QComboBox QAbstractItemView {
    background: #16162a; color: #a8a8c0;
    border: 1px solid #26263c;
    selection-background-color: #222240;
    selection-color: #f4d641;
    outline: none;
}

/* ── Labels ── */
QLabel { background: transparent; color: #dcdce8; }

/* ── Text edit (log) ── */
QTextEdit {
    background: #0a0a12; color: #7878a0;
    border: 1px solid #1c1c2c; border-radius: 3px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px; padding: 4px;
}

/* ── Spin boxes ── */
QSpinBox {
    background: #16162a; color: #a8a8c0;
    border: 1px solid #26263c; border-radius: 3px; padding: 4px 8px;
}
QSpinBox:hover { border-color: #f4d641; }
QSpinBox::up-button, QSpinBox::down-button {
    width: 16px; background: #1e1e34; border: none;
}

/* ── Check boxes ── */
QCheckBox             { color: #a8a8c0; background: transparent; }
QCheckBox::indicator  {
    width: 14px; height: 14px;
    background: #16162a; border: 1px solid #26263c; border-radius: 2px;
}
QCheckBox::indicator:checked { background: #f4d641; border-color: #f4d641; }
QCheckBox::indicator:hover   { border-color: #f4d641; }

/* ── Progress bars ── */
QProgressBar {
    background: #16162a; border: 1px solid #26263c;
    border-radius: 3px; text-align: center;
    color: #e0e0e0; font-size: 10px;
}
QProgressBar::chunk { background: #f4d641; border-radius: 2px; }

/* ── Message boxes ── */
QMessageBox         { background: #0c0c14; }
QMessageBox QLabel  { color: #dcdce8; }

/* ── Form row labels ── */
QFormLayout QLabel { color: #606078; }

/* ── Menus ── */
QMenu {
    background: #16162a; color: #a8a8c0;
    border: 1px solid #26263c; padding: 4px 0;
}
QMenu::item { padding: 6px 20px; }
QMenu::item:selected { background: #222240; color: #f4d641; }
QMenu::separator { height: 1px; background: #26263c; margin: 4px 0; }
"""
