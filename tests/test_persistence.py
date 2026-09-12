"""Tests for MongoPersistence.

The allowlist is the part worth guarding: `entry_text` is raw journal text, and
persisting it would copy the most sensitive field the bot holds into a second
store that `/delete` would then also have to reach.
"""
from __future__ import annotations

import pytest

from bot.persistence import MongoPersistence
from db.db import user_data_collection

USER = 4242
CHAT = 1


@pytest.fixture
def store():
    return MongoPersistence()


class TestUserData:
    async def test_round_trips_persisted_keys(self, store):
        await store.update_user_data(USER, {'name': 'Sam', 'mood_score': 3})
        assert await store.get_user_data() == {USER: {'name': 'Sam', 'mood_score': 3}}

    async def test_entry_text_is_never_written(self, store):
        await store.update_user_data(
            USER, {'name': 'Sam', 'mood_score': 1, 'entry_text': 'a private thing'}
        )

        assert await store.get_user_data() == {USER: {'name': 'Sam', 'mood_score': 1}}
        # Not filtered on read — genuinely absent from the stored document.
        assert 'a private thing' not in str(list(user_data_collection().find({})))

    async def test_keys_are_allowlisted_not_denylisted(self, store):
        """A key nobody thought about is dropped, not silently persisted."""
        await store.update_user_data(USER, {'name': 'Sam', 'some_future_field': 'x'})
        assert await store.get_user_data() == {USER: {'name': 'Sam'}}

    async def test_row_is_dropped_when_nothing_is_persistable(self, store):
        await store.update_user_data(USER, {'name': 'Sam'})
        await store.update_user_data(USER, {'entry_text': 'only this'})
        assert await store.get_user_data() == {}

    async def test_stale_keys_do_not_survive_an_update(self, store):
        await store.update_user_data(USER, {'name': 'Sam', 'mood_score': 3})
        await store.update_user_data(USER, {'name': 'Sam'})
        assert await store.get_user_data() == {USER: {'name': 'Sam'}}

    async def test_drop_user_data_removes_the_row(self, store):
        await store.update_user_data(USER, {'name': 'Sam'})
        await store.drop_user_data(USER)
        assert await store.get_user_data() == {}

    async def test_empty_store_reads_back_empty(self, store):
        assert await store.get_user_data() == {}


class TestConversations:
    async def test_round_trips_a_state(self, store):
        await store.update_conversation('journal', (CHAT, USER), 4)
        assert await store.get_conversations('journal') == {(CHAT, USER): 4}

    async def test_keys_read_back_as_tuples(self, store):
        """PTB looks conversations up by tuple; a list would never match."""
        await store.update_conversation('journal', (CHAT, USER), 4)
        key, = (await store.get_conversations('journal')).keys()
        assert isinstance(key, tuple)

    async def test_a_new_state_replaces_the_old_one(self, store):
        await store.update_conversation('journal', (CHAT, USER), 4)
        await store.update_conversation('journal', (CHAT, USER), 5)
        assert await store.get_conversations('journal') == {(CHAT, USER): 5}

    async def test_none_ends_the_conversation(self, store):
        await store.update_conversation('journal', (CHAT, USER), 4)
        await store.update_conversation('journal', (CHAT, USER), None)
        assert await store.get_conversations('journal') == {}

    async def test_states_are_scoped_by_handler_name(self, store):
        await store.update_conversation('journal', (CHAT, USER), 4)
        assert await store.get_conversations('something_else') == {}

    async def test_users_are_isolated(self, store):
        await store.update_conversation('journal', (CHAT, USER), 4)
        await store.update_conversation('journal', (CHAT, 9999), 6)
        assert await store.get_conversations('journal') == {(CHAT, USER): 4, (CHAT, 9999): 6}


class TestUnusedStores:
    """Declared off in PersistenceInput; the no-ops exist only to satisfy the ABC."""

    async def test_bot_and_chat_data_read_back_empty(self, store):
        assert await store.get_bot_data() == {}
        assert await store.get_chat_data() == {}
        assert await store.get_callback_data() is None

    async def test_writes_to_unused_stores_are_harmless(self, store):
        await store.update_bot_data({'x': 1})
        await store.update_chat_data(CHAT, {'x': 1})
        await store.update_callback_data(None)
        await store.drop_chat_data(CHAT)
        await store.flush()
        assert await store.get_bot_data() == {}


class TestWiring:
    """The pieces only help if they are actually attached to the Application."""

    TOKEN = '123456:AAABBBCCCDDDEEEFFFGGGHHHIIIJJJKKKLLL'

    def _build(self):
        from telegram.ext import ApplicationBuilder
        from bot.handlers import commands, errors, journal

        app = ApplicationBuilder().token(self.TOKEN).persistence(MongoPersistence()).build()
        commands.register(app)
        journal.register(app)
        errors.register(app)
        return app

    def _conversation(self, app):
        from telegram.ext import ConversationHandler

        return next(h for h in app.handlers[0] if isinstance(h, ConversationHandler))

    def test_the_conversation_is_persisted_under_a_stable_name(self):
        conv = self._conversation(self._build())
        assert conv.persistent is True
        # The persistence layer keys stored states by this; changing it orphans
        # every live conversation.
        assert conv.name == 'journal'

    def test_an_error_handler_is_registered(self):
        assert self._build().error_handlers

    def test_a_stray_text_message_has_somewhere_to_land(self):
        """The lost-state entry point — without it such a message matches nothing."""
        from telegram.ext import MessageHandler

        conv = self._conversation(self._build())
        assert any(isinstance(h, MessageHandler) for h in conv.entry_points)
