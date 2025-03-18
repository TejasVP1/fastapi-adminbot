import pymysql
from app.core.config import config
from pymongo import MongoClient
from app.core.config import *

# MongoDB Connection
client = MongoClient(MONGO_URI)  # Uses the MongoDB Atlas URI
db = client[MONGO_DB_NAME]  # Uses the correct database name
admins_collection = db["admins"]  # Admin credentials stored here

def get_database():
    """Returns the MongoDB database instance"""
    return db

def get_db_connection():
    """Establish a database connection and return the connection object."""
    return pymysql.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        port=config.DB_PORT,
        cursorclass=pymysql.cursors.DictCursor
    )

def execute_sql_query(query: str):
    """Executes the generated SQL query on MySQL database and returns results."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        return {"error": str(e)}
