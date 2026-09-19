from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)
database = client[settings.db_name]


async def ping_database() -> bool:
    try:
        await client.admin.command("ping")
        return True
    except Exception:
        return False