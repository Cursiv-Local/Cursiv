"""
Cursiv's look, in one place: colours, fonts and the common widget styles.
Every window imports these instead of defining its own palette, so the app
looks like one thing (and matches the website: quiet, with one muted-gold accent).

Light or dark: Settings → Appearance saves "light", "dark" or "" (match
Windows). The mode is chosen once, when Cursiv starts, so a change applies
the next time it opens. In light mode, install() also translates the few
dark colours older windows still write directly into their styles
(_LIGHT_REMAP), so every window follows the mode.

Older code uses the names BG, BG2, BORDER, GOLD, LGOLD, SILVER, SILV2, RED,
GREEN and AMBER; they're kept as aliases of the tokens below.
"""
from __future__ import annotations

import re as _re

FONT = '"Segoe UI Variable Text", "Segoe UI", Arial, sans-serif'
MONO = '"Cascadia Code", Consolas, monospace'

DARK = dict(
    BG="#0e1016", SURFACE="#151821", SURFACE2="#1b1f2a", BORDER="#262b38", BORDER2="#343a4a",
    TEXT="#e6e2d8", MUTED="#9a9586", FAINT="#6c6a62",
    ACCENT="#d4b04c", ACCENT_HOVER="#e2c062", ACCENT_DOWN="#b8963a", ACCENT_TEXT="#17120a",
    ACCENT_SOFT="rgba(212,176,76,0.12)", LINK="#d8d2c4", GREEN="#6fd39b", AMBER="#e8b45a", RED="#ff6b6b",
    LGOLD="#7a6630",
)
# Warm off-white, charcoal text, a deeper gold that stays readable on light.
LIGHT = dict(
    BG="#f7f5f0", SURFACE="#ffffff", SURFACE2="#efebe3", BORDER="#e2ddd2", BORDER2="#cfc8ba",
    TEXT="#26231e", MUTED="#6b655a", FAINT="#8f887b",
    ACCENT="#9a7417", ACCENT_HOVER="#ad8420", ACCENT_DOWN="#7f5f12", ACCENT_TEXT="#fffdf7",
    ACCENT_SOFT="rgba(154,116,23,0.10)", LINK="#4a4438", GREEN="#2f8a57", AMBER="#9a6a12", RED="#c0392b",
    LGOLD="#c9b37a",
)

# Dark colours written directly in older windows' styles, and their light versions.
_LIGHT_REMAP = {
    "#0e1016": "#f7f5f0", "#0b0b12": "#f7f5f0", "#151821": "#ffffff", "#13131e": "#ffffff",
    "#1b1f2a": "#efebe3", "#1a1a2e": "#efebe3", "#1e1e2e": "#efebe3", "#1a1b28": "#efebe3", "#1a1a3a": "#efebe3",
    "#262b38": "#e2ddd2", "#2a2a3f": "#e2ddd2", "#0a0a1a": "#e2ddd2", "#343a4a": "#cfc8ba", "#444466": "#cfc8ba",
    "#e6e2d8": "#26231e", "#f0e9d8": "#26231e", "#c8c8d4": "#26231e", "#d8d2c4": "#4a4438",
    "#9a9586": "#6b655a", "#6c6a62": "#8f887b", "#666680": "#8f887b",
    "#d4b04c": "#9a7417", "#e2c062": "#ad8420", "#b8963a": "#7f5f12", "#17120a": "#fffdf7", "#7a6630": "#c9b37a",
    "#ffd700": "#9a7417", "#9b7b20": "#c9b37a",
    "#6fd39b": "#2f8a57", "#44cc66": "#2f8a57", "#3ecf6e": "#2f8a57", "#44cc88": "#2f8a57",
    "#e8b45a": "#9a6a12", "#e8a020": "#9a6a12",
    "#ff6b6b": "#c0392b", "#ff6666": "#c0392b", "#ff4455": "#c0392b", "#3a1010": "#fbe4e1", "#6a2020": "#e8b5ad",
    "#1a1200": "#fbf3e0", "#5a3a00": "#e8d3a0", "#7a4d00": "#c79a3a", "#b07000": "#9a6a12", "#a06500": "#9a6a12",
    "#ffe0a0": "#7a5200",
    "#777": "#8f887b", "#666": "#8f887b", "#999": "#6b655a", "#444": "#cfc8ba",
}
_HEX = _re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")


def saved_mode() -> str:
    """"light", "dark", or "" (match Windows)."""
    try:
        from cursiv_v215.chat import keys
        mode = keys.saved_key("ui_theme")
        return mode if mode in ("light", "dark") else ""
    except Exception:
        return ""


def set_mode(mode: str) -> None:
    from cursiv_v215.chat import keys
    keys.store_key("ui_theme", mode if mode in ("light", "dark") else "")


def windows_prefers_light() -> bool:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return bool(winreg.QueryValueEx(k, "AppsUseLightTheme")[0])
    except Exception:
        return False


def resolve_mode() -> str:
    mode = saved_mode()
    return mode or ("light" if windows_prefers_light() else "dark")


