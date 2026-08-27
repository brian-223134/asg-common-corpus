from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

from common_corpus.config import PROJECT_ROOT


def setup_logging(name: str, log_dir: Path | None = None) -> Path:
    """Log to both stderr and logs/<name>_<timestamp>.log. Returns the log path."""
    log_dir = log_dir or PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"{name}_{datetime.now():%Y%m%d_%H%M%S}.log"
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in (logging.FileHandler(path), logging.StreamHandler(sys.stderr)):
        h.setFormatter(fmt)
        root.addHandler(h)
    return path
