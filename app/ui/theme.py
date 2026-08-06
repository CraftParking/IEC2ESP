"""Color tokens + Qt theme application, following the same approach as the
ModbusLens app (Fusion style + a full QPalette + a chrome QSS layer on top,
Light/Dark/Follow System, restart-to-apply) rather than a single hand-rolled
dark stylesheet. Flat, thin 1px borders, no rounded corners - that flatness
is deliberate, matching the reference app's look.
"""

import os

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QPalette

APP_ORG = "IEC2ESP"
APP_NAME = "IEC2ESP"
THEME_MODE_KEY = "app/theme_mode"
VALID_MODES = ("light", "dark", "system")

LIGHT = {
    "window_bg": "#F0F0F0",
    "surface": "#FFFFFF",
    "surface_alt": "#F5F5F5",
    "surface_alt2": "#F8F8F8",
    "border": "#CCCCCC",
    "border_light": "#E0E0E0",
    "text": "#000000",
    "text_secondary": "#333333",
    "text_dim": "#444444",
    "text_disabled": "#999999",
    "heading": "#222222",
    "header_bg": "#E9E9E9",
    "hover": "#E0E0E0",
    "hover_strong": "#E8E8E8",
    "pressed": "#D0D0D0",
    "accent": "#007ACC",
    "selection_bg": "#007ACC",
    "selection_text": "#FFFFFF",
    "selection_inactive_bg": "#B3D7FF",
    "selection_inactive_text": "#000000",
    "danger": "#B00020",
    "warning": "#9A6700",
    "success": "#1B7F3B",
    "tooltip_bg": "#FFFFDC",
    "tooltip_text": "#000000",
    "button_hover_border": "#BBBBBB",
    "button_pressed_bg": "#DDDDDD",
    "button_pressed_border": "#AAAAAA",
    "button_disabled_border": "#EEEEEE",
}

DARK = {
    "window_bg": "#1E1E1E",
    "surface": "#252526",
    "surface_alt": "#2D2D30",
    "surface_alt2": "#252526",
    "border": "#3F3F46",
    "border_light": "#3F3F46",
    "text": "#E8E8E8",
    "text_secondary": "#CCCCCC",
    "text_dim": "#B0B0B0",
    "text_disabled": "#6E6E6E",
    "heading": "#E0E0E0",
    "header_bg": "#333337",
    "hover": "#3E3E42",
    "hover_strong": "#3E3E42",
    "pressed": "#094771",
    "accent": "#3A9CDC",
    "selection_bg": "#094771",
    "selection_text": "#FFFFFF",
    "selection_inactive_bg": "#264F78",
    "selection_inactive_text": "#E8E8E8",
    "danger": "#F44336",
    "warning": "#D9A441",
    "success": "#81C784",
    "tooltip_bg": "#3B3B3B",
    "tooltip_text": "#F0F0F0",
    "button_hover_border": "#555555",
    "button_pressed_bg": "#0E639C",
    "button_pressed_border": "#1177BB",
    "button_disabled_border": "#2D2D30",
}

# Ladder canvas colors (app/ui/ladder/canvas.py) - the diagram itself stays a
# light "paper" surface regardless of app theme, matching real ladder software.
CANVAS_BG = "#f5f5f2"
WIRE = "#1a1a1a"
SYMBOL = "#1a1a1a"
TAG_LABEL = "#0d5fd6"
COMMENT_BG = "#fff2b8"
COMMENT_TEXT = "#4a3b00"
TIMER_BLOCK_BG = "#ffffff"
TIMER_BLOCK_BORDER = "#00008c"
SELECTION = "#0d5fd6"


def get_colors(mode: str) -> dict:
    return DARK if mode == "dark" else LIGHT


def load_saved_mode() -> str:
    settings = QSettings(APP_ORG, APP_NAME)
    mode = settings.value(THEME_MODE_KEY, "system", type=str)
    return mode if mode in VALID_MODES else "system"


def save_mode(mode: str) -> None:
    settings = QSettings(APP_ORG, APP_NAME)
    settings.setValue(THEME_MODE_KEY, mode)


def resolve_mode(saved_mode: str, app) -> str:
    """Turn 'system' into a concrete 'light'/'dark' by asking Qt what the OS
    prefers; falls back to 'light' if Qt can't tell."""
    if saved_mode in ("light", "dark"):
        return saved_mode
    try:
        from PySide6.QtCore import Qt

        scheme = app.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return "dark"
    except Exception:
        pass
    return "light"


