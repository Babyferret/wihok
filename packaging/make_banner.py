r"""Draws the README banner: the app icon and the name in the app's own pixel font, in a light and a dark version.

  .\.venv\Scripts\python.exe packaging\make_banner.py

Writes assets/banner-light.png and assets/banner-dark.png (1280 x 360, shown at half size in the README so the
pixel font stays sharp on high-density screens). The font sizes are multiples of 16 px, as in the app.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontMetrics, QGuiApplication, QImage, QPainter, QPainterPath
from PySide6.QtSvg import QSvgRenderer

from ui.appearance import ASSETS, FONT_FILE
from ui.theme import DARK, LIGHT

WIDTH, HEIGHT = 1280, 360
ICON = 200
TAGLINE = "Karaoke  /  Acapella  /  BPM  /  Key"  # the pixel font has no middle dot, so a slash separates


def draw(palette, path: Path, font_family: str):
    image = QImage(WIDTH, HEIGHT, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)

    card = QPainterPath()
    card.addRoundedRect(QRectF(0, 0, WIDTH, HEIGHT), 28, 28)
    p.fillPath(card, QColor(palette.background))
    p.setPen(QColor(palette.line))
    p.drawPath(card)

    def text(value: str, size: int, color: str, x: int, baseline: int):
        font = QFont(font_family)
        font.setPixelSize(size)
        font.setStyleStrategy(QFont.NoAntialias)  # keep the pixel font's squares hard-edged
        p.setFont(font)
        p.setPen(QColor(color))
        p.drawText(x, baseline, value)
        return p.fontMetrics().horizontalAdvance(value)

    # measure the text block first so the icon and the words are centred together
    name_size, thai_size, tag_size, gap = 128, 96, 32, 56
    probe = QFont(font_family)
    probe.setPixelSize(name_size)
    name_width = QFontMetrics(probe).horizontalAdvance("Wihok")
    block = ICON + gap + max(name_width, 700)
    left = (WIDTH - block) // 2

    renderer = QSvgRenderer(str(ASSETS / "wihok.svg"))
    renderer.render(p, QRectF(left, (HEIGHT - ICON) / 2, ICON, ICON))

    x = left + ICON + gap
    text("Wihok", name_size, palette.text, x, 160)
    thai_x = x + name_width + 28
    text("วิหค", thai_size, palette.accent, thai_x, 160)
    text(TAGLINE, tag_size, palette.muted, x + 4, 240)
    p.end()
    image.save(str(path))
    print("wrote", path)


def main():
    app = QGuiApplication([])
    font_id = QFontDatabase.addApplicationFont(str(FONT_FILE))
    family = QFontDatabase.applicationFontFamilies(font_id)[0]
    out = ASSETS
    draw(LIGHT, out / "banner-light.png", family)
    draw(DARK, out / "banner-dark.png", family)
    return 0


if __name__ == "__main__":
    sys.exit(main())
