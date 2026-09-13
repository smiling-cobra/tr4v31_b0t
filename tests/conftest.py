from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import mongomock
import pytest

import db.db as db_module


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    """Replace the MongoDB connection with an in-memory mongomock instance.

    Applied automatically to every test so no test ever touches a real database.
    The fixture resets _db to None after each test so the next test starts clean.
    """
    client = mongomock.MongoClient()
    db = client['anxiety_journal']
    monkeypatch.setattr(db_module, '_db', db)
    yield db
    monkeypatch.setattr(db_module, '_db', None)


def make_update(text: str, user_id: int = 12345) -> MagicMock:
    """A mocked Update carrying a text message, for handler tests."""
    u = MagicMock()
    u.message.text = text
    u.message.reply_text = AsyncMock()
    u.effective_user.id = user_id
    return u


def make_location_update(lat: float, lng: float, user_id: int = 12345) -> MagicMock:
    """A mocked Update carrying a shared location, for the timezone-detection tests."""
    u = MagicMock()
    u.message.location.latitude = lat
    u.message.location.longitude = lng
    u.message.reply_text = AsyncMock()
    u.effective_user.id = user_id
    return u


def make_context(user_data: dict | None = None) -> MagicMock:
    """A mocked CallbackContext with a plain dict for user_data."""
    c = MagicMock()
    c.user_data = user_data if user_data is not None else {}
    return c
