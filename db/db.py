import os
from pymongo import MongoClient
from pymongo.database import Database
from dotenv import load_dotenv

load_dotenv()

_client: MongoClient = None
_db: Database = None

# Every Mongo call now runs in a worker thread handed off from the event loop.
# pymongo's 30s default would pin one of those threads for half a minute and
# leave the user staring at nothing before the error arrives.
_SERVER_SELECTION_TIMEOUT_MS = 5000


def get_db() -> Database:
    global _client, _db

    if _db is None:
        mongo_uri = os.environ.get('MONGODB_URI')

        if not mongo_uri:
            raise ValueError('MONGODB_URI is not set in environment variables')

        _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=_SERVER_SELECTION_TIMEOUT_MS)
        _db = _client['anxiety_journal']

    return _db


def get_collection(name: str):
    return get_db()[name]


# Collection accessors
def users_collection():
    return get_collection('users')


def entries_collection():
    return get_collection('entries')


def streaks_collection():
    return get_collection('streaks')


def notifications_collection():
    return get_collection('notifications')
