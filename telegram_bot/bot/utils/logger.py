import gzip
import logging
import os
import shutil
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional


class CompressingRotatingFileHandler(RotatingFileHandler):
    """
    A RotatingFileHandler that compresses each rotated log file with gzip
    to save disk space. Only the first-level rollover (.1) is compressed
    - older backups (.2, .3, ...) are already gzipped by previous cycles.
    """

    def doRollover(self):
        """
        Extend base rollover logic, then gzip the most recent backup.
        """
        super().doRollover()

        backup_file = f"{self.baseFilename}.1"
        if os.path.exists(backup_file) and not backup_file.endswith(".gz"):
            try:
                with open(backup_file, "rb") as src, gzip.open(f"{backup_file}.gz", "wb") as dst:
                    shutil.copyfileobj(src, dst)
                os.remove(backup_file)
            except Exception as exc:
                logging.getLogger(__name__).exception("Failed to gzip log file %s: %s", backup_file, exc)


def setup_logging(level: int = logging.INFO,
                  log_dir: Optional[str] = 'logs',
                  log_filename: str = "app.log",
                  max_bytes: int = 100 * 1024 * 1024,
                  backup_count: int = 0,
                  error_dir: Optional[str] = None,
                  error_log_filename: str = "error.log") -> logging.Logger:
    """
    Configure root logger with:
      • Console handler (stdout) for Docker visibility
      • Rotating file handler with gzip compression once file exceeds 1 MiB
    Environment variable LOG_DIR can override log directory.
    Returns root logger instance for further use.

    Parameters
    ----------
    level : int
        Logging level for the root logger.
    log_dir : Optional[str]
        Directory to store logs. Falls back to $LOG_DIR or ./logs.
    log_filename : str
        Name of the active log file.
    max_bytes : int
        Maximum size in bytes before rollover (default 1 MiB).
    backup_count : int
        Number of compressed backups to keep (0 = unlimited).
    """
    if log_dir is None:
        log_dir = os.getenv("LOG_DIR", "logs")

    env_backup_count = os.getenv("LOG_BACKUP_COUNT")
    if env_backup_count is not None and env_backup_count.isdigit():
        backup_count = int(env_backup_count)

    internal_backup_count = backup_count if backup_count > 0 else 1000000

    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_filename)

    file_handler = CompressingRotatingFileHandler(
        filename=log_path,
        maxBytes=max_bytes,
        backupCount=internal_backup_count,
        encoding="utf-8"
    )
    file_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    file_handler.setFormatter(file_format)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(file_format)

    if hasattr(console_handler.stream, 'reconfigure'):
        console_handler.stream.reconfigure(encoding='utf-8')
    else:

        import codecs
        console_handler.stream = codecs.getwriter('utf-8')(console_handler.stream.buffer)

    handlers = [file_handler, console_handler]

    if error_dir is None:
        error_dir = os.getenv("ERROR_DIR", "errors")
    if error_dir:
        os.makedirs(error_dir, exist_ok=True)
        error_log_path = os.path.join(error_dir, error_log_filename)
        error_file_handler = CompressingRotatingFileHandler(
            filename=error_log_path,
            maxBytes=max_bytes,
            backupCount=internal_backup_count,
            encoding="utf-8"
        )
        error_file_handler.setFormatter(file_format)
        error_file_handler.setLevel(logging.ERROR)
        handlers.append(error_file_handler)

    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True,
    )

    logging.captureWarnings(True)
    return logging.getLogger()
