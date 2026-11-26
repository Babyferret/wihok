"""Generate the Windows icon and the installer images from the bird drawing.

Run with the project's Python:  python packaging/make_assets.py
Writes into packaging/generated/ (not committed). Small icon sizes use thicker lines and fewer details
instead of shrinking the big drawing, as decided in the plan.
"""
import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "packaging" / "generated"
FONT_FILE = ROOT / "assets" / "fonts" / "TA GBA monothai_MAX.ttf"

PLUM, PINK, CREAM = "#3A2A31", "#F4A6BE", "#FBF6F7"
BODY = "M52 20C52 13 42 11 38 17C34 22 36 27 31 31C23 38 16 46 8 54C20 55 29 52 35 48C45 42 51 34 52 26"
BEAK = "M52 20L59 23L52 26"
LEGS = "M32 49.5L31 58M37.5 46.5L37.5 58"
WING = "M26 40C32 37 38 39 40 43"
EYE = f'<circle cx="46" cy="19" r="1.8" fill="{PLUM}" stroke="none"/>'
INNER = "translate(32 32) scale(.92) translate(-33.5 -34.5)"


def tier(size: int) -> tuple[float, bool, bool]:
    """(stroke width in drawing units, legs, wing+eye) for an icon of this pixel size."""
    if size >= 96:
        return 3.2, True, True
    if size >= 48:
        return 3.8, True, True
    if size >= 24:
        return 4.8, True, False
    return 6.0, False, False


def bird_svg(size: int, tile: bool = True, color: str = PLUM) -> str:
    stroke, legs, detail = tier(size)
    stroke /= 0.92
    parts = [f'<path d="{BODY}"/>', f'<path d="{BEAK}"/>']
    if legs:
        parts += [f'<path d="{d}"/>' for d in LEGS.replace("M", "|M").split("|") if d]
    if detail:
        parts += [f'<path d="{WING}"/>', EYE.replace(PLUM, color)]
    rect = f'<rect width="64" height="64" rx="14" fill="{PINK}"/>' if tile else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">{rect}'
        f'<g transform="{INNER}" fill="none" stroke="{color}" stroke-width="{stroke:.2f}" '
        f'stroke-linecap="round" stroke-linejoin="round">{"".join(parts)}</g></svg>'
    )


def render_svg(svg: str, width: int, height: int | None = None) -> QImage:
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    image = QImage(width, height or width, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    renderer.render(painter, QRectF(0, 0, width, height or width))
    painter.end()
    return image


def png_bytes(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


def write_ico(path: Path, sizes: list[int]) -> None:
    """An .ico with one PNG-compressed image per size (supported since Windows Vista)."""
    images = [(s, png_bytes(render_svg(bird_svg(s), s))) for s in sizes]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    directory, payload = b"", b""
    for size, data in images:
        directory += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset + len(payload))
        payload += data
    path.write_bytes(header + directory + payload)


def wizard_image(width: int, height: int, font_family: str) -> QImage:
    """The tall image on the installer's welcome and finish pages: one large bird and the name."""
    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(QColor(PINK))
    scale = width / 164
    bird_w = int(width * 0.78)
    bird = render_svg(bird_svg(256, tile=False), bird_w)
    painter = QPainter(image)
    painter.drawImage((width - bird_w) // 2, int(height * 0.20), bird)
    font = QFont(font_family)
    font.setPixelSize(16 * max(2, round(2 * scale)))  # a multiple of 16 keeps the pixel font crisp
    painter.setFont(font)
    painter.setPen(QColor(PLUM))
    painter.drawText(QRectF(0, height * 0.70, width, height * 0.12), Qt.AlignCenter, "Wihok")
    painter.end()
    return image


def small_image(size: int) -> QImage:
    """The icon in the corner of the wizard's header. The wizard puts it flush against the top and right edges of
    a white header, so the image is white with the icon inset: the margin is part of the picture."""
    image = QImage(size, size, QImage.Format_RGB32)
    image.fill(QColor("#FFFFFF"))
    tile = round(size * 0.80)
    margin = (size - tile) // 2
    painter = QPainter(image)
    painter.drawImage(margin, margin, render_svg(bird_svg(tile), tile))
    painter.end()
    return image


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QGuiApplication(sys.argv)
    families = QFontDatabase.applicationFontFamilies(QFontDatabase.addApplicationFont(str(FONT_FILE)))
    family = families[0] if families else "Segoe UI"

    write_ico(OUT / "wihok.ico", [16, 24, 32, 48, 64, 128, 256])
    # Sizes for 100%, 125%, 150% and 200% display scaling.
    for w, h in ((164, 314), (192, 386), (246, 459), (328, 628)):
        wizard_image(w, h, family).save(str(OUT / f"wizard-{w}x{h}.bmp"))
    for s in (55, 64, 83, 110):
        small_image(s).save(str(OUT / f"wizard-small-{s}.bmp"))
    for p in sorted(OUT.iterdir()):
        print(f"{p.name:28s} {p.stat().st_size:>8,d} bytes")
    del app
    return 0


if __name__ == "__main__":
    sys.exit(main())
