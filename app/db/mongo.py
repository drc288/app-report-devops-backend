from pymongo import AsyncMongoClient
from ..schemas.settings import Settings


class MongoDB:
    """
    MongoDB connection handler
    """
    settings: Settings = Settings()
    table: str = "repositories"

    def __init__(self):
        self.client = None
        self.db = None

    async def connect(self):
        try:
            self.client = AsyncMongoClient(self.settings.mongo_string_connection)
            await self.client.admin.command('ping')
            self.db = self.client[self.table]
        except Exception as e:
            print(f"Error: {str(e)}")
            raise

    async def close(self):
        if self.client:
            await self.client.close()
            print("Conexion cerrada")

    def get_db(self):
        return self.db

mongodb = MongoDB()

async def get_mongodb():
    yield mongodb.get_db()
