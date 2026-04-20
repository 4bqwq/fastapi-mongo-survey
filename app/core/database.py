from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, IndexModel

from app.core.config import settings


class Database:
    client: AsyncIOMotorClient = None
    db = None


db = Database()


async def ensure_indexes():
    await db.db.questions.create_indexes(
        [
            IndexModel([("questionId", ASCENDING), ("version", ASCENDING)], unique=True),
            IndexModel([("userId", ASCENDING), ("questionId", ASCENDING)]),
            IndexModel([("versionChainRootId", ASCENDING), ("version", ASCENDING)]),
        ]
    )

    await db.db.surveys.create_indexes(
        [
            IndexModel([("userId", ASCENDING), ("createdAt", DESCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("questions.questionId", ASCENDING)]),
        ]
    )

    await db.db.answers.create_indexes(
        [
            IndexModel([("surveyId", ASCENDING), ("submittedAt", DESCENDING)]),
            IndexModel([("surveyId", ASCENDING), ("respondentId", ASCENDING)]),
        ]
    )


async def connect_to_mongo():
    db.client = AsyncIOMotorClient(settings.MONGODB_URL)
    db.db = db.client[settings.MONGO_DB_NAME]
    await ensure_indexes()


async def close_mongo_connection():
    if db.client is not None:
        db.client.close()


def get_database():
    return db.db
