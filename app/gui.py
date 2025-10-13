from __future__ import annotations

import logging
import tempfile
import threading
import traceback
from collections import deque
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from uuid import uuid4

import numpy as np
import sounddevice as sd  # type: ignore[import]
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import (
    QCloseEvent,
    QColor,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QProgressDialog,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .recorder import AudioRecorder
from .transcriber import (
    ModelLoadError,
    TranscriberConfig,
    ensure_model_downloaded,
    transcribe_audio,
)


class ModelPreloadThread(QThread):
    progress = Signal(int, int, str)
    failed = Signal(str, str)
    succeeded = Signal()

    def __init__(self, configs: list[TranscriberConfig], parent=None) -> None:
        super().__init__(parent)
        self.configs = configs
        self._logger = logging.getLogger("mimitranscribe.gui.preload")

    def run(self) -> None:  # noqa: D401 - Qt entry point
        total = len(self.configs)
        for index, config in enumerate(self.configs, start=1):
            if self.isInterruptionRequested():
                self._logger.info("Model preload interrupted")
                return
            waiting_message = (
                f"モデルを準備しています ({index}/{total})\n{config.model_id}"
            )
            self.progress.emit(index - 1, total, waiting_message)
            try:
                ensure_model_downloaded(config)
            except ModelLoadError as exc:
                self._logger.warning("Model preload failed: %s", exc)
                self.failed.emit(config.model_id, str(exc))
                return
            except Exception as exc:  # pragma: no cover - unexpected
                error_text = "".join(traceback.format_exception(exc))
                self._logger.exception("Unexpected error during preload")
                self.failed.emit(config.model_id, error_text)
                return

            done_message = (
                f"モデルの準備が完了しました ({index}/{total})\n{config.model_id}"
            )
            self.progress.emit(index, total, done_message)

        self.succeeded.emit()


class TranscriptionThread(QThread):
    completed = Signal(str)
    failed = Signal(str)

    def __init__(
        self, audio_path: Path, config: TranscriberConfig, parent=None
    ) -> None:
        super().__init__(parent)
        self.audio_path = audio_path
        self.config = config
        self._logger = logging.getLogger("mimitranscribe.gui.thread")

    def run(self) -> None:  # noqa: D401 - Qt entry point
        try:
            self._logger.info("Thread started: file=%s", self.audio_path)
            result = transcribe_audio(self.audio_path, self.config)
            self._logger.info("Thread completed successfully")
            self.completed.emit(result.text.strip())
        except ModelLoadError as exc:
            self._logger.warning("Model load failed: %s", exc)
            self.failed.emit(str(exc))
        except Exception as exc:  # pragma: no cover - GUI thread
            error_text = "".join(traceback.format_exception(exc))
            self._logger.exception("Transcription failed")
            self.failed.emit(error_text)


class WaveformWidget(QWidget):
    """Simple real-time waveform display for audio input."""

    def __init__(self, parent: Optional[QWidget] = None, buffer_samples: int = 4096):
        super().__init__(parent)
        self._buffer = np.zeros(buffer_samples, dtype=np.float32)
        self._lock = threading.Lock()
        self._active = False
        self._has_data = False
        self._wave_color = QColor("#3D8AF7")
        self._grid_color = QColor("#C9D8FB")
        self.setObjectName("waveformWidget")
        self.setMinimumHeight(120)
        self.setAutoFillBackground(False)

    def set_active(self, active: bool) -> None:
        if self._active == active:
            return
        self._active = active
        if not active:
            self.clear()
        self.update()

    def is_active(self) -> bool:
        return self._active

    def append_samples(self, samples: np.ndarray) -> None:
        if not self._active:
            return
        if samples.size == 0:
            return
        flattened = np.asarray(samples, dtype=np.float32).reshape(-1)
        with self._lock:
            if flattened.size >= self._buffer.size:
                self._buffer[:] = flattened[-self._buffer.size :]
            else:
                shift = flattened.size
                self._buffer[:-shift] = self._buffer[shift:]
                self._buffer[-shift:] = flattened
            self._has_data = True
        self.update()

    def clear(self) -> None:
        with self._lock:
            self._buffer.fill(0)
            self._has_data = False
        self.update()

    def paintEvent(self, event):  # noqa: D401 - Qt override
        painter = QPainter(self)
        rect = self.rect()
        painter.fillRect(rect, self.palette().color(self.backgroundRole()))

        mid_y = rect.center().y()
        grid_color = QColor(self._grid_color)
        grid_color.setAlpha(90)
        painter.setPen(QPen(grid_color, 1, Qt.PenStyle.DashLine))
        painter.drawLine(rect.left(), mid_y, rect.right(), mid_y)

        if not self._active or not self._has_data:
            placeholder = (
                "録音開始すると波形が表示されます"
                if not self._active
                else "音声の入力を待機しています…"
            )
            placeholder_color = self.palette().color(QPalette.ColorRole.Mid)
            painter.setPen(placeholder_color)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, placeholder)
            return

        with self._lock:
            data = self._buffer.copy()

        width = rect.width()
        height = rect.height()
        if width <= 2 or height <= 0 or data.size < 2:
            return

        max_val = float(np.max(np.abs(data)))
        if max_val <= 1e-6:
            normalized = data
        else:
            normalized = data / max_val

        indices = np.linspace(0, normalized.size - 1, num=width, dtype=np.int32)
        samples = normalized[indices]

        amplitude = height / 2.2
        origin_x = rect.left()
        origin_y = mid_y

        path = QPainterPath()
        path.moveTo(origin_x, origin_y - samples[0] * amplitude)
        for x_offset, sample in enumerate(samples[1:], start=1):
            path.lineTo(origin_x + x_offset, origin_y - sample * amplitude)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(self._wave_color, 1.5)
        painter.setPen(pen)
        painter.drawPath(path)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("MimiTranscribe")
        self.resize(900, 600)
        self.setMinimumSize(720, 480)

        self._logger = logging.getLogger("mimitranscribe.gui")
        self._logger.info("MainWindow initializing")
        self.recorder = AudioRecorder()
        self.transcriber_config = TranscriberConfig()
        self.waveform_widget = WaveformWidget(self)

        self._waveform_queue = deque(maxlen=24)
        self._waveform_queue_lock = threading.Lock()
        self._waveform_timer = QTimer(self)
        self._waveform_timer.setInterval(33)
        self._waveform_timer.timeout.connect(self._drain_waveform_queue)
        self._waveform_timer.start()
        self.recorder.set_frame_consumer(self._on_audio_frame)

        self._initialization_done = False
        self._preload_thread: Optional[ModelPreloadThread] = None
        self._init_dialog: Optional[QProgressDialog] = None

        self._recording_path: Optional[Path] = None
        self._transcription_thread: Optional[TranscriptionThread] = None
        self._record_start_time: Optional[datetime] = None

        self._record_timer = QTimer(self)
        self._record_timer.setInterval(1000)
        self._record_timer.timeout.connect(self._update_recording_duration)

        self.status_label = QLabel("マイク入力の準備ができています")
        self.status_label.setObjectName("statusLabel")

        self.elapsed_label = QLabel("録音時間: 00:00")
        self.elapsed_label.setObjectName("elapsedLabel")

        self.start_button = QPushButton("録音開始")
        self.start_button.clicked.connect(self.toggle_recording)
        self.start_button.setMinimumWidth(160)

        self.import_button = QPushButton("ファイル取り込み")
        self.import_button.clicked.connect(self.import_audio_file)
        self.import_button.setMinimumWidth(160)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setTextVisible(False)

        self.fp32_checkbox = QCheckBox("FP32 モード (メモリ多、精度高)")
        self.fp32_checkbox.setChecked(self.transcriber_config.use_fp32)

        self.local_attention_checkbox = QCheckBox("ローカルアテンションを有効化")
        self.local_attention_checkbox.setChecked(
            self.transcriber_config.local_attention
        )
        self.local_attention_checkbox.toggled.connect(self._on_local_attention_toggled)

        self.local_attention_spin = QSpinBox()
        self.local_attention_spin.setRange(32, 2048)
        self.local_attention_spin.setSingleStep(32)
        self.local_attention_spin.setValue(
            self.transcriber_config.local_attention_context_size
        )
        self.local_attention_spin.setEnabled(self.transcriber_config.local_attention)

        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)

        self.device_refresh_button = QToolButton()
        self.device_refresh_button.setText("再読込")
        self.device_refresh_button.clicked.connect(self._refresh_devices)

        self.copy_output_button = QToolButton()
        self.copy_output_button.setText("コピー")
        self.copy_output_button.clicked.connect(self._copy_output_to_clipboard)

        self.open_output_button = QToolButton()
        self.open_output_button.setText("保存…")
        self.open_output_button.clicked.connect(self._save_transcript_to_file)

        self.history_list = QListWidget()
        self.history_list.setObjectName("historyList")
        self.history_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.history_list.itemSelectionChanged.connect(
            self._on_history_selection_changed
        )
        self.history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(
            self._on_history_context_menu
        )

        self.clear_history_button = QToolButton()
        self.clear_history_button.setText("履歴をクリア")
        self.clear_history_button.clicked.connect(self.history_list.clear)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("ここに音声の書き起こし結果が表示されます")
        self.output_text.setObjectName("transcriptionOutput")

        self._build_layout()
        self._apply_styles()

        self._set_config_controls_enabled(False)
        self.start_button.setEnabled(False)
        self.import_button.setEnabled(False)
        self._prepare_startup()

        self._logger.info("Loading audio devices")
        self._refresh_devices()

        self.statusBar().setSizeGripEnabled(False)
        if self._initialization_done:
            self.statusBar().showMessage("準備完了")
        self._logger.info("MainWindow ready")

    # slots --------------------------------------------------------------------
    def toggle_recording(self) -> None:
        if not self._initialization_done:
            self._logger.info(
                "Recording requested before initialization completed; ignoring"
            )
            return
        if self.recorder.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def import_audio_file(self) -> None:
        """Import and transcribe an audio file."""
        if not self._initialization_done:
            self._logger.info(
                "File import requested before initialization completed; ignoring"
            )
            return

        if self.recorder.is_recording or (
            self._transcription_thread and self._transcription_thread.isRunning()
        ):
            self._logger.info("Cannot import file while recording or transcribing")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "音声ファイルを選択",
            str(Path.home()),
            "Audio Files (*.wav *.mp3 *.m4a *.flac *.ogg *.opus);;All Files (*)",
        )
        if not file_path:
            return

        audio_path = Path(file_path)
        if not audio_path.exists():
            self._show_error("ファイルが見つかりません", message=str(audio_path))
            return

        self._logger.info("Importing audio file: %s", audio_path)
        self._start_transcription(audio_path)

    def _start_recording(self) -> None:
        self._update_config_from_controls()
        self._clear_waveform_queue()
        self.waveform_widget.set_active(True)
        path = (
            Path(tempfile.gettempdir()) / f"mimitranscribe-recording-{uuid4().hex}.wav"
        )
        self._logger.info("Starting recording to %s", path)
        try:
            self.recorder.start(path)
        except Exception as exc:
            self._logger.exception("Failed to start recording")
            self._show_error("録音を開始できません", message=str(exc))
            self.waveform_widget.set_active(False)
            return

        self._recording_path = path
        self.status_label.setText("録音中…もう一度ボタンを押すと停止します")
        self.start_button.setText("録音停止")
        self.import_button.setEnabled(False)
        self.output_text.clear()
        self._set_config_controls_enabled(False)
        self.progress_bar.setVisible(False)
        self._record_start_time = datetime.now()
        self.elapsed_label.setText("録音時間: 00:00")
        self._record_timer.start()
        self.statusBar().showMessage("録音中", 3000)
        self.history_list.clearSelection()

    def _stop_recording(self) -> None:
        self._logger.info("Stopping recording")
        self.recorder.stop()
        self.start_button.setEnabled(False)
        self.status_label.setText("書き起こし中です。しばらくお待ちください…")
        self._record_timer.stop()
        self._record_start_time = None
        self.elapsed_label.setText("録音時間: --:--")
        self.progress_bar.setVisible(True)
        self.statusBar().showMessage("書き起こし中", 3000)

        if not self._recording_path:
            self._logger.warning("Recording path was None when stopping")
            self._reset_ui()
            return

        self._start_transcription(self._recording_path, is_temporary=True)

    def _start_transcription(
        self, audio_path: Path, is_temporary: bool = False
    ) -> None:
        """Start transcription of an audio file.
        
        Args:
            audio_path: Path to the audio file to transcribe
            is_temporary: If True, delete the file after transcription
        """
        self.output_text.clear()
        self.history_list.clearSelection()
        self.start_button.setEnabled(False)
        self.import_button.setEnabled(False)
        self.status_label.setText("書き起こし中です。しばらくお待ちください…")
        self.progress_bar.setVisible(True)
        self.statusBar().showMessage("書き起こし中", 3000)
        self._set_config_controls_enabled(False)

        self._update_config_from_controls()
        config_copy = replace(self.transcriber_config)
        thread = TranscriptionThread(audio_path, config_copy, self)
        thread.completed.connect(self._on_transcription_completed)
        thread.failed.connect(self._on_transcription_failed)
        if is_temporary:
            thread.finished.connect(lambda: self._cleanup_thread(audio_path))
        else:
            thread.finished.connect(lambda: self._cleanup_thread(None))

        self._transcription_thread = thread
        self._logger.info("Transcription thread starting for: %s", audio_path)
        thread.start()

    def _on_transcription_completed(self, text: str) -> None:
        self.output_text.setPlainText(text)
        self.status_label.setText("書き起こしが完了しました")
        self.progress_bar.setVisible(False)
        self.elapsed_label.setText("録音時間: 00:00")
        self.statusBar().showMessage("書き起こしが完了しました", 4000)
        self._append_history(text)
        self._logger.info("Transcription completed. Text length=%d", len(text))

    def _on_transcription_failed(self, error_text: str) -> None:
        self.progress_bar.setVisible(False)
        self.elapsed_label.setText("録音時間: 00:00")
        self.statusBar().showMessage("書き起こしでエラーが発生しました", 5000)

        if error_text.strip().startswith("Traceback"):
            self._show_error(
                "書き起こしでエラーが発生しました",
                message="処理中に予期しないエラーが発生しました。詳細を確認してください。",
                details=error_text,
            )
        else:
            self._show_error("書き起こしでエラーが発生しました", message=error_text)

        self._logger.error("Transcription failed. Details shown to user")

    def _cleanup_thread(self, temp_file: Optional[Path] = None) -> None:
        self._reset_ui()
        # Clean up temporary recording file if provided
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
                self._logger.debug("Temporary file deleted: %s", temp_file)
            except OSError:
                self._logger.warning("Failed to delete temp file: %s", temp_file)
        self._recording_path = None
        self._transcription_thread = None

    def _reset_ui(self) -> None:
        self.start_button.setEnabled(True)
        self.start_button.setText("録音開始")
        self.import_button.setEnabled(True)
        if not self.recorder.is_recording:
            self.status_label.setText("マイク入力の準備ができています")
        self.progress_bar.setVisible(False)
        self.elapsed_label.setText("録音時間: 00:00")
        self._set_config_controls_enabled(True)
        self.waveform_widget.set_active(False)
        self._clear_waveform_queue()
        self._logger.debug("UI reset")

    def _on_audio_frame(self, frame: np.ndarray) -> None:
        with self._waveform_queue_lock:
            if len(self._waveform_queue) == self._waveform_queue.maxlen:
                self._waveform_queue.popleft()
            self._waveform_queue.append(frame)

    def _drain_waveform_queue(self) -> None:
        if not self.waveform_widget.is_active():
            self._clear_waveform_queue()
            return

        frames: list[np.ndarray] = []
        with self._waveform_queue_lock:
            while self._waveform_queue:
                frames.append(self._waveform_queue.popleft())

        if frames:
            concatenated = np.concatenate(frames)
            self.waveform_widget.append_samples(concatenated)

    def _clear_waveform_queue(self) -> None:
        with self._waveform_queue_lock:
            self._waveform_queue.clear()

    def _show_error(
        self,
        title: str,
        *,
        message: Optional[str] = None,
        details: Optional[str] = None,
    ) -> None:
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText(message or title)
        if details:
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
        if self._preload_thread and self._preload_thread.isRunning():
            self._logger.info("Waiting for preload thread to finish")
            self._preload_thread.requestInterruption()
            self._preload_thread.wait(1000)
        if self._record_timer.isActive():
            self._record_timer.stop()
        if self._waveform_timer.isActive():
            self._waveform_timer.stop()
        super().closeEvent(event)

    # ui helpers --------------------------------------------------------------
    def _build_layout(self) -> None:
        container = QWidget(self)
        root_layout = QVBoxLayout(container)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        header_layout.addWidget(self.start_button)
        header_layout.addWidget(self.import_button)

        status_container = QVBoxLayout()
        status_container.setSpacing(4)
        status_container.addWidget(self.status_label)
        status_container.addWidget(self.elapsed_label)

        status_widget = QWidget()
        status_widget.setLayout(status_container)
        header_layout.addWidget(status_widget, stretch=1)
        header_layout.addWidget(self.progress_bar)

        root_layout.addLayout(header_layout)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        root_layout.addWidget(separator)

        config_group = QGroupBox("録音とモデル設定")
        config_layout = QFormLayout()
        config_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )
        config_layout.addRow("マイクデバイス", self._build_device_selector())
        config_layout.addRow("精度設定", self.fp32_checkbox)
        config_layout.addRow("局所アテンション", self.local_attention_checkbox)
        config_layout.addRow("コンテキスト長", self.local_attention_spin)
        config_group.setLayout(config_layout)
        root_layout.addWidget(config_group)

        waveform_group = QGroupBox("リアルタイム波形")
        waveform_layout = QVBoxLayout()
        waveform_layout.setContentsMargins(8, 8, 8, 8)
        waveform_layout.setSpacing(8)
        waveform_layout.addWidget(self.waveform_widget)
        waveform_group.setLayout(waveform_layout)
        root_layout.addWidget(waveform_group)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        history_panel = QWidget()
        history_layout = QVBoxLayout(history_panel)
        history_layout.setContentsMargins(0, 0, 0, 0)
        history_layout.setSpacing(8)

        history_header = QHBoxLayout()
        history_header.setSpacing(8)
        history_header.addWidget(QLabel("書き起こし履歴"))
        history_header.addStretch(1)
        history_header.addWidget(self.clear_history_button)

        history_layout.addLayout(history_header)
        history_layout.addWidget(self.history_list)
        splitter.addWidget(history_panel)

        transcript_panel = QWidget()
        transcript_layout = QVBoxLayout(transcript_panel)
        transcript_layout.setContentsMargins(0, 0, 0, 0)
        transcript_layout.setSpacing(8)

        transcript_header = QHBoxLayout()
        transcript_header.setSpacing(8)
        transcript_header.addWidget(QLabel("書き起こし結果"))
        transcript_header.addStretch(1)
        transcript_header.addWidget(self.copy_output_button)
        transcript_header.addWidget(self.open_output_button)

        transcript_layout.addLayout(transcript_header)
        transcript_layout.addWidget(self.output_text)
        splitter.addWidget(transcript_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        root_layout.addWidget(splitter, stretch=1)

        container.setLayout(root_layout)
        self.setCentralWidget(container)

    def _build_device_selector(self) -> QWidget:
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.device_combo, stretch=1)
        layout.addWidget(self.device_refresh_button)
        return wrapper

    def _prepare_startup(self) -> None:
        configs = [replace(self.transcriber_config)]
        if not configs:
            self._logger.info("No models to preload; enabling controls immediately")
            self._finalize_initialization()
            return

        self._logger.info("Preparing default model at startup")
        self.status_label.setText("必要なモデルを準備しています…")
        self.statusBar().showMessage("モデルを準備しています…")

        dialog = QProgressDialog("モデルを準備しています…", "", 0, len(configs), self)
        dialog.setWindowTitle("初期化中")
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        dialog.setCancelButton(None)
        dialog.setMinimumDuration(0)
        dialog.setAutoClose(False)
        dialog.setAutoReset(False)
        dialog.setValue(0)
        dialog.show()
        self._init_dialog = dialog

        thread = ModelPreloadThread(configs, self)
        thread.progress.connect(self._on_preload_progress)
        thread.succeeded.connect(self._on_preload_succeeded)
        thread.failed.connect(self._on_preload_failed)
        thread.finished.connect(self._clear_preload_thread)
        self._preload_thread = thread
        thread.start()

    def _on_preload_progress(self, current: int, total: int, message: str) -> None:
        dialog = self._init_dialog
        if dialog is None:
            return
        dialog.setMaximum(total)
        dialog.setValue(current)
        dialog.setLabelText(message)

    def _on_preload_succeeded(self) -> None:
        self._logger.info("Model preload finished successfully")
        self._cleanup_preload_dialog()
        self._finalize_initialization()

    def _on_preload_failed(self, model_id: str, error_text: str) -> None:
        self._cleanup_preload_dialog()
        self._logger.error(
            "Model preload failed for %s: %s", model_id, error_text.strip()
        )
        message = (
            "起動時にモデルのダウンロードに失敗しました。\n"
            "モデル ID: {model_id}\n詳細: {detail}"
        ).format(model_id=model_id, detail=error_text.strip())
        self._show_error("モデルを初期化できません", message=message)
        self._finalize_initialization(
            status_text="モデルの準備でエラーが発生しました",
            bar_message="モデルの準備でエラーが発生しました",
        )

    def _finalize_initialization(
        self,
        *,
        status_text: Optional[str] = None,
        bar_message: Optional[str] = None,
    ) -> None:
        self._initialization_done = True
        self._cleanup_preload_dialog()
        self._set_config_controls_enabled(True)
        self.start_button.setEnabled(True)
        self.import_button.setEnabled(True)
        if status_text is None:
            status_text = "マイク入力の準備ができています"
        if bar_message is None:
            bar_message = "準備完了"
        self.status_label.setText(status_text)
        self.statusBar().showMessage(bar_message, 4000)

    def _cleanup_preload_dialog(self) -> None:
        if self._init_dialog is None:
            return
        self._init_dialog.hide()
        self._init_dialog.deleteLater()
        self._init_dialog = None

    def _clear_preload_thread(self) -> None:
        self._preload_thread = None

    def _apply_styles(self) -> None:
        self.status_label.setStyleSheet("font-weight: 600")
        self.elapsed_label.setStyleSheet("color: #555")
        self.history_list.setStyleSheet(
            "\n".join(
                (
                    "QListWidget { background: #fbfbfb; border: 1px solid #e0e0e0; }",
                    "QListWidget::item { color: #1a1a1a; padding: 4px 6px; }",
                    "QListWidget::item:selected {"
                    " color: #ffffff;"
                    " background: #2f6feb;"
                    " }",
                )
            )
        )
        self.waveform_widget.setStyleSheet(
            "#waveformWidget {"
            " background: #f7f9fc;"
            " border: 1px solid #d0d7de;"
            " border-radius: 8px;"
            " }"
        )

    def _set_config_controls_enabled(self, enabled: bool) -> None:
        for widget in (
            self.device_combo,
            self.device_refresh_button,
            self.fp32_checkbox,
            self.local_attention_checkbox,
            self.local_attention_spin,
        ):
            widget.setEnabled(enabled)

    def _on_local_attention_toggled(self, checked: bool) -> None:
        self.local_attention_spin.setEnabled(checked)

    def _update_config_from_controls(self) -> None:
        self.transcriber_config = replace(
            self.transcriber_config,
            use_fp32=self.fp32_checkbox.isChecked(),
            local_attention=self.local_attention_checkbox.isChecked(),
            local_attention_context_size=self.local_attention_spin.value(),
        )

    def _on_device_changed(self, index: int) -> None:
        device = self.device_combo.itemData(index, Qt.ItemDataRole.UserRole)
        self.recorder.device = device
        self._logger.info("Audio device selected: %s", device)

    def _refresh_devices(self) -> None:
        self._logger.info("Refreshing audio devices")
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        self.device_combo.addItem("システム既定", None)
        try:
            devices = sd.query_devices()
        except Exception as exc:  # pragma: no cover - system dependent
            self._logger.exception("Failed to query audio devices")
            self.device_combo.addItem("取得に失敗しました", None)
            self.device_combo.setEnabled(False)
            self._show_error("オーディオデバイスを取得できません", message=str(exc))
            self.device_combo.blockSignals(False)
            return

        self.device_combo.setEnabled(True)
        for index, device in enumerate(devices):
            if device.get("max_input_channels", 0) <= 0:
                continue
            name = device.get("name", f"Device {index}")
            label = f"{index}: {name} ({device.get('max_input_channels')}ch)"
            self.device_combo.addItem(label, index)

        default_device = sd.default.device
        default_index: Optional[int] = None
        if isinstance(default_device, (list, tuple)) and default_device:
            default_index = default_device[0] if default_device[0] is not None else None
        elif isinstance(default_device, int) and default_device >= 0:
            default_index = default_device

        if default_index is not None:
            combo_index = self.device_combo.findData(
                default_index, Qt.ItemDataRole.UserRole
            )
            if combo_index != -1:
                self.device_combo.setCurrentIndex(combo_index)

        self.device_combo.blockSignals(False)
        current_index = self.device_combo.currentIndex()
        if current_index >= 0:
            self._on_device_changed(current_index)

    def _update_recording_duration(self) -> None:
        if not self._record_start_time:
            return
        elapsed = datetime.now() - self._record_start_time
        elapsed = max(elapsed, timedelta())
        minutes, seconds = divmod(int(elapsed.total_seconds()), 60)
        self.elapsed_label.setText(f"録音時間: {minutes:02}:{seconds:02}")

    def _append_history(self, text: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        summary = f"{timestamp} 文字数: {len(text)}"
        item = QListWidgetItem(summary)
        item.setData(Qt.ItemDataRole.UserRole, text)
        self.history_list.insertItem(0, item)
        self.history_list.setCurrentItem(item)

    def _on_history_selection_changed(self) -> None:
        current = self.history_list.currentItem()
        if current is None:
            return
        text = current.data(Qt.ItemDataRole.UserRole)
        if isinstance(text, str):
            self.output_text.setPlainText(text)

    def _on_history_context_menu(self, position) -> None:
        item = self.history_list.itemAt(position)
        if item is None:
            return
        menu = QMenu(self)
        copy_action = menu.addAction("この結果をコピー")
        delete_action = menu.addAction("履歴から削除")
        chosen = menu.exec(self.history_list.mapToGlobal(position))
        if chosen == copy_action:
            self._copy_text(item.data(Qt.ItemDataRole.UserRole))
        elif chosen == delete_action:
            row = self.history_list.row(item)
            self.history_list.takeItem(row)

    def _copy_output_to_clipboard(self) -> None:
        text = self.output_text.toPlainText()
        self._copy_text(text)

    def _copy_text(self, text: Optional[str]) -> None:
        if not text:
            return
        QApplication.clipboard().setText(text)
        self.statusBar().showMessage("書き起こし結果をコピーしました", 3000)

    def _save_transcript_to_file(self) -> None:
        text = self.output_text.toPlainText()
        if not text:
            self._show_error("保存できません", message="書き起こし結果がありません")
            return
        default_path = Path.home() / "Desktop" / "transcript.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "書き起こし結果を保存",
            str(default_path),
            "Text Files (*.txt);;All Files (*)",
        )
        if not file_path:
            return
        try:
            Path(file_path).write_text(text, encoding="utf-8")
        except OSError as exc:
            self._show_error("保存に失敗しました", message=str(exc))
            return
        self.statusBar().showMessage("書き起こし結果を保存しました", 4000)


def run_app() -> int:
    logger = logging.getLogger("mimitranscribe.gui")
    logger.info("Creating QApplication")
    app = QApplication.instance() or QApplication([])
    logger.info("QApplication created: %s", app)
    window = MainWindow()
    logger.info("Showing main window")
    window.show()
    result = app.exec()
    logger.info("Qt event loop exited: code=%s", result)
    return result
