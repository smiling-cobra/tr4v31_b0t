"""MongoDB-backed persistence for python-telegram-bot.

Without this, conversation state lives only in memory: every deploy — and the
deploy strategy here stops the machine outright — drops whoever was mid-onboarding
or mid-check-in into a state where their replies match no handler.

Two deliberate limits:

* **`user_data` is written through an allowlist, not a denylist.** Only the keys
  in `_PERSISTED_USER_DATA_KEYS` are stored. `entry_text` is deliberately absent:
  it is the most sensitive field the bot holds, it already lives in the entries
  collection, and persisting it would copy raw journal text into a second PII
  surface that `/delete` would then also have to reach. A new key is persisted
  only when someone adds it here on purpose.
* **Every pymongo call is dispatched to a worker thread.** These methods are
  coroutines on the bot's event loop, and a blocking driver call here would stall
  message handling for every user, not just the one being persisted.
"""
from __future__ import annotations

import asyncio
from typing import Any

from telegram.ext import BasePersistence, PersistenceInput

from db.db import conversations_collection, user_data_collection

_PERSISTED_USER_DATA_KEYS = ('name', 'mood_score')


def _persistable(data: dict) -> dict:
    """The subset of a user's data that is safe to write to a second store."""
    return {key: data[key] for key in _PERSISTED_USER_DATA_KEYS if key in data}


class MongoPersistence(BasePersistence):
    """Persists conversation state and a narrow slice of `user_data`.

    `bot_data`, `chat_data` and `callback_data` are switched off rather than
    stored empty — nothing in this bot uses them, and the no-op implementations
    below exist only because BasePersistence declares them abstract.
    """

    def __init__(self, update_interval: float = 60):
        super().__init__(
            store_data=PersistenceInput(
                bot_data=False,
                chat_data=False,
                user_data=True,
                callback_data=False,
            ),
            update_interval=update_interval,
        )

    # -- conversations ----------------------------------------------------

    async def get_conversations(self, name: str) -> dict:
        docs = await asyncio.to_thread(
            lambda: list(conversations_collection().find({'name': name}, {'_id': 0}))
        )
        return {tuple(doc['key']): doc['state'] for doc in docs}

    async def update_conversation(self, name: str, key: tuple, new_state: object | None) -> None:
        query = {'name': name, 'key': list(key)}

        if new_state is None:  # the conversation ended
            await asyncio.to_thread(lambda: conversations_collection().delete_one(query))
            return

        await asyncio.to_thread(
            lambda: conversations_collection().update_one(
                query, {'$set': {'state': new_state}}, upsert=True
            )
        )

    # -- user_data --------------------------------------------------------

    async def get_user_data(self) -> dict[int, dict]:
        docs = await asyncio.to_thread(lambda: list(user_data_collection().find({})))
        return {int(doc['_id']): doc.get('data', {}) for doc in docs}

    async def update_user_data(self, user_id: int, data: dict) -> None:
        kept = _persistable(data)

        if not kept:
            # Nothing worth keeping: drop the row rather than leaving an empty
            # one behind for every user who ever sent a message.
            await asyncio.to_thread(lambda: user_data_collection().delete_one({'_id': user_id}))
            return

        await asyncio.to_thread(
            lambda: user_data_collection().update_one(
                {'_id': user_id}, {'$set': {'data': kept}}, upsert=True
            )
        )

    async def drop_user_data(self, user_id: int) -> None:
        await asyncio.to_thread(lambda: user_data_collection().delete_one({'_id': user_id}))

    async def refresh_user_data(self, user_id: int, user_data: dict) -> None:
        """No-op: this store has no writer other than the bot itself."""

    # -- unused stores ----------------------------------------------------

    async def get_bot_data(self) -> dict:
        return {}

    async def update_bot_data(self, data: dict) -> None:
        """No-op: bot_data is not stored."""

    async def refresh_bot_data(self, bot_data: dict) -> None:
        """No-op: bot_data is not stored."""

    async def get_chat_data(self) -> dict[int, dict]:
        return {}

    async def update_chat_data(self, chat_id: int, data: dict) -> None:
        """No-op: chat_data is not stored."""

    async def refresh_chat_data(self, chat_id: int, chat_data: dict) -> None:
        """No-op: chat_data is not stored."""

    async def drop_chat_data(self, chat_id: int) -> None:
        """No-op: chat_data is not stored."""

    async def get_callback_data(self) -> Any:
        return None

    async def update_callback_data(self, data: Any) -> None:
        """No-op: callback_data is not stored."""

    # -- lifecycle --------------------------------------------------------

    async def flush(self) -> None:
        """No-op: every update above is written through immediately."""
