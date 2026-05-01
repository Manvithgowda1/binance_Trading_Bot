"""
logging_config.py — Structured logging setup for the trading bot.
Logs are written to both console (INFO+) and a rotating log file (DEBUG+).
"""

import logging
import logging.handlers
import os
from pathlib import Path


LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"

_CONFIGURED = False


def setup_logging(log_level: str = "DEBUG") -> logging.Logger:
    """
    Configure root logger with:
    - Console handler  : INFO and above, human-readable
    - File handler     : DEBUG and above, timestamped, rotating (5 MB × 3 backups)
    """
    global _CONFIGURED
    if _CONFIGURED:
        return logging.getLogger("trading_bot")

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("trading_bot")
    root.setLevel(logging.DEBUG)

    # ── Console handler ───────────────────────────────────────────────────────
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(
        logging.Formatter("%(levelname)-8s %(message)s")
    )

    # ── Rotating file handler ─────────────────────────────────────────────────
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root.addHandler(console)
    root.addHandler(file_handler)
    _CONFIGURED = True
    return root


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the 'trading_bot' namespace."""
    setup_logging()
    return logging.getLogger(f"trading_bot.{name}")
