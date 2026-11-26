import threading
from pathlib import Path

from PySide6.QtCore import QEvent, QSettings, QStandardPaths, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from core.analysis import NOTES
from core.device import looks_cuda_capable, probe_device
from ui.appearance import system_prefers_dark
from ui.frameless import EdgeResizer
from ui.player_panel import PlayerPanel
from ui.strings import DEFAULT_LANGUAGE, LANGUAGES, tr
from ui.theme import PALETTES, stylesheet
from ui.title_bar import TitleBar
from ui.update_bar import UpdateBar
from ui.update_ui import UpdateUi
from ui.worker import ProcessWorker

SUPPORTED_SUFFIXES = {".mp3", ".wav", ".flac", ".m4a"}
BPM_RANGE = (30.0, 300.0)  # the ÷2 and ×2 buttons stop at a tempo no song has
SHOW_TUNING_CONTROLS = False  # ÷2 / ×2 and the key picker are built but kept out of sight until they are really used
STAGE_KEYS = {
    "reusing": "reusing",
    "downloading_model": "downloading_model",
    "separating": "separating",
    "analyzing": "analyzing",
}


class DropZone(QFrame):
    """Accepts a song dragged from Explorer and offers a file picker as the alternative."""

    file_dropped = Signal(object)
    choose_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("dropzone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(190)
        self.title = QLabel(alignment=Qt.AlignCenter)
        self.title.setObjectName("drop-title")
        self.formats = QLabel(alignment=Qt.AlignCenter)
        self.formats.setObjectName("drop-formats")
        self.button = QPushButton()
        self.button.clicked.connect(self.choose_clicked)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)
        layout.addStretch()
        layout.addWidget(self.title)
        layout.addWidget(self.formats)
        layout.addSpacing(8)
        layout.addWidget(self.button, alignment=Qt.AlignCenter)
        layout.addStretch()

    def _set_dragging(self, dragging: bool):
        self.setProperty("dragging", dragging)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_dragging(True)

    def dragLeaveEvent(self, event):
        self._set_dragging(False)

    def dropEvent(self, event):
        self._set_dragging(False)
        urls = [u for u in event.mimeData().urls() if u.isLocalFile()]
        if urls:
            self.file_dropped.emit(Path(urls[0].toLocalFile()))