MODE = resolve_mode()
_P = LIGHT if MODE == "light" else DARK
BG, SURFACE, SURFACE2, BORDER, BORDER2 = _P["BG"], _P["SURFACE"], _P["SURFACE2"], _P["BORDER"], _P["BORDER2"]
TEXT, MUTED, FAINT = _P["TEXT"], _P["MUTED"], _P["FAINT"]
ACCENT, ACCENT_HOVER, ACCENT_DOWN, ACCENT_TEXT = _P["ACCENT"], _P["ACCENT_HOVER"], _P["ACCENT_DOWN"], _P["ACCENT_TEXT"]
ACCENT_SOFT, LINK, GREEN, AMBER, RED = _P["ACCENT_SOFT"], _P["LINK"], _P["GREEN"], _P["AMBER"], _P["RED"]

# Aliases for the names older modules use.
BG2, GOLD, LGOLD, SILVER, SILV2 = SURFACE, ACCENT, _P["LGOLD"], TEXT, FAINT


def light_qss(qss: str) -> str:
    """A style written with dark colours, translated to the light palette."""
    return translate(qss, "dark", "light")


# ── Switching while Cursiv is open ───────────────────────────────────────────
# Module constants (BG, ACCENT, …) keep the palette Cursiv started with (START).
# Every style a window sets, and rich text in labels, passes through live(), which
# translates START colours to the CURRENT mode. switch_live() re-translates what's
# already on screen, so a change in Settings shows at once.

START = MODE
CURRENT = MODE

_D2L = {DARK[k].lower(): LIGHT[k] for k in DARK if str(DARK[k]).startswith("#")}
_D2L.update(_LIGHT_REMAP)
_L2D = {LIGHT[k].lower(): DARK[k] for k in LIGHT if str(LIGHT[k]).startswith("#")}
for _d, _l in _LIGHT_REMAP.items():
    _L2D.setdefault(_l.lower(), _d)
_RGBA = {("dark", "light"): {DARK["ACCENT_SOFT"]: LIGHT["ACCENT_SOFT"], "rgba(111,211,155,0.10)": "rgba(47,138,87,0.10)",
                             "rgba(232,180,90,0.10)": "rgba(154,106,18,0.10)"}}
_RGBA[("light", "dark")] = {v: k for k, v in _RGBA[("dark", "light")].items()}


def translate(text: str, src: str, dst: str) -> str:
    """Colours written for the src palette, rewritten for dst."""
    if not text or src == dst:
        return text
    table = _D2L if (src, dst) == ("dark", "light") else _L2D
    out = _HEX.sub(lambda m: table.get(m.group(0).lower(), m.group(0)), text)
    for a, b in _RGBA[(src, dst)].items():
        out = out.replace(a, b)
    return out


def to_current(html: str) -> str:
    """HTML saved in either mode (an older conversation), in the current mode."""
    return translate(html, "dark" if CURRENT == "light" else "light", CURRENT)


def live(text: str) -> str:
    """A style or HTML written with the palette Cursiv started with, in the current mode."""
    return translate(text, START, CURRENT)


_installed = False
_ORIG = {}


def install() -> None:
    """Call once at start-up: every setStyleSheet, and rich text set on a label,
    goes through live(), so all windows follow the current mode."""
    global _installed
    if _installed:
        return
    from PyQt6.QtWidgets import QLabel, QWidget
    _ORIG["style"] = QWidget.setStyleSheet
    _ORIG["text"] = QLabel.setText

    def themed_style(self, qss):
        return _ORIG["style"](self, live(qss or ""))

    def themed_text(self, text):
        return _ORIG["text"](self, live(text) if text and "#" in text and "<" in text else text)
    QWidget.setStyleSheet = themed_style
    QLabel.setText = themed_text
    _installed = True


def switch_live(mode_setting: str) -> str:
    """Save the choice ("light", "dark" or "" for Windows) and recolour everything open.
    Returns the mode now showing."""
    global CURRENT
    set_mode(mode_setting)
    new = mode_setting or ("light" if windows_prefers_light() else "dark")
    old = CURRENT
    if new == old:
        return new
    CURRENT = new
    from PyQt6.QtWidgets import QApplication, QLabel, QTextBrowser
    app = QApplication.instance()
    if app is None:
        return new
    set_style = _ORIG.get("style")
    set_text = _ORIG.get("text")
    app.setStyleSheet(live(APP_QSS))
    for w in app.allWidgets():
        ss = w.styleSheet()
        if ss:
            (set_style or type(w).setStyleSheet)(w, translate(ss, old, new))
        if isinstance(w, QLabel) and set_text and "#" in w.text() and "<" in w.text():
            set_text(w, translate(w.text(), old, new))
        if isinstance(w, QTextBrowser):
            bar = w.verticalScrollBar()
            pos = bar.value()
            w.setHtml(translate(w.toHtml(), old, new))
            bar.setValue(pos)
    return new


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
QCheckBox, QRadioButton {{ spacing: 8px; background: transparent; }}
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
