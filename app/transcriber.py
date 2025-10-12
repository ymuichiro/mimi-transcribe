from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import mlx.core as mx
from parakeet_mlx import AlignedResult, from_pretrained


@dataclass(slots=True)
class TranscriberConfig:
    model_id: str = "mlx-community/parakeet-tdt_ctc-0.6b-ja"
    use_fp32: bool = False
    local_attention: bool = False
    local_attention_context_size: int = 256
    cache_dir: Optional[Path] = None


class ParakeetModelManager:
    """Lazy-load and reuse the Parakeet model across threads."""

    _lock = threading.Lock()
    _model = None
    _loaded_config: Optional[TranscriberConfig] = None

    @classmethod
    def get_model(cls, config: TranscriberConfig):
        logger = logging.getLogger("parakeet.transcriber")
        with cls._lock:
            if cls._model is None or cls._loaded_config != config:
                logger.info(
                    "Loading Parakeet model: id=%s fp32=%s",
                    config.model_id,
                    config.use_fp32,
                )
                dtype = mx.float32 if config.use_fp32 else mx.bfloat16
                model = from_pretrained(
                    config.model_id, dtype=dtype, cache_dir=config.cache_dir
                )

                if config.local_attention:
                    logger.debug(
                        "Setting local attention: ctx=%d",
                        config.local_attention_context_size,
                    )
                    model.encoder.set_attention_model(
                        "rel_pos_local_attn",
                        (
                            config.local_attention_context_size,
                            config.local_attention_context_size,
                        ),
                    )

                cls._model = model
                cls._loaded_config = config
                logger.info("Model ready")
            else:
                logger.debug("Reusing cached model")
            return cls._model


def transcribe_audio(audio_path: Path, config: TranscriberConfig) -> AlignedResult:
    """Transcribe ``audio_path`` using the configured Parakeet model."""
    logger = logging.getLogger("parakeet.transcriber")
    logger.info("Transcription started: file=%s", audio_path)
    model = ParakeetModelManager.get_model(config)
    dtype = mx.float32 if config.use_fp32 else mx.bfloat16
    result = model.transcribe(audio_path, dtype=dtype)
    logger.info("Transcription finished: length=%d chars", len(result.text))
    return result