def apply_theme(app, mode: str) -> None:
    """Fusion style + a full QPalette + a chrome QSS layer for the widgets
    the palette alone doesn't reach (menus, tabs, group boxes, headers)."""
    from PySide6.QtCore import Qt

    c = get_colors(mode)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(c["window_bg"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(c["text"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(c["surface"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(c["surface_alt"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(c["text"]))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(c["selection_text"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(c["window_bg"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(c["text"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(c["selection_bg"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(c["selection_text"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(c["tooltip_bg"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(c["tooltip_text"]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(c["text_disabled"]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(c["text_disabled"]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(c["text_disabled"]))
    app.setPalette(palette)

    # Qt tracks the OS light/dark setting independently of the palette on
    # Windows; without this, native/Fusion-derived sub-controls can still
    # follow the OS scheme even after setPalette() above.
    style_hints = app.styleHints()
    if hasattr(style_hints, "setColorScheme") and hasattr(Qt, "ColorScheme"):
        style_hints.setColorScheme(Qt.ColorScheme.Dark if mode == "dark" else Qt.ColorScheme.Light)

    app.setStyleSheet(f"""
        QMainWindow {{
            background-color: {c["window_bg"]};
        }}

        QMenuBar {{
            background-color: {c["window_bg"]};
            color: {c["text"]};
            border-bottom: 1px solid {c["border"]};
        }}
        QMenuBar::item:selected {{
            background-color: {c["hover"]};
        }}

        QMenu {{
            background-color: {c["surface"]};
            color: {c["text"]};
            border: 1px solid {c["border"]};
        }}
        QMenu::item:selected {{
            background-color: {c["selection_bg"]};
            color: {c["selection_text"]};
        }}

        QStatusBar {{
            background-color: {c["window_bg"]};
            color: {c["text"]};
            border-top: 1px solid {c["border"]};
        }}

        QTreeWidget, QGraphicsView {{
            background-color: {c["surface"]};
            color: {c["text"]};
            border: 1px solid {c["border"]};
            outline: none;
        }}
        QTreeWidget::item {{
            padding: 4px 4px;
        }}
        QTreeWidget::item:selected {{
            background-color: {c["selection_bg"]};
            color: {c["selection_text"]};
        }}
        QTreeWidget::item:hover:!selected {{
            background-color: {c["hover"]};
        }}

        QGroupBox {{
            font-weight: bold;
            color: {c["heading"]};
            border: 1px solid {c["border"]};
            margin-top: 1ex;
            background-color: {c["surface_alt2"]};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 6px;
        }}

        QTableWidget {{
            background-color: {c["surface"]};
            color: {c["text"]};
            border: 1px solid {c["border"]};
            gridline-color: {c["border_light"]};
        }}
        QHeaderView::section {{
            background-color: {c["header_bg"]};
            color: {c["text"]};
            border: 1px solid {c["border"]};
            padding: 5px;
        }}
        QTableWidget::item:selected {{
            background-color: {c["selection_bg"]};
            color: {c["selection_text"]};
        }}

        QListWidget {{
            background-color: {c["surface"]};
            color: {c["text"]};
            border: 1px solid {c["border"]};
        }}
        QListWidget::item:selected {{
            background-color: {c["selection_bg"]};
            color: {c["selection_text"]};
        }}

        QLineEdit, QPlainTextEdit, QSpinBox, QComboBox {{
            background-color: {c["surface"]};
            color: {c["text"]};
            border: 1px solid {c["border"]};
            padding: 4px 6px;
            selection-background-color: {c["selection_bg"]};
        }}
        QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
            border-color: {c["accent"]};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 18px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {c["surface"]};
            border: 1px solid {c["border"]};
            selection-background-color: {c["selection_bg"]};
        }}

        QCheckBox::indicator {{
            width: 14px;
            height: 14px;
            border: 1px solid {c["border"]};
            background-color: {c["surface"]};
        }}
        QCheckBox::indicator:checked {{
            background-color: {c["accent"]};
            border-color: {c["accent"]};
        }}

        QPushButton {{
            background-color: {c["surface_alt"]};
            color: {c["text_secondary"]};
            border: 1px solid {c["border"]};
            padding: 6px 14px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {c["hover_strong"]};
            border-color: {c["button_hover_border"]};
        }}
        QPushButton:pressed {{
            background-color: {c["button_pressed_bg"]};
            border-color: {c["button_pressed_border"]};
        }}
        QPushButton:disabled {{
            background-color: {c["surface_alt2"]};
            color: {c["text_disabled"]};
            border-color: {c["button_disabled_border"]};
        }}
        QPushButton#primary {{
            background-color: {c["accent"]};
            border: 1px solid {c["accent"]};
            color: #ffffff;
            font-weight: 600;
        }}
        QPushButton#primary:hover {{
            background-color: {c["pressed"]};
        }}

        QToolButton {{
            background-color: transparent;
            border: 1px solid transparent;
            padding: 3px 6px;
        }}
        QToolButton:hover {{
            background-color: {c["hover"]};
            border-color: {c["border"]};
        }}

        QSplitter::handle {{
            background-color: {c["border"]};
        }}

        QScrollBar:vertical {{
            background-color: {c["window_bg"]};
            width: 12px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {c["border"]};
            min-height: 24px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {c["accent"]};
        }}
        QScrollBar:horizontal {{
            background-color: {c["window_bg"]};
            height: 12px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {c["border"]};
            min-width: 24px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: {c["accent"]};
        }}
        QScrollBar::add-line, QScrollBar::sub-line {{
            height: 0;
            width: 0;
        }}

        QToolTip {{
            background-color: {c["tooltip_bg"]};
            color: {c["tooltip_text"]};
            border: 1px solid {c["border"]};
        }}
    """)


# Flat hex fallbacks for code that colors things (e.g. validation issue rows)
# without threading the resolved theme mode through - readable on both themes.
ERROR = "#D64545"
WARNING = "#C98A2B"
SUCCESS = "#3FA35B"
