"""Configuration du logging pour le bot de trading SMC/ICT."""

import os
import logging
from logging.handlers import TimedRotatingFileHandler


def setup_logging() -> logging.Logger:
    """Configure le logging avec rotation journalière et sortie console.

    Retourne le logger racine configuré avec :
    - Fichier logs/bot.log avec rotation journalière (30 jours)
    - Sortie console simultanée
    - Format : '2026-02-23 14:30:00 [INFO] message'
    """
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "bot.log")

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    if logger.handlers:
        logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    return logger
