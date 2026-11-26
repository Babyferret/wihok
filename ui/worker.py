import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from core.audio import FfmpegMissing
from core.model import ModelDownloadFailed, is_model_cached
from core.pipeline import process_song
from core.separator import OutOfGpuMemory, SeparationCancelled


class ProcessWorker(QThread):
    """Runs one song through core off the GUI thread."""

    stage = Signal(str)
    notice = Signal()
    succeeded = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    gpu_out_of_memory = Signal()
    ffmpeg_missing = Signal()
    model_download_failed = Signal()

    def __init__(self, song: Path, base: Path, device: str, cancel: threading.Event,
                 model_known: bool = False, parent=None):
        super().__init__(parent)
        self._song, self._base, self._device, self._cancel = song, base, device, cancel
        self._model_known = model_known  # a separation already succeeded here, so the model is on this computer

    def run(self):
        try:
            done = process_song(
                self._song, self._base, self._device,
                cancel=self._cancel,
                on_stage=self.stage.emit,
                on_notice=lambda _message: self.notice.emit(),
                model_cached=lambda: self._model_known or is_model_cached(),
            )
        except SeparationCancelled:
            self.cancelled.emit()
        except OutOfGpuMemory:
            self.gpu_out_of_memory.emit()
        except FfmpegMissing:
            self.ffmpeg_missing.emit()
        except ModelDownloadFailed:
            self.model_download_failed.emit()
        except Exception as error:  # a corrupt file or a failed Demucs run: report it, don't crash the app
            self.failed.emit(str(error))
        else:
            self.succeeded.emit(done)
