from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import mlx.core as mx
from huggingface_hub import hf_hub_download
from huggingface_hub.errors import (
    GatedRepoError,
    RepositoryNotFoundError,
    RevisionNotFoundError,
)
from parakeet_mlx import AlignedResult, from_pretrained  # type: ignore[import]

try:
    import mlx_whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False


# Model registry with model type information
MODEL_REGISTRY = {
    "mlx-community/parakeet-tdt_ctc-0.6b-ja": {
        "type": "parakeet",
        "name": "Parakeet-TDT 0.6B (日本語)",
        "description": "日本語音声認識に最適化されたモデル"
    },
    "mlx-community/whisper-large-v3-mlx": {
        "type": "whisper",
        "name": "Whisper Large V3",
        "description": "多言語対応の高精度音声認識モデル"
    },
    "mlx-community/whisper-large-v3-turbo-q4": {
        "type": "whisper",
        "name": "Whisper Large V3 Turbo (量子化)",
        "description": "高速で軽量な多言語音声認識モデル"
    },
}


@dataclass(slots=True)
class TranscriberConfig:
    model_id: str = "mlx-community/parakeet-tdt_ctc-0.6b-ja"
    use_fp32: bool = True
    local_attention: bool = True
    local_attention_context_size: int = 2048
    cache_dir: Optional[Path] = None
    chunk_duration: Optional[float] = 4.0
    chunk_overlap: float = 0.5
    
    def get_model_type(self) -> str:
        """Get the model type (parakeet, whisper, etc.)"""
        return MODEL_REGISTRY.get(self.model_id, {}).get("type", "parakeet")


class ModelLoadError(RuntimeError):
    """Raised when a Parakeet model cannot be downloaded or initialized."""


class ParakeetModelManager:
    """Lazy-load and reuse the Parakeet model across threads."""

    _lock = threading.Lock()
    _model = None
    _loaded_config: Optional[TranscriberConfig] = None

    @classmethod
    def get_model(cls, config: TranscriberConfig):
        logger = logging.getLogger("mimitranscribe.transcriber")
        with cls._lock:
            if cls._model is None or cls._loaded_config != config:
                logger.info(
                    "Loading Parakeet model: id=%s fp32=%s",
                    config.model_id,
                    config.use_fp32,
                )
                ensure_model_downloaded(config)
                dtype = mx.float32 if config.use_fp32 else mx.bfloat16
                try:
                    model = from_pretrained(
                        config.model_id, dtype=dtype, cache_dir=config.cache_dir
                    )
                except GatedRepoError as exc:
                    raise ModelLoadError(_format_auth_error(config.model_id)) from exc
                except (RepositoryNotFoundError, RevisionNotFoundError) as exc:
                    raise ModelLoadError(_format_repo_error(config.model_id)) from exc
                except FileNotFoundError as exc:
                    raise ModelLoadError(
                        _format_local_path_error(config.model_id)
                    ) from exc
                except Exception as exc:  # pragma: no cover - defensive
                    raise ModelLoadError(
                        _format_generic_error(config.model_id, str(exc))
                    ) from exc

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
    """Transcribe ``audio_path`` using the configured model."""
    logger = logging.getLogger("mimitranscribe.transcriber")
    logger.info("Transcription started: file=%s, model=%s", audio_path, config.model_id)
    
    model_type = config.get_model_type()
    logger.info("DEBUG: Model type detected: %s", model_type)
    logger.info("DEBUG: WHISPER_AVAILABLE: %s", WHISPER_AVAILABLE)
    
    if model_type == "whisper":
        if not WHISPER_AVAILABLE:
            raise ModelLoadError("Whisper モデルを使用するには mlx-whisper のインストールが必要です")
        logger.info("DEBUG: Calling _transcribe_with_whisper")
        return _transcribe_with_whisper(audio_path, config)
    else:
        logger.info("DEBUG: Calling _transcribe_with_parakeet")
        return _transcribe_with_parakeet(audio_path, config)


def _transcribe_with_parakeet(audio_path: Path, config: TranscriberConfig) -> AlignedResult:
    """Transcribe using Parakeet model."""
    logger = logging.getLogger("mimitranscribe.transcriber")
    model = ParakeetModelManager.get_model(config)
    dtype = mx.float32 if config.use_fp32 else mx.bfloat16
    if config.chunk_duration is not None and config.chunk_duration > 0:
        result = model.transcribe(
            audio_path,
            dtype=dtype,
            chunk_duration=float(config.chunk_duration),
            overlap_duration=float(max(config.chunk_overlap, 0.0)),
        )
    else:
        result = model.transcribe(audio_path, dtype=dtype)
    logger.info("Transcription finished: length=%d chars", len(result.text))
    return result


