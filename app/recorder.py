from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import sounddevice as sd
import soundfile as sf


class AudioRecorder:
    """Simple audio recorder that writes microphone input to a WAV file."""

    def __init__(
        self,
        *,
        samplerate: int = 16_000,
        channels: int = 1,
        subtype: str = "PCM_16",
        device: Optional[int | str] = None,
        frame_consumer: Optional[Callable[[np.ndarray], None]] = None,
    ) -> None:
        self.samplerate = samplerate
        self.channels = channels
        self.subtype = subtype
        self.device = device
        self._frame_consumer = frame_consumer

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._is_recording = False
        self._lock = threading.Lock()
        self._logger = logging.getLogger("mimitranscribe.recorder")

    def set_frame_consumer(
        self, consumer: Optional[Callable[[np.ndarray], None]]
    ) -> None:
        """Set a callable that receives raw audio frames during recording."""

        self._frame_consumer = consumer

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._is_recording

    def start(self, output_path: Path) -> None:
        with self._lock:
            if self._is_recording:
                raise RuntimeError("Recorder is already running")
            self._is_recording = True

        self._logger.debug(
            "Starting recording: path=%s samplerate=%d channels=%d subtype=%s device=%s",
            output_path,
            self.samplerate,
            self.channels,
            self.subtype,
            self.device,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._record_loop, args=(output_path,), daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        with self._lock:
            if not self._is_recording:
                return
            self._is_recording = False

        self._logger.debug("Stop requested")
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None
        self._logger.debug("Recorder thread joined")

    # internal -----------------------------------------------------------------
    def _record_loop(self, output_path: Path) -> None:
        self._logger.info("Recorder thread started")
        try:
            with sf.SoundFile(
                output_path,
                mode="w",
                samplerate=self.samplerate,
                channels=self.channels,
                subtype=self.subtype,
            ) as wav_file:
                with sd.InputStream(
                    samplerate=self.samplerate,
                    channels=self.channels,
                    dtype="float32",
                    device=self.device,
                    callback=lambda indata, frames, time, status: self._callback(
                        indata, status, wav_file
                    ),
                ):
                    while not self._stop_event.wait(0.1):
                        pass
                self._logger.info("Input stream closed normally")
        finally:
            with self._lock:
                self._is_recording = False
            self._logger.info("Recorder thread finished")

    def _callback(
        self, indata: np.ndarray, status: sd.CallbackFlags, wav_file: sf.SoundFile
    ) -> None:
        if status:
            # The status object stringifies useful debug info, but we avoid raising.
            self._logger.warning("Input stream status: %s", status)
        wav_file.write(indata)
        if self._frame_consumer is not None:
            try:
                self._frame_consumer(indata.copy())
            except Exception:  # pragma: no cover - defensive logging
                self._logger.exception("Frame consumer raised an exception")
        if self._stop_event.is_set():
            self._logger.debug("Stop event detected inside callback")
            raise sd.CallbackStop()
