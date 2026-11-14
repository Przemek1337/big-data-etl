import logging
import os
import sys

import colorama
from colorama import Fore, Style

LINE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LEVEL_COLORS = {
    logging.DEBUG: Fore.CYAN,
    logging.INFO: Fore.GREEN,
    logging.WARNING: Fore.YELLOW,
    logging.ERROR: Fore.RED,
    logging.CRITICAL: Style.BRIGHT + Fore.RED,
}
QUIET_LOGGERS = ("pymongo", "httpx", "httpcore")


class ColorFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__(LINE_FORMAT)

    def format(self, record: logging.LogRecord) -> str:
        line = super().format(record)
        if os.environ.get("NO_COLOR"):
            return line
        return f"{LEVEL_COLORS.get(record.levelno, '')}{line}{Style.RESET_ALL}"


def configure_logging(level: str) -> None:
    colorama.just_fix_windows_console()
    root = logging.getLogger()
    for existing in list(root.handlers):
        if isinstance(existing.formatter, ColorFormatter):
            root.removeHandler(existing)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColorFormatter())
    root.addHandler(handler)
    root.setLevel(level.upper())
    for name in QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
