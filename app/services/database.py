import pymysql
import logging
from app.core.config import config
from pymongo import MongoClient
from app.core.config import *

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB Connection
try:
    logger.info("Establishing MongoDB connection")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)  # Added timeout
    # Test connection
    client.server_info()
    db = client[MONGO_DB_NAME]
    admins_collection = db["admins"]
    logger.info("MongoDB connection established successfully")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}")
    raise

def get_database():
    """Returns the MongoDB database instance for use in application routes and services"""
    try:
        return db
    except Exception as e:
        logger.error(f"Error accessing MongoDB database: {str(e)}")
        raise RuntimeError(f"Database access error: {str(e)}")

def get_db_connection():
    """Establish a MySQL database connection with configured credentials and return the connection object"""
    try:
        logger.info("Establishing MySQL connection")
        connection = pymysql.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            port=config.DB_PORT,
            cursorclass=pymysql.cursors.DictCursor
        )
        logger.debug("MySQL connection established successfully")
        return connection
    except pymysql.MySQLError as e:
        logger.error(f"MySQL connection error: {str(e)}")
        raise RuntimeError(f"Database connection error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error establishing MySQL connection: {str(e)}")
        raise

def execute_sql_query(query: str):
    """Executes the provided SQL query on MySQL database and returns results as dictionary objects"""
    conn = None
    try:
        logger.info(f"Executing SQL query: {query[:50]}...")
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
            logger.info(f"Query executed successfully, returned {len(results)} rows")
            return results
    except pymysql.MySQLError as e:
        logger.error(f"MySQL query error: {str(e)}")
        return {"error": f"Database query error: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error executing query: {str(e)}")
        return {"error": f"Query execution error: {str(e)}"}
    finally:
        if conn:
            conn.close()
            logger.debug("MySQL connection closed")