from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "admin_db"

client = AsyncIOMotorClient(MONGO_URL)
database = client[DB_NAME]
admin_collection = database.get_collection("admins")
