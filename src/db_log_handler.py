"""Handler logging Python qui persiste les logs dans PostgreSQL."""

import logging


class DatabaseLogHandler(logging.Handler):
    """Envoie chaque log record dans la table bot_logs via Database.save_log()."""

    def __init__(self, db):
        super().__init__()
        self.db = db

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.db.save_log(record.levelname, msg)
        except Exception:
            pass
