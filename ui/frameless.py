"""Resizing a window that has no native frame: find the edge under the mouse and hand over to the system."""
from PySide6.QtCore import QEvent, QObject, QPoint, QSize, Qt
from PySide6.QtWidgets import QWidget

EDGE_MARGIN = 6

_CURSORS = {
    Qt.LeftEdge: Qt.SizeHorCursor,
    Qt.RightEdge: Qt.SizeHorCursor,
    Qt.TopEdge: Qt.SizeVerCursor,
    Qt.BottomEdge: Qt.SizeVerCursor,
    Qt.LeftEdge | Qt.TopEdge: Qt.SizeFDiagCursor,
    Qt.RightEdge | Qt.BottomEdge: Qt.SizeFDiagCursor,
    Qt.RightEdge | Qt.TopEdge: Qt.SizeBDiagCursor,
    Qt.LeftEdge | Qt.BottomEdge: Qt.SizeBDiagCursor,
}


def edges_at(pos: QPoint, size: QSize, margin: int = EDGE_MARGIN) -> Qt.Edges:
    edges = Qt.Edges()
    if pos.x() < margin:
        edges |= Qt.LeftEdge
    elif pos.x() >= size.width() - margin:
        edges |= Qt.RightEdge
    if pos.y() < margin:
        edges |= Qt.TopEdge
    elif pos.y() >= size.height() - margin:
        edges |= Qt.BottomEdge
    return edges


class EdgeResizer(QObject):
    """Application-wide event filter: shows a resize cursor near the window edge and starts a system resize."""

    def __init__(self, window: QWidget):
        super().__init__(window)
        self._window = window

    def eventFilter(self, obj, event):
        kind = event.type()
        if kind not in (QEvent.MouseMove, QEvent.MouseButtonPress):
            return False
        if not isinstance(obj, QWidget) or obj.window() is not self._window:
            return False
        if self._window.isMaximized() or self._window.isFullScreen():
            return False

        pos = self._window.mapFromGlobal(event.globalPosition().toPoint())
        edges = edges_at(pos, self._window.size())
        if kind == QEvent.MouseMove and event.buttons() == Qt.NoButton:
            if edges:
                self._window.setCursor(_CURSORS[edges])
            else:
                self._window.unsetCursor()
        elif kind == QEvent.MouseButtonPress and event.button() == Qt.LeftButton and edges:
            handle = self._window.windowHandle()
            if handle is not None:
                handle.startSystemResize(edges)
                return True
        return False
