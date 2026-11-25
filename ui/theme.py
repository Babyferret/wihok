"""Light and dark palettes and the style sheet built from them. Pink pastel accents; no gradients or shadows.

The app font is a pixel font with a single weight, so the style sheet never asks for bold, and sizes are
multiples of 16 px (the font is drawn on a 16-cell em, so those sizes stay crisp).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    name: str
    background: str
    surface: str
    text: str
    muted: str
    line: str
    pink: str
    pink_hover: str
    pink_pressed: str
    on_pink: str  # text on a pink button
    accent: str
    error: str
    groove: str
    dashed: str
    tint_hover: str
    tint_pressed: str
    disabled_bg: str
    disabled_text: str
    scroll_handle: str
    close_hover: str = "#E81123"


LIGHT = Palette(
    name="light",
    background="#FBF6F7", surface="#FFFFFF", text="#3A2A31", muted="#7A6670", line="#EBDDE2",
    pink="#F4B6C8", pink_hover="#F0A5BC", pink_pressed="#E58BA8", on_pink="#3A2A31",
    accent="#D9708F", error="#B3365A", groove="#F3E4E9", dashed="#E3B5C4",
    tint_hover="#FFF0F4", tint_pressed="#F9DCE5",
    disabled_bg="#EFE3E7", disabled_text="#A8959D", scroll_handle="#E3B5C4",
)

DARK = Palette(
    name="dark",
    background="#161014", surface="#1F171C", text="#F5E8ED", muted="#A99AA2", line="#34272F",
    pink="#F4A6BE", pink_hover="#F7B8CB", pink_pressed="#E58BA8", on_pink="#2A1B22",
    accent="#F08FAE", error="#FF8FA8", groove="#33262E", dashed="#5B3F4C",
    tint_hover="#2A1E25", tint_pressed="#352730",
    disabled_bg="#2B2128", disabled_text="#76666E", scroll_handle="#5B3F4C",
)

PALETTES = {"light": LIGHT, "dark": DARK}


def stylesheet(p: Palette) -> str:
    return f"""
QWidget {{ background: {p.background}; color: {p.text}; }}
QLabel {{ background: transparent; }}
QLabel#muted {{ color: {p.muted}; }}
QLabel#status[kind="error"] {{ color: {p.error}; }}
QLabel#readout {{ font-size: 32px; }}
QLabel#drop-title {{ font-size: 32px; }}
/* 24 px sits between the two crisp sizes (16 and 32); it is a little soft but clearly larger than 16. */
QLabel#title-text {{ font-size: 24px; }}
QLabel#drop-formats {{ color: {p.muted}; font-size: 24px; }}
QLabel#status {{ font-size: 24px; }}

QFrame#frame {{ background: {p.background}; border: 1px solid {p.line}; }}
QFrame#frame[maximized="true"] {{ border: none; }}

QFrame#dropzone {{
    background: {p.surface};
    border: 2px dashed {p.dashed};
    border-radius: 12px;
}}
QFrame#dropzone[dragging="true"] {{ background: {p.tint_hover}; border-color: {p.accent}; }}

QFrame#results {{
    background: {p.surface};
    border: 1px solid {p.line};
    border-radius: 12px;
}}
QFrame#player {{
    background: {p.surface};
    border: 1px solid {p.line};
    border-radius: 12px;
}}

/* Buttons never take focus from a mouse click (see MainWindow), so the focus
   border below only shows for keyboard users. A click is shown by the pressed colour. */
QPushButton {{
    background: {p.pink};
    color: {p.on_pink};
    border: 2px solid transparent;
    border-radius: 8px;
    padding: 6px 14px;
}}
QPushButton:hover {{ background: {p.pink_hover}; }}
QPushButton:pressed {{ background: {p.pink_pressed}; }}
QPushButton:focus {{ border-color: {p.accent}; }}
QPushButton:disabled {{ background: {p.disabled_bg}; color: {p.disabled_text}; }}

QPushButton#secondary {{ background: transparent; color: {p.text}; border-color: {p.dashed}; }}
QPushButton#secondary:hover {{ background: {p.tint_hover}; }}
QPushButton#secondary:pressed {{ background: {p.tint_pressed}; }}
QPushButton#secondary:focus {{ border-color: {p.accent}; }}
QPushButton#secondary:disabled {{ background: transparent; border-color: {p.line}; color: {p.disabled_text}; }}

QPushButton#tab {{ background: transparent; color: {p.text}; border-color: {p.line}; }}
QPushButton#tab:hover {{ background: {p.tint_hover}; }}
QPushButton#tab:pressed {{ background: {p.tint_pressed}; }}
QPushButton#tab:checked {{ background: {p.pink}; color: {p.on_pink}; border-color: {p.pink}; }}
QPushButton#tab:checked:pressed {{ background: {p.pink_pressed}; border-color: {p.pink_pressed}; }}
QPushButton#tab:focus {{ border-color: {p.accent}; }}

QSlider::groove:horizontal {{ height: 6px; background: {p.groove}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {p.accent}; border-radius: 3px; }}
QSlider::handle:horizontal {{
    background: {p.accent};
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}}

QProgressBar {{
    background: {p.groove};
    border: none;
    border-radius: 3px;
    min-height: 6px;
    max-height: 6px;
}}
QProgressBar::chunk {{ background: {p.accent}; border-radius: 3px; }}

QComboBox {{
    background: {p.surface};
    color: {p.text};
    border: 1px solid {p.line};
    border-radius: 8px;
    padding: 4px 10px;
}}
QComboBox#key-select {{ font-size: 32px; padding: 2px 12px; }}
QComboBox#lang-select {{ padding: 2px 8px; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {p.surface};
    color: {p.text};
    selection-background-color: {p.pink};
    selection-color: {p.on_pink};
    border: 1px solid {p.line};
}}

QScrollArea {{ border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {p.scroll_handle}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QToolTip {{ background: {p.surface}; color: {p.text}; border: 1px solid {p.line}; padding: 4px 8px; }}
"""
