from __future__ import annotations

import logging
import os
import pathlib
import sys
from datetime import datetime

from app.gui import run_app


def _setup_ffmpeg_path() -> None:
    """Add bundled ffmpeg to PATH when running in PyInstaller bundle."""
    if hasattr(sys, "_MEIPASS"):
        # Running in PyInstaller bundle
        bin_dir = pathlib.Path(sys._MEIPASS) / "bin"
        if bin_dir.exists():
            # Add bundled bin directory to PATH
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")


def _setup_logging() -> None:
    log_dir = pathlib.Path.home() / "Library" / "Logs" / "mimitranscribe"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = log_dir / f"session-{timestamp}.log"

    level_name = os.getenv("MIMITRANSCRIBE_LOG_LEVEL", "DEBUG")
    level = getattr(logging, level_name.upper(), logging.DEBUG)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )

    logging.getLogger("mimitranscribe").info("Logging initialized. file=%s", log_file)


def main() -> None:
    _setup_ffmpeg_path()
    _setup_logging()
    logger = logging.getLogger("mimitranscribe.main")
    logger.info("Launching GUI")
    exit_code = run_app()
    logger.info("GUI exited with code %s", exit_code)


if __name__ == "__main__":
    main()
