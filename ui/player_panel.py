from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QSlider, QStyle, QVBoxLayout,
)

from ui.strings import DEFAULT_LANGUAGE, tr

TRACKS = ("original", "karaoke", "acapella")
HANDLE_WIDTH = 14


def format_time(ms: int) -> str:
    seconds = max(0, ms) // 1000
    return f"{seconds // 60}:{seconds % 60:02d}"


class SeekSlider(QSlider):
    """A slider where a click jumps to that spot and a drag scrubs; the player only seeks on release."""

    previewed = Signal(int)
    committed = Signal(int)

    def __init__(self):
        super().__init__(Qt.Horizontal)
        self.dragging = False
        self.setCursor(Qt.PointingHandCursor)

    def _value_at(self, x: float) -> int:
        usable = max(1, self.width() - HANDLE_WIDTH)
        return QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), int(x - HANDLE_WIDTH / 2), usable)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.maximum() > 0:
            self.dragging = True
            value = self._value_at(event.position().x())
            self.setValue(value)
            self.previewed.emit(value)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging:
            value = self._value_at(event.position().x())
            self.setValue(value)
            self.previewed.emit(value)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dragging and event.button() == Qt.LeftButton:
            self.dragging = False
            value = self._value_at(event.position().x())
            self.setValue(value)
            self.committed.emit(value)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class PlayerPanel(QFrame):
    """Plays the original, karaoke or acapella track. Switching tracks keeps the position and play state."""

    failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("player")
        self.language = DEFAULT_LANGUAGE
        self._paths: dict[str, Path] = {}
        self._current: str | None = None
        self._resume: tuple[int, bool] | None = None

        self.audio = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio)
        self.player.positionChanged.connect(self._on_position)
        self.player.durationChanged.connect(self._on_duration)
        self.player.playbackStateChanged.connect(self._update_play_button)
        self.player.mediaStatusChanged.connect(self._on_media_status)
        self.player.errorOccurred.connect(lambda _error, message: self.failed.emit(message))

        self.track_buttons: dict[str, QPushButton] = {}
        group = QButtonGroup(self)
        group.setExclusive(True)
        tabs = QHBoxLayout()
        tabs.setSpacing(8)
        for key in TRACKS:
            button = QPushButton()
            button.setObjectName("tab")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked, k=key: self.select(k))
            group.addButton(button)
            tabs.addWidget(button, 1)
            self.track_buttons[key] = button

        self.play_button = QPushButton()
        self.play_button.setMinimumWidth(110)
        self.play_button.clicked.connect(self._toggle_play)
        self.slider = SeekSlider()
        self.slider.previewed.connect(self._on_preview)
        self.slider.committed.connect(self.player.setPosition)
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setObjectName("muted")
        self.time_label.setMinimumWidth(92)
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        transport = QHBoxLayout()
        transport.setSpacing(12)
        transport.addWidget(self.play_button)
        transport.addWidget(self.slider, 1)
        transport.addWidget(self.time_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)
        layout.addLayout(tabs)
        layout.addLayout(transport)
        self.retranslate(self.language)
        self.hide()

    # ---- public -------------------------------------------------------

    def set_tracks(self, paths: dict[str, Path], first: str = "karaoke"):
        self.clear()
        self._paths = dict(paths)
        self.select(first)
        self.show()

    def clear(self):
        self.player.stop()
        self.player.setSource(QUrl())
        self._paths, self._current, self._resume = {}, None, None
        self.slider.setRange(0, 0)
        self.time_label.setText("0:00 / 0:00")
        self.hide()

    def select(self, key: str):
        if key == self._current or key not in self._paths:
            return
        was_playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        self._resume = (self.player.position() if self._current else 0, was_playing)
        self._current = key
        self.track_buttons[key].setChecked(True)
        self.player.setSource(QUrl.fromLocalFile(str(self._paths[key])))

    def retranslate(self, language: str):
        self.language = language
        for key, button in self.track_buttons.items():
            button.setText(tr(language, f"track_{key}"))
        self._update_play_button()

    # ---- internals ----------------------------------------------------

    def _toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _update_play_button(self, *_):
        playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        self.play_button.setText(tr(self.language, "pause" if playing else "play"))

    def _on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.LoadedMedia and self._resume:
            position, was_playing = self._resume
            self._resume = None
            self.player.setPosition(position)
            if was_playing:
                self.player.play()

    def _on_position(self, position: int):
        if not self.slider.dragging:
            self.slider.setValue(position)
            self._show_time(position)

    def _on_duration(self, duration: int):
        self.slider.setRange(0, duration)
        self._show_time(self.player.position())

    def _on_preview(self, position: int):
        self._show_time(position)

    def _show_time(self, position: int):
        self.time_label.setText(f"{format_time(position)} / {format_time(self.player.duration())}")
