"""Application-wide look: the bundled pixel font and high-DPI behaviour."""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

ASSETS = Path(__file__).resolve().parent.parent / "assets"
ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)
FONT_FILE = ASSETS / "fonts" / "TA GBA monothai_MAX.ttf"
# Per-glyph fallback: Thai if the pixel font ever lacks a letter, and symbols it does not have (÷ ×).
FALLBACK_FAMILIES = ["Leelawadee UI", "Segoe UI"]
BASE_PIXEL_SIZE = 16  # the font is drawn on a 16-cell em, so multiples of 16 px stay crisp


def configure_high_dpi() -> None:
    """Call before creating the QApplication. Whole-number scaling keeps pixel art sharp at 125% and 150%."""
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.Round)


def setup_fonts(app) -> bool:
    """Load the bundled font and make it the default. Returns False if it could not be loaded."""
    families: list[str] = []
    font_id = QFontDatabase.addApplicationFont(str(FONT_FILE))
    if font_id >= 0:
        families = QFontDatabase.applicationFontFamilies(font_id)
    font = QFont()
    font.setFamilies(families + FALLBACK_FAMILIES)
    font.setPixelSize(BASE_PIXEL_SIZE)
    app.setFont(font)
    return bool(families)


def load_svg_icon(path: Path) -> QIcon:
    """QIcon(path) returns an empty icon for an SVG here (the SVG image plugin is not shipped), so draw it ourselves."""
    renderer = QSvgRenderer(str(path))
    icon = QIcon()
    for size in ICON_SIZES:
        image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(QPixmap.fromImage(image))
    return icon


def system_prefers_dark() -> bool:
    return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