class MainWindow(QMainWindow):
    device_probed = Signal(str)

    def __init__(self, output_base: Path | None = None, device: str | None = None, check_updates: bool = True):
        super().__init__()
        self.setWindowTitle("Wihok")  # still used by the taskbar even though the title bar is our own
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowMinMaxButtonsHint)
        self.setMinimumSize(560, 600)
        self.resize(600, 880)

        self._settings = QSettings()
        saved = self._settings.value("language", DEFAULT_LANGUAGE)
        self.language = saved if saved in LANGUAGES else DEFAULT_LANGUAGE
        saved_theme = self._settings.value("theme")
        self.theme_name = saved_theme if saved_theme in PALETTES else ("dark" if system_prefers_dark() else "light")
        music = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.MusicLocation)
        self.output_base = Path(output_base) if output_base else Path(music) / "Wihok"
        # Importing torch here would keep hundreds of MB in memory for as long as the window is open. So guess from
        # the files first, and let a short-lived second process confirm what PyTorch really sees.
        self.device = device or ("cuda" if looks_cuda_capable() else "cpu")
        self._probe_needed = device is None and self.device == "cuda"

        self._worker: ProcessWorker | None = None
        self._cancel = threading.Event()
        self._song: Path | None = None
        self._done = None
        self._status = ("cpu_mode" if self.device == "cpu" else "ready", "normal", {})

        self._build()
        self.update_ui = UpdateUi(self, auto_check=check_updates)
        self._apply_theme(self.theme_name)
        self._retranslate()
        self._resizer = EdgeResizer(self)
        QApplication.instance().installEventFilter(self._resizer)
        self.device_probed.connect(self._on_device_probed)
        if self._probe_needed:
            threading.Thread(target=self._probe_device, daemon=True).start()

    def _probe_device(self):
        device = probe_device()
        try:
            self.device_probed.emit(device)
        except RuntimeError:  # the window was closed before the check finished
            pass

    def _on_device_probed(self, device: str):
        if device == self.device:
            return
        self.device = device
        if self._status[0] == "ready":
            self._set_status("cpu_mode")

    # ---- layout -------------------------------------------------------

    def _build(self):
        root = QVBoxLayout()
        root.setContentsMargins(28, 12, 28, 24)
        root.setSpacing(16)

        self.title_bar = TitleBar(self.language)
        self.language_box = self.title_bar.language_box
        self.language_box.currentIndexChanged.connect(self._on_language_changed)
        self.title_bar.theme_button.clicked.connect(self._toggle_theme)

        self.update_bar = UpdateBar()
        root.addWidget(self.update_bar)

        self.drop_zone = DropZone()
        self.drop_zone.file_dropped.connect(self.start_processing)
        self.drop_zone.choose_clicked.connect(self._choose_file)
        root.addWidget(self.drop_zone)

        self.status_label = QLabel()
        self.status_label.setObjectName("status")
        self.status_label.setWordWrap(True)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.cancel_button = QPushButton()
        self.cancel_button.setObjectName("secondary")
        self.cancel_button.clicked.connect(self._cancel_clicked)
        status_row = QHBoxLayout()
        status_row.addWidget(self.status_label, 1)
        status_row.addWidget(self.cancel_button)
        root.addLayout(status_row)
        root.addWidget(self.progress)

        self.results = self._build_results()
        root.addWidget(self.results)
        self.player = PlayerPanel()
        self.player.failed.connect(lambda error: self._set_status("player_failed", "error", error=error))
        root.addWidget(self.player)
        root.addStretch()

        content = QWidget()
        content.setLayout(root)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setWidget(content)

        self.frame = QFrame()
        self.frame.setObjectName("frame")
        outer = QVBoxLayout(self.frame)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self.title_bar)
        outer.addWidget(self.scroll, 1)
        self.setCentralWidget(self.frame)
        # A mouse click must not leave a focus ring on a button; Tab still reaches it.
        for button in content.findChildren(QPushButton):
            button.setFocusPolicy(Qt.TabFocus)

    def _build_results(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("results")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        self.bpm_caption, self.bpm_value, self.bpm_note = QLabel(), QLabel(), QLabel()
        self.key_caption, self.key_box, self.key_note = QLabel(), QComboBox(), QLabel()
        for label in (self.bpm_caption, self.bpm_note, self.key_caption, self.key_note):
            label.setObjectName("muted")
        self.bpm_value.setObjectName("readout")
        self.key_box.setObjectName("key-select")
        for tonic in NOTES:
            for mode in ("major", "minor"):
                self.key_box.addItem(f"{tonic} {mode}")
        self.key_box.currentIndexChanged.connect(self._on_key_changed)

        self.halve_button, self.double_button = QPushButton("÷2"), QPushButton("×2")
        for button in (self.halve_button, self.double_button):
            button.setObjectName("secondary")
            button.setMinimumWidth(56)
        self.halve_button.clicked.connect(lambda: self._scale_bpm(0.5))
        self.double_button.clicked.connect(lambda: self._scale_bpm(2.0))
        bpm_buttons = QHBoxLayout()
        bpm_buttons.setSpacing(8)
        bpm_buttons.addWidget(self.halve_button)
        bpm_buttons.addWidget(self.double_button)
        bpm_buttons.addStretch()
        if not SHOW_TUNING_CONTROLS:
            # the key stays on screen as a plain readout: not clickable, no arrow
            self.halve_button.hide()
            self.double_button.hide()
            self.key_box.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.key_box.setFocusPolicy(Qt.NoFocus)
            self.key_box.setProperty("locked", True)

        bpm_column = QVBoxLayout()
        bpm_column.setSpacing(4)
        for item in (self.bpm_caption, self.bpm_value):
            bpm_column.addWidget(item)
        bpm_column.addLayout(bpm_buttons)
        bpm_column.addWidget(self.bpm_note)
        bpm_column.addStretch()
        key_column = QVBoxLayout()
        key_column.setSpacing(4)
        for item in (self.key_caption, self.key_box, self.key_note):
            key_column.addWidget(item)
        key_column.addStretch()
        numbers = QHBoxLayout()
        numbers.setSpacing(24)
        numbers.addLayout(bpm_column, 1)
        numbers.addLayout(key_column, 1)
        layout.addLayout(numbers)

        self.karaoke_caption, self.karaoke_name = QLabel(), QLabel()
        self.acapella_caption, self.acapella_name = QLabel(), QLabel()
        for caption in (self.karaoke_caption, self.acapella_caption):
            caption.setObjectName("muted")
        for name in (self.karaoke_name, self.acapella_name):
            name.setTextInteractionFlags(Qt.TextSelectableByMouse)
            name.setWordWrap(True)
        for caption, name in ((self.karaoke_caption, self.karaoke_name), (self.acapella_caption, self.acapella_name)):
            layout.addWidget(caption)
            layout.addWidget(name)

        self.open_button = QPushButton()
        self.open_button.clicked.connect(self._open_folder)
        self.reset_button = QPushButton()
        self.reset_button.setObjectName("secondary")
        self.reset_button.clicked.connect(self._reset_edits)
        self.reset_button.hide()
        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addWidget(self.open_button)
        actions.addWidget(self.reset_button)
        actions.addStretch()
        layout.addLayout(actions)
        frame.hide()
        return frame

    # ---- text ---------------------------------------------------------

    def _retranslate(self):
        t = lambda key, **v: tr(self.language, key, **v)
        self.language_box.setToolTip(t("language"))
        self.title_bar.theme_button.setToolTip(t("switch_theme"))
        self.title_bar.minimize_button.setToolTip(t("minimize"))
        self.title_bar.maximize_button.setToolTip(t("restore") if self.isMaximized() else t("maximize"))
        self.title_bar.close_button.setToolTip(t("close_window"))
        self.drop_zone.title.setText(t("drop_hint"))
        self.drop_zone.formats.setText(t("drop_formats"))
        self.drop_zone.button.setText(t("choose_file"))
        self.cancel_button.setText(t("cancel"))
        self.open_button.setText(t("open_folder"))
        self.bpm_caption.setText(t("bpm"))
        self.key_caption.setText(t("key"))
        self.karaoke_caption.setText(t("karaoke"))
        self.acapella_caption.setText(t("acapella"))
        self.reset_button.setText(t("reset"))
        self.update_ui.retranslate()
        self.player.retranslate(self.language)
        if self._done:
            self._refresh_numbers()
        key, kind, values = self._status
        self._set_status(key, kind, **values)
        self._update_controls()

    def _set_status(self, key: str, kind: str = "normal", **values):
        self._status = (key, kind, values)
        self.status_label.setText(tr(self.language, key, **values))
        self.status_label.setProperty("kind", kind)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _on_language_changed(self):
        self.language = self.language_box.currentData()
        self._settings.setValue("language", self.language)
        self._retranslate()

    # ---- theme and window state ---------------------------------------

    def _apply_theme(self, name: str):
        self.theme_name = name
        palette = PALETTES[name]
        self.setStyleSheet(stylesheet(palette))
        self.title_bar.apply_palette(palette)
        self.update_ui.apply_palette(palette)

    def _toggle_theme(self):
        self._apply_theme("light" if self.theme_name == "dark" else "dark")
        self._settings.setValue("theme", self.theme_name)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange and hasattr(self, "frame"):
            maximized = self.isMaximized()
            self.title_bar.set_maximized(maximized)
            self.frame.setProperty("maximized", maximized)
            self.frame.style().unpolish(self.frame)
            self.frame.style().polish(self.frame)
            self._retranslate()

    # ---- state --------------------------------------------------------

    @property
    def busy(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def _update_controls(self):
        self.progress.setVisible(self.busy)
        self.cancel_button.setVisible(self.busy)
        self.cancel_button.setEnabled(self.busy and not self._cancel.is_set())
        self.drop_zone.button.setEnabled(not self.busy)

    # ---- actions ------------------------------------------------------

    def _choose_file(self):
        filters = "Audio (" + " ".join(f"*{s}" for s in sorted(SUPPORTED_SUFFIXES)) + ")"
        path, _ = QFileDialog.getOpenFileName(self, tr(self.language, "choose_dialog_title"), "", filters)
        if path:
            self.start_processing(Path(path))

    def start_processing(self, song: Path, device: str | None = None):
        song = Path(song)
        if self.busy:
            self._set_status("busy", "error")
            return
        if song.suffix.lower() not in SUPPORTED_SUFFIXES:
            self._set_status("unsupported", "error")
            return

        self._song = song
        self._done = None
        self.results.hide()
        self.player.clear()
        self._cancel = threading.Event()
        # Remembered once a separation has worked, so the "downloading the model" notice never comes back,
        # even if the cache check cannot see where the model was stored. Read here: QSettings stays on this thread.
        model_known = self._settings.value("model_ready", False, type=bool)
        worker = ProcessWorker(song, self.output_base, device or self.device, self._cancel, model_known, self)
        worker.stage.connect(self._on_stage)
        worker.notice.connect(lambda: self._set_status("retry_notice"))
        worker.succeeded.connect(self._on_succeeded)
        worker.failed.connect(lambda error: self._finish("failed", "error", error=error))
        worker.cancelled.connect(lambda: self._finish("cancelled"))
        worker.gpu_out_of_memory.connect(self._on_gpu_out_of_memory)
        worker.ffmpeg_missing.connect(lambda: self._finish("ffmpeg_missing", "error"))
        worker.model_download_failed.connect(lambda: self._finish("model_download_failed", "error"))
        self._worker = worker
        self._set_status("separating")
        worker.start()
        self._update_controls()

    def _cancel_clicked(self):
        self._cancel.set()
        self._update_controls()

    def _on_stage(self, stage: str):
        self._set_status(STAGE_KEYS[stage])

    def _on_succeeded(self, done):
        self._done = done
        if not done.reused:
            self._settings.setValue("model_ready", True)
        self._reset_edits()
        self.karaoke_name.setText(done.instrumental.name)
        self.acapella_name.setText(done.vocals.name)
        self.results.show()
        self.player.set_tracks({
            "original": self._song,
            "karaoke": done.instrumental,
            "acapella": done.vocals,
        })
        self._finish("done")

    # ---- BPM and key the user can correct ------------------------------

    def _reset_edits(self):
        analysis = self._done.analysis
        self._bpm, self._key = analysis.bpm, analysis.key
        self._refresh_numbers()

    def _scale_bpm(self, factor: float):
        self._bpm *= factor
        self._refresh_numbers()

    def _on_key_changed(self):
        if self._done and self.key_box.currentIndex() >= 0:
            self._key = self.key_box.currentText()
            self._refresh_numbers()

    def _refresh_numbers(self):
        analysis = self._done.analysis
        t = lambda key, **v: tr(self.language, key, **v)
        bpm_edited = abs(self._bpm - analysis.bpm) > 1e-9
        key_edited = self._key != analysis.key

        self.bpm_value.setText(f"{self._bpm:.1f}")
        self.halve_button.setEnabled(self._bpm / 2 >= BPM_RANGE[0])
        self.double_button.setEnabled(self._bpm * 2 <= BPM_RANGE[1])
        self.key_box.blockSignals(True)
        self.key_box.setCurrentIndex(self.key_box.findText(self._key))  # -1 (blank) if none was found
        self.key_box.blockSignals(False)

        confidence = f"{analysis.key_confidence:.2f}"
        self.bpm_note.setText(t("detected", value=f"{analysis.bpm:.1f}") if bpm_edited else "")
        self.key_note.setText(
            t("detected", value=f"{analysis.key} ({confidence})") if key_edited
            else t("confidence", value=confidence)
        )
        self.reset_button.setVisible(bpm_edited or key_edited)

    def _on_gpu_out_of_memory(self):
        answer = QMessageBox.question(
            self, tr(self.language, "oom_title"), tr(self.language, "oom_body"),
        )
        self._worker.wait()
        if answer == QMessageBox.StandardButton.Yes and self._song:
            self.start_processing(self._song, device="cpu")
        else:
            self._finish("cancelled")

    def _finish(self, key: str, kind: str = "normal", **values):
        if self._worker is not None:
            self._worker.wait()
        self._set_status(key, kind, **values)
        self._update_controls()

    def _open_folder(self):
        if self._done:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._done.directory)))

    def closeEvent(self, event):
        QApplication.instance().removeEventFilter(self._resizer)
        self.update_ui.cancel()
        self.player.clear()
        if self.busy:
            self._cancel.set()
            self._worker.wait(15000)
        super().closeEvent(event)