def _transcribe_with_whisper(audio_path: Path, config: TranscriberConfig) -> AlignedResult:
    """Transcribe using Whisper model."""
    logger = logging.getLogger("mimitranscribe.transcriber")
    
    logger.info("DEBUG: Starting Whisper transcription")
    logger.info("DEBUG: Model ID: %s", config.model_id)
    logger.info("DEBUG: Audio path: %s", audio_path)
    logger.info("DEBUG: Audio path exists: %s", audio_path.exists())
    
    try:
        # Use mlx_whisper.transcribe
        # Note: mlx_whisper handles dtype internally, no need to pass it
        logger.info("DEBUG: Calling mlx_whisper.transcribe...")
        result = mlx_whisper.transcribe(
            str(audio_path),
            path_or_hf_repo=config.model_id,
            verbose=True,  # Enable verbose output for debugging
            word_timestamps=False,
        )
        logger.info("DEBUG: mlx_whisper.transcribe returned successfully")
        logger.info("DEBUG: Result type: %s", type(result))
        logger.info("DEBUG: Result keys: %s", result.keys() if isinstance(result, dict) else "not a dict")
        
    except Exception as exc:
        logger.exception("DEBUG: Exception during mlx_whisper.transcribe")
        raise ModelLoadError(f"Whisper transcription failed: {str(exc)}") from exc
    
    # Convert whisper result to AlignedResult-like object
    # Whisper returns a dict with 'text' and 'segments'
    class WhisperResult:
        def __init__(self, text):
            self.text = text
    
    transcribed_text = result.get("text", "")
    logger.info("Transcription finished: length=%d chars", len(transcribed_text))
    logger.info("DEBUG: Returning WhisperResult with text: %s", transcribed_text[:100] if len(transcribed_text) > 100 else transcribed_text)
    return WhisperResult(transcribed_text)


def ensure_model_downloaded(config: TranscriberConfig) -> None:
    """Ensure model files are present locally, downloading them if needed."""
    model_id = config.model_id
    logger = logging.getLogger("mimitranscribe.transcriber")
    logger.info("Ensuring model assets are available: %s", model_id)
    
    model_type = config.get_model_type()
    
    # For Whisper models, trigger download by loading the model
    if model_type == "whisper":
        if not WHISPER_AVAILABLE:
            raise ModelLoadError("Whisper モデルを使用するには mlx-whisper のインストールが必要です")
        logger.info("DEBUG: Downloading Whisper model: %s", model_id)
        try:
            # Import load_model from mlx_whisper to trigger download
            from mlx_whisper.load_models import load_model
            logger.info("DEBUG: Calling load_model...")
            # Load the model to trigger download (dtype is handled internally by mlx_whisper)
            model = load_model(model_id)
            logger.info("DEBUG: Whisper model loaded successfully")
            logger.info("Whisper model downloaded and cached: %s", model_id)
        except Exception as exc:
            logger.exception("DEBUG: Failed to load Whisper model")
            raise ModelLoadError(f"Whisper モデルのダウンロードに失敗しました: {str(exc)}") from exc
        return

    # For Parakeet models, check local path first
    model_path = Path(model_id).expanduser()
    if model_path.exists():
        required = [model_path / "config.json", model_path / "model.safetensors"]
        missing = [path for path in required if not path.exists()]
        if missing:
            missing_names = ", ".join(path.name for path in missing)
            raise ModelLoadError(
                f"ローカルディレクトリ '{model_path}' に必要ファイルがありません: {missing_names}"
            )
        logger.debug("Using local model directory: %s", model_path)
        return

    try:
        hf_hub_download(
            model_id,
            "config.json",
            cache_dir=config.cache_dir,
            resume_download=True,
        )
        hf_hub_download(
            model_id,
            "model.safetensors",
            cache_dir=config.cache_dir,
            resume_download=True,
        )
    except GatedRepoError as exc:
        raise ModelLoadError(_format_auth_error(model_id)) from exc
    except (RepositoryNotFoundError, RevisionNotFoundError) as exc:
        raise ModelLoadError(_format_repo_error(model_id)) from exc
    except FileNotFoundError as exc:
        raise ModelLoadError(_format_local_path_error(model_id)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise ModelLoadError(_format_generic_error(model_id, str(exc))) from exc

    logger.info("Model assets downloaded: %s", model_id)


def _format_repo_error(model_id: str) -> str:
    return (
        f"モデル『{model_id}』にアクセスできませんでした。\n"
        "モデル名が正しいか確認し、必要に応じて公開モデルを選択してください。"
    )


def _format_auth_error(model_id: str) -> str:
    return (
        f"モデル『{model_id}』は Hugging Face の認証が必要です。\n"
        "ターミナルで `uv run huggingface-cli login` を実行するか、"
        "環境変数 HUGGINGFACEHUB_API_TOKEN を設定してから再試行してください。"
    )


def _format_generic_error(model_id: str, detail: str) -> str:
    return f"モデル『{model_id}』をダウンロードできませんでした。\n詳細: {detail}"


def _format_local_path_error(model_id: str) -> str:
    return (
        f"モデル『{model_id}』のローカルファイルが見つかりません。\n"
        "パスが正しいか、事前にダウンロードされているかを確認してください。"
    )
