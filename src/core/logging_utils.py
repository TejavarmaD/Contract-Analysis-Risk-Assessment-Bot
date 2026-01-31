"""Simple in-memory logging helper for Streamlit UI display.

Provides a list-backed logging.Handler and helper functions to configure logging
and retrieve recent logs for display in the app.
"""
import logging
from typing import List

_LOG_LINES: List[str] = []
_MAX_LINES = 200


class ListHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        _LOG_LINES.append(msg)
        # keep list bounded
        if len(_LOG_LINES) > _MAX_LINES:
            del _LOG_LINES[0 : len(_LOG_LINES) - _MAX_LINES]


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with the in-memory handler.

    Safe to call multiple times.
    """
    root = logging.getLogger()
    root.setLevel(level)
    # avoid adding duplicate handlers
    for h in list(root.handlers):
        if isinstance(h, ListHandler):
            return
    handler = ListHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", "%H:%M:%S")
    handler.setFormatter(formatter)
    root.addHandler(handler)


def get_logs() -> List[str]:
    return list(_LOG_LINES)


__all__ = ["setup_logging", "get_logs"]
