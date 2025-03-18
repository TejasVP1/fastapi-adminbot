import pandas as pd
import os
from app.core.config import EXCEL_STORAGE_PATH
from app.services.redis_service import store_excel_path, get_excel_path
import logging

# Ensure the storage directory exists
os.makedirs(EXCEL_STORAGE_PATH, exist_ok=True)

async def generate_excel(conversation_id: str, data: list):
    """
    Asynchronously generate an Excel file from query results.
    """
    df = pd.DataFrame(data)  
    file_path = os.path.join(EXCEL_STORAGE_PATH, f"{conversation_id}.xlsx")
    
    try:
        df.to_excel(file_path, index=False)
        store_excel_path(conversation_id, file_path)  # Store path in Redis
        logging.info(f"Excel generated: {file_path}")
    except Exception as e:
        logging.error(f"Excel generation failed: {e}")
