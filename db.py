"""Compatibility module for Vercel/flat import environments."""

from app.db import (
    get_daily_devotionals,
    get_journal_entries,
    get_prayer_requests,
    save_daily_devotional,
    save_journal_entry,
    save_prayer_request,
)

__all__ = [
    "get_daily_devotionals",
    "get_journal_entries",
    "get_prayer_requests",
    "save_daily_devotional",
    "save_journal_entry",
    "save_prayer_request",
]
