"""Grace Daily app package."""

from importlib import import_module

try:
    from app.db import get_journal_entries, save_journal_entry, get_prayer_requests, save_prayer_request
except ImportError:  # pragma: no cover - fallback for flat deployment layouts
    from db import get_journal_entries, save_journal_entry, get_prayer_requests, save_prayer_request

__all__ = [
    "app",
    "get_journal_entries",
    "save_journal_entry",
    "get_prayer_requests",
    "save_prayer_request",
]


def __getattr__(name):
    if name == "app":
        return import_module("main").app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
