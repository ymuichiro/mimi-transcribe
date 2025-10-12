from __future__ import annotations

import logging
import tempfile
import traceback
from dataclasses import replace
from pathlib import Path
from typing import Optional
from uuid import uuid4

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .recorder import AudioRecorder
from .transcriber import TranscriberConfig, transcribe_audio


class TranscriptionThread(QThread):
    completed = Signal(str)
    failed = Signal(str)

    def __init__(
        self, audio_path: Path, config: TranscriberConfig, parent=None
    ) -> None:
        super().__init__(parent)
        self.audio_path = audio_path
        self.config = config
        self._logger = logging.getLogger("parakeet.gui.thread")

    def run(self) -> None:  # noqa: D401 - Qt entry point
        try:
            self._logger.info("Thread started: file=%s", self.audio_path)
            result = transcribe_audio(self.audio_path, self.config)
            self._logger.info("Thread completed successfully")
            self.completed.emit(result.text.strip())
        except Exception as exc:  # pragma: no cover - GUI thread
            error_text = "".join(traceback.format_exception(exc))
            self._logger.exception("Transcription failed")
            self.failed.emit(error_text)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Parakeet TDT Transcriber")
        self.resize(480, 360)

        self._logger = logging.getLogger("parakeet.gui")
        self._logger.info("MainWindow initializing")
        self.recorder = AudioRecorder()
        self.transcriber_config = TranscriberConfig()

        self._recording_path: Optional[Path] = None
        self._transcription_thread: Optional[TranscriptionThread] = None

        self.status_label = QLabel("マイク入力の準備ができています")

        self.start_button = QPushButton("録音開始")
        self.start_button.clicked.connect(self.toggle_recording)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("ここに音声の書き起こし結果が表示されます")

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.start_button)
        layout.addWidget(self.output_text)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self._logger.info("MainWindow ready")

    # slots --------------------------------------------------------------------
    def toggle_recording(self) -> None:
        if self.recorder.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        path = Path(tempfile.gettempdir()) / f"parakeet-recording-{uuid4().hex}.wav"
        self._logger.info("Starting recording to %s", path)
        try:
            self.recorder.start(path)
        except Exception as exc:
            self._logger.exception("Failed to start recording")
            self._show_error("録音を開始できません", str(exc))
            return

        self._recording_path = path
        self.status_label.setText("録音中…もう一度ボタンを押すと停止します")
        self.start_button.setText("録音停止")
        self.output_text.clear()

    def _stop_recording(self) -> None:
        self._logger.info("Stopping recording")
        self.recorder.stop()
        self.start_button.setEnabled(False)
        self.status_label.setText("書き起こし中です。しばらくお待ちください…")

        if not self._recording_path:
            self._logger.warning("Recording path was None when stopping")
            self._reset_ui()
            return

        config_copy = replace(self.transcriber_config)
        thread = TranscriptionThread(self._recording_path, config_copy, self)
        thread.completed.connect(self._on_transcription_completed)
        thread.failed.connect(self._on_transcription_failed)
        thread.finished.connect(self._cleanup_thread)

        self._transcription_thread = thread
        self._logger.info("Transcription thread starting")
        thread.start()

    def _on_transcription_completed(self, text: str) -> None:
        self.output_text.setPlainText(text)
        self.status_label.setText("書き起こしが完了しました")
        self._logger.info("Transcription completed. Text length=%d", len(text))

    def _on_transcription_failed(self, error_text: str) -> None:
        self._show_error("書き起こしでエラーが発生しました", error_text)
        self._logger.error("Transcription failed. Details shown to user")

    def _cleanup_thread(self) -> None:
        self._reset_ui()
        if self._recording_path and self._recording_path.exists():
            try:
                self._recording_path.unlink()
                self._logger.debug("Temporary file deleted: %s", self._recording_path)
            except OSError:
                self._logger.warning(
                    "Failed to delete temp file: %s", self._recording_path
                )
                pass
        self._recording_path = None
        self._transcription_thread = None

    def _reset_ui(self) -> None:
        self.start_button.setEnabled(True)
        self.start_button.setText("録音開始")
        if not self.recorder.is_recording:
            self.status_label.setText("マイク入力の準備ができています")
        self._logger.debug("UI reset")

    def _show_error(self, title: str, details: str) -> None:
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText(title)
        msg.setDetailedText(details)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt override
        if self.recorder.is_recording:
            self._logger.info("Window closed while recording; stopping recorder")
            self.recorder.stop()
        if self._transcription_thread and self._transcription_thread.isRunning():
            self._logger.info("Waiting for transcription thread to finish")
            self._transcription_thread.wait(1000)
        super().closeEvent(event)


def run_app() -> int:
    logger = logging.getLogger("parakeet.gui")
    logger.info("Creating QApplication")
    app = QApplication.instance() or QApplication([])
    logger.info("QApplication created: %s", app)
    window = MainWindow()
    logger.info("Showing main window")
    window.show()
    result = app.exec()
    logger.info("Qt event loop exited: code=%s", result)
    return result
