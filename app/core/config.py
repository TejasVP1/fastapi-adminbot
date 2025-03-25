
import os
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables from .env file
load_dotenv()

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

JWT_SECRET_KEY = "your_secret_key"  
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour

# Define the Excel storage path
EXCEL_STORAGE_PATH = os.getenv("EXCEL_STORAGE_PATH", "/home/praadnyah/AdminBot/fastapi-adminbot/excel_files")
# Define the Excel storage path
CHARTS_DIR = os.getenv("CHARTS_DIR", "/home/praadnyah/AdminBot/fastapi-adminbot/charts")

class Config:
    DB_HOST = os.getenv("DB_HOST")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_NAME = os.getenv("DB_NAME")
    DB_PORT = int(os.getenv("DB_PORT"))
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # Redis Config
    REDIS_HOST = os.getenv("REDIS_HOST")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))

    MONGO_URI = os.getenv("MONGO_URI")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

    # Email configuration
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")  # Hardcoded admin email
    EMAIL_HOST = os.getenv("EMAIL_HOST")
    EMAIL_PORT = os.getenv("EMAIL_PORT")
    EMAIL_USER = os.getenv("EMAIL_USER") # Your Gmail address
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD") # Your Gmail app password

config = Config()