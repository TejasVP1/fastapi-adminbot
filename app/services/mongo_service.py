from pymongo import MongoClient
import app.services.redis_service as redis
from app.core.config import config  

# Initialize MongoDB connection
mongo_client = MongoClient(config.MONGO_URI)
db = mongo_client[config.MONGO_DB_NAME]

threads_collection = db["threads"]
conversations_collection = db["conversations"]

def migrate_thread_to_mongo(thread_id):
    # Get thread data from Redis
    thread_data = redis.get_from_redis(thread_id)
    
    if "message" in thread_data and thread_data["message"] == "Thread not found":
        return {"message": "Thread not found in Redis", "thread_id": thread_id}, 404

    thread_details = thread_data["thread_details"]
    conversations = thread_data["conversations"]

    # Check if the thread already exists in MongoDB
    existing_thread = threads_collection.find_one({"thread_id": thread_id})
    if not existing_thread:  # Only insert if it doesn't exist
        thread_doc = {
            "thread_id": thread_details["thread_id"],
            "admin_id": thread_details["admin_id"],
            "chat_name": thread_details["chat_name"],
            "start_timestamp": conversations[0]["timestamp"] if conversations else None,
            "end_timestamp": conversations[-1]["timestamp"] if conversations else None
        }
        threads_collection.insert_one(thread_doc)

    # Insert each conversation only if it doesn't already exist
    for conv in conversations:
        existing_conv = conversations_collection.find_one({"conversation_id": conv["conversation_id"]})
        if not existing_conv:
            conv_doc = {
                "conversation_id": conv["conversation_id"],
                "thread_id": thread_id,
                "admin_id": thread_details["admin_id"],
                "query": conv["query"],
                "response": conv["response"],
                "visualization": conv.get("visualization"),
                "timestamp": conv["timestamp"],
                "data_type": conv.get("data_type"),
                "excel_path": conv.get("excel_path")
            }
            conversations_collection.insert_one(conv_doc)

    return f"Thread {thread_id} migrated to MongoDB successfully"
