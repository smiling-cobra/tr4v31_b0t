"""IANA timezone lookup: exact match, fuzzy substring search, and coordinate detection.

Pure — no telegram imports, no service calls. Testable without an Update.
"""
from zoneinfo import available_timezones

from timezonefinder import TimezoneFinder

_tf = TimezoneFinder()
_ALL_TIMEZONES = sorted(available_timezones())


def detect_timezone(lat: float, lng: float) -> str | None:
    """The IANA timezone name at a coordinate, or None if it cannot be resolved."""
    return _tf.timezone_at(lat=lat, lng=lng)


def search_timezones(query: str) -> list:
    """Return IANA timezone names that contain the query (case-insensitive, spaces→underscores)."""
    needle = query.strip().replace(' ', '_').lower()
    return [tz for tz in _ALL_TIMEZONES if needle in tz.lower()]
