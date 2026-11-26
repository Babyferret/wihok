"""The window's own title bar: icon and name on the left, language, theme and window buttons on the right."""
from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QAbstractButton, QComboBox, QHBoxLayout, QLabel, QWidget

from ui.appearance import ASSETS, load_svg_icon
from ui.strings import LANGUAGES
from ui.theme import Palette

BAR_HEIGHT = 40


class IconButton(QAbstractButton):
    """A flat button whose icon is drawn with lines, so it follows the palette in both themes."""

    def __init__(self, kind: str, width: int = 46):
        super().__init__()
        self.kind = kind
        self.setFixedSize(QSize(width, BAR_HEIGHT))
        self.setFocusPolicy(Qt.TabFocus)
        self.setCursor(Qt.ArrowCursor)
        self._fg = QColor("#000000")
        self._hover_bg = QColor("#EEEEEE")
        self._pressed_bg = QColor("#DDDDDD")
        self._hover_fg = QColor("#000000")
        self._badge = False
        self._badge_color = QColor("#D9708F")

    def set_badge(self, on: bool, color: str | None = None):
        """A small dot in the corner: something here wants the person's attention."""
        self._badge = on
        if color:
            self._badge_color = QColor(color)
        self.update()

    def set_kind(self, kind: str):
        self.kind = kind
        self.update()

    def set_colors(self, fg: str, hover_bg: str, pressed_bg: str, hover_fg: str | None = None):
        self._fg, self._hover_bg, self._pressed_bg = QColor(fg), QColor(hover_bg), QColor(pressed_bg)
        self._hover_fg = QColor(hover_fg or fg)
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        hovered, down = self.underMouse(), self.isDown()
        if hovered or down:
            painter.fillRect(self.rect(), self._pressed_bg if down else self._hover_bg)
        color = self._hover_fg if (hovered or down) else self._fg
        c = QPointF(self.width() / 2, self.height() / 2)
        pen = QPen(color, 1.4)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)

        if self.kind == "minimize":
            painter.drawLine(QPointF(c.x() - 5, c.y()), QPointF(c.x() + 5, c.y()))
        elif self.kind == "maximize":
            painter.drawRect(QRectF(c.x() - 5, c.y() - 5, 10, 10))
        elif self.kind == "restore":
            painter.drawRect(QRectF(c.x() - 6, c.y() - 3, 9, 9))
            path = QPainterPath(QPointF(c.x() - 3, c.y() - 3))
            path.lineTo(c.x() - 3, c.y() - 6)
            path.lineTo(c.x() + 6, c.y() - 6)
            path.lineTo(c.x() + 6, c.y() + 3)
            path.lineTo(c.x() + 3, c.y() + 3)
            painter.drawPath(path)
        elif self.kind == "close":
            painter.drawLine(QPointF(c.x() - 5, c.y() - 5), QPointF(c.x() + 5, c.y() + 5))
            painter.drawLine(QPointF(c.x() - 5, c.y() + 5), QPointF(c.x() + 5, c.y() - 5))
        elif self.kind == "moon":
            moon = QPainterPath()
            moon.addEllipse(c, 6.5, 6.5)
            bite = QPainterPath()
            bite.addEllipse(QPointF(c.x() + 3.5, c.y() - 3), 5.5, 5.5)
            painter.setPen(Qt.NoPen)
            painter.fillPath(moon.subtracted(bite), color)
        elif self.kind == "update":  # an arrow going down into a tray
            painter.drawLine(QPointF(c.x(), c.y() - 6), QPointF(c.x(), c.y() + 2))
            arrow = QPainterPath(QPointF(c.x() - 4, c.y() - 2))
            arrow.lineTo(c.x(), c.y() + 2)
            arrow.lineTo(c.x() + 4, c.y() - 2)
            painter.drawPath(arrow)
            painter.drawLine(QPointF(c.x() - 6, c.y() + 6), QPointF(c.x() + 6, c.y() + 6))
        elif self.kind == "sun":
            painter.drawEllipse(c, 3.5, 3.5)
            for i in range(8):
                painter.save()
                painter.translate(c)
                painter.rotate(i * 45)
                painter.drawLine(QPointF(0, -6.5), QPointF(0, -8.5))
                painter.restore()

        if self._badge:
            painter.setPen(Qt.NoPen)
            painter.setBrush(self._badge_color)
            painter.drawEllipse(QPointF(c.x() + 7, c.y() - 7), 3.5, 3.5)
            painter.setBrush(Qt.NoBrush)

        if self.hasFocus():
            focus = QPen(self._fg, 1)
            focus.setStyle(Qt.DotLine)
            painter.setPen(focus)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.rect().adjusted(2, 2, -3, -3))


class TitleBar(QWidget):
    def __init__(self, language: str):
        super().__init__()
        self.setObjectName("titlebar")
        self.setFixedHeight(BAR_HEIGHT)

        icon = QLabel()
        icon.setPixmap(load_svg_icon(ASSETS / "wihok.svg").pixmap(24, 24))
        title = QLabel("Wihok")
        title.setObjectName("title-text")
        self.version_label = QLabel()
        self.version_label.setObjectName("version-text")

        self.language_box = QComboBox()
        self.language_box.setObjectName("lang-select")
        self.language_box.setFocusPolicy(Qt.TabFocus)
        for code, name in LANGUAGES.items():
            self.language_box.addItem(name, code)
        self.language_box.setCurrentIndex(self.language_box.findData(language))

        self.update_button = IconButton("update", width=40)
        self.theme_button = IconButton("moon", width=40)
        self.minimize_button = IconButton("minimize")
        self.maximize_button = IconButton("maximize")
        self.close_button = IconButton("close")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(icon)
        layout.addSpacing(8)
        layout.addWidget(title)
        layout.addSpacing(8)
        layout.addWidget(self.version_label)
        layout.addStretch()
        layout.addWidget(self.language_box)
        layout.addSpacing(8)
        for button in (self.update_button, self.theme_button, self.minimize_button, self.maximize_button, self.close_button):
            layout.addWidget(button)

        self.minimize_button.clicked.connect(lambda: self.window().showMinimized())
        self.maximize_button.clicked.connect(self.toggle_maximized)
        self.close_button.clicked.connect(lambda: self.window().close())

    def toggle_maximized(self):
        window = self.window()
        window.showNormal() if window.isMaximized() else window.showMaximized()

    def set_maximized(self, maximized: bool):
        self.maximize_button.set_kind("restore" if maximized else "maximize")

    def apply_palette(self, p: Palette):
        for button in (self.update_button, self.theme_button, self.minimize_button, self.maximize_button):
            button.set_colors(p.text, p.tint_hover, p.tint_pressed)
        self.update_button.set_badge(self.update_button._badge, p.accent)
        self.close_button.set_colors(p.text, p.close_hover, p.close_hover, hover_fg="#FFFFFF")
        # Show the icon of the theme the button switches to.
        self.theme_button.set_kind("sun" if p.name == "dark" else "moon")

    # Dragging the bar moves the window; double-click maximizes. Buttons keep their own clicks.
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None:
                handle.startSystemMove()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_maximized()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)
