"""A slim card at the top of the window that exists only while there is something to say about updates:
a new version, a download in progress, or a problem. Otherwise it is hidden, so the window stays as it was."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout


class UpdateBar(QFrame):
    update_clicked = Signal()
    later_clicked = Signal()
    cancel_clicked = Signal()
    dismissed = Signal()
    notes_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("update-bar")

        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.RichText)
        self.label.linkActivated.connect(lambda _href: self.notes_clicked.emit())

        self.update_button = QPushButton()
        self.later_button = QPushButton()
        self.later_button.setObjectName("secondary")
        self.cancel_button = QPushButton()
        self.cancel_button.setObjectName("secondary")
        self.ok_button = QPushButton()
        self.ok_button.setObjectName("secondary")
        for button in (self.update_button, self.later_button, self.cancel_button, self.ok_button):
            button.setFocusPolicy(Qt.TabFocus)  # a mouse click must not leave a focus ring (see MainWindow)
        self.update_button.clicked.connect(self.update_clicked)
        self.later_button.clicked.connect(self.later_clicked)
        self.cancel_button.clicked.connect(self.cancel_clicked)
        self.ok_button.clicked.connect(self.dismissed)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self.label, 1)
        for button in (self.later_button, self.update_button, self.cancel_button, self.ok_button):
            row.addWidget(button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        layout.addLayout(row)
        layout.addWidget(self.progress)
        self.hide()

    # ---- the things the bar can say ---------------------------------------

    def _show(self, text: str, *, buttons=(), progress: int | None = None, indeterminate: bool = False, error: bool = False):
        self.label.setText(text)
        self.label.setProperty("kind", "error" if error else "normal")
        self.label.style().unpolish(self.label)
        self.label.style().polish(self.label)
        for button in (self.later_button, self.update_button, self.cancel_button, self.ok_button):
            button.setVisible(button in buttons)
        self.progress.setVisible(progress is not None or indeterminate)
        if indeterminate:
            self.progress.setRange(0, 0)
        elif progress is not None:
            self.progress.setRange(0, 100)
            self.progress.setValue(progress)
        self.show()

    def available(self, text: str):
        self._show(text, buttons=(self.later_button, self.update_button))

    def downloading(self, text: str, percent: int):
        self._show(text, buttons=(self.cancel_button,), progress=percent)

    def installing(self, text: str):
        self._show(text, indeterminate=True)

    def message(self, text: str, error: bool = False):
        self._show(text, buttons=(self.ok_button,), error=error)
