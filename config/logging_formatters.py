"""Custom logging formatters."""

from __future__ import annotations

import logging
import os
import sys


class ColorFormatter(logging.Formatter):
    """
    Human-friendly console line: ``HH:MM:SS LEVEL name:lineno message`` with
    ANSI colors when stderr is a TTY and NO_COLOR is unset (see no-color.org).
    """

    RESET = "\033[0m"
    DIM = "\033[2m"

    _LEVEL_COLORS: dict[int, str] = {
        logging.DEBUG: "\033[90m",
        logging.INFO: "\033[32m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[1;31m",
    }
    _NAME_COLOR = "\033[36m"

    def __init__(self, *args, datefmt: str = "%H:%M:%S", **kwargs) -> None:
        kwargs.setdefault("fmt", "%(message)s")
        super().__init__(*args, datefmt=datefmt, **kwargs)

    @staticmethod
    def _use_color() -> bool:
        return sys.stderr.isatty() and not os.environ.get("NO_COLOR")

    @staticmethod
    def _short_name(name: str) -> str:
        parts = name.split(".")
        if len(parts) > 2:
            return f"{parts[0]}.…{parts[-1]}"
        return name

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        ts = self.formatTime(record, self.datefmt)
        level_padded = f"{record.levelname:<8}"
        loc = f"{self._short_name(record.name)}:{record.lineno}"

        if self._use_color():
            dim_ts = f"{self.DIM}{ts}{self.RESET}"
            lc = self._LEVEL_COLORS.get(record.levelno, "")
            colored_level = f"{lc}{level_padded}{self.RESET}"
            colored_loc = f"{self._NAME_COLOR}{loc}{self.RESET}"
            line = f"{dim_ts} {colored_level} {colored_loc} {record.message}"
        else:
            line = f"{ts} {level_padded} {loc} {record.message}"

        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        elif record.exc_text:
            line += "\n" + record.exc_text

        if record.stack_info:
            line += "\n" + self.formatStack(record.stack_info)

        return line
