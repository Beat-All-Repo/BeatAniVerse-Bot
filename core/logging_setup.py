"""
core/logging_setup.py
=====================
Centralised logging configuration for the bot.
Call setup_logging() once at startup.
"""
import os
import logging
import logging.handlers


def setup_logging() -> None:
    """Configure all loggers. Call once in main()."""
    os.makedirs("logs", exist_ok=True)

    _fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    _datefmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        format=_fmt,
        datefmt=_datefmt,
        level=logging.INFO,
        handlers=[
            logging.handlers.RotatingFileHandler(
                "logs/bot.log",
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            ),
            logging.StreamHandler(),
        ],
    )

    for name in ["httpx", "httpcore", "telegram", "apscheduler"]:
        logging.getLogger(name).setLevel(logging.WARNING)


# Named loggers — import from here instead of creating per-file
logger = logging.getLogger("bot")
db_logger = logging.getLogger("database")
api_logger = logging.getLogger("api")
broadcast_logger = logging.getLogger("broadcast")
error_logger = logging.getLogger("errors")
