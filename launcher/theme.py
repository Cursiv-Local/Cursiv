"""
Cursiv's look, in one place: colours, fonts and the common widget styles.
Every window imports these instead of defining its own palette, so the app
looks like one thing (and matches the website: dark, quiet, muted gold).

Older code uses the names BG, BG2, BORDER, GOLD, LGOLD, SILVER, SILV2, RED,
GREEN and AMBER; they're kept as aliases of the tokens below.
"""
from __future__ import annotations

# Surfaces
BG       = "#0e1016"     # window background
SURFACE  = "#151821"     # panels, transcript, inputs
SURFACE2 = "#1b1f2a"     # hover, raised items
BORDER   = "#262b38"
BORDER2  = "#343a4a"     # stronger border (focus, hover)

# Text
TEXT  = "#e6e2d8"
MUTED = "#9a9586"
FAINT = "#6c6a62"

# Accent and states
ACCENT       = "#d4b04c"   # primary buttons, highlights
ACCENT_HOVER = "#e2c062"
ACCENT_DOWN  = "#b8963a"
ACCENT_TEXT  = "#17120a"   # text on an accent background
ACCENT_SOFT  = "rgba(212,176,76,0.12)"
LINK  = "#d8d2c4"     # links: light neutral, underlined; no second accent colour
GREEN = "#6fd39b"
AMBER = "#e8b45a"
RED   = "#ff6b6b"

FONT = '"Segoe UI Variable Text", "Segoe UI", Arial, sans-serif'
MONO = '"Cascadia Code", Consolas, monospace'

# Aliases for the names older modules use.
BG2, GOLD, LGOLD, SILVER, SILV2 = SURFACE, ACCENT, "#7a6630", TEXT, FAINT

# Application-wide base style (set once on QApplication in main.py).
APP_QSS = f"""
QWidget {{ background-color: {BG}; color: {TEXT}; font-family: {FONT}; font-size: 14px; }}
QLabel {{ background: transparent; }}
QToolTip {{ background: {SURFACE2}; color: {TEXT}; border: 1px solid {BORDER2}; padding: 5px 8px; border-radius: 6px; }}
QMenu {{ background: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER2}; border-radius: 8px; padding: 4px; }}
QMenu::item {{ padding: 6px 18px; border-radius: 5px; }}
QMenu::item:selected {{ background: {SURFACE2}; color: {TEXT}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER2}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {FAINT}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QLineEdit, QPlainTextEdit, QTextEdit {{ background: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 6px 8px; selection-background-color: {ACCENT_SOFT}; }}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{ border-color: {BORDER2}; }}
QComboBox {{ background: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 8px; padding: 5px 10px; }}
QComboBox:hover {{ border-color: {BORDER2}; }}
QComboBox QAbstractItemView {{ background: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER2};
    selection-background-color: {SURFACE2}; selection-color: {TEXT}; }}
QCheckBox {{ spacing: 8px; }}
"""


def primary_button(radius: int = 8) -> str:
    return (f"QPushButton {{ background: {ACCENT}; color: {ACCENT_TEXT}; border: none; border-radius: {radius}px;"
            f" padding: 6px 14px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {ACCENT_HOVER}; }}"
            f"QPushButton:pressed {{ background: {ACCENT_DOWN}; }}"
            f"QPushButton:disabled {{ background: {SURFACE2}; color: {FAINT}; }}")


def ghost_button(radius: int = 8) -> str:
    return (f"QPushButton {{ background: transparent; color: {TEXT}; border: 1px solid {BORDER}; border-radius: {radius}px;"
            f" padding: 6px 12px; }}"
            f"QPushButton:hover {{ background: {SURFACE2}; border-color: {BORDER2}; }}"
            f"QPushButton:pressed {{ background: {SURFACE}; }}"
            f"QPushButton:disabled {{ color: {FAINT}; }}")


def icon_button(size: int = 32) -> str:
    return (f"QPushButton {{ background: transparent; color: {MUTED}; border: none; border-radius: 6px;"
            f" font-size: 15px; min-width: {size}px; min-height: {size}px; }}"
            f"QPushButton:hover {{ background: {SURFACE2}; color: {TEXT}; }}"
            f"QPushButton:pressed {{ background: {SURFACE}; }}"
            f"QPushButton:disabled {{ color: {FAINT}; }}")
