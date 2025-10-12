from __future__ import annotations

import logging
import os
import pathlib
import sys
from datetime import datetime

from app.gui import run_app


def _setup_logging() -> None:
    log_dir = pathlib.Path.home() / "Library" / "Logs" / "parakeet-tdt-study"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = log_dir / f"session-{timestamp}.log"

    level_name = os.getenv("PARAKEET_LOG_LEVEL", "DEBUG")
    level = getattr(logging, level_name.upper(), logging.DEBUG)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )

    logging.getLogger("parakeet").info("Logging initialized. file=%s", log_file)


def main() -> None:
    _setup_logging()
    logger = logging.getLogger("parakeet.main")
    logger.info("Launching GUI")
    exit_code = run_app()
    logger.info("GUI exited with code %s", exit_code)


if __name__ == "__main__":
    main()
