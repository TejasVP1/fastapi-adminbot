import logging
import json
import google.generativeai as genai
from app.core.config import config
import datetime
from decimal import Decimal

# Configure Gemini API
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

def serialize_dates(obj):
    """Convert non-serializable types (datetime, Decimal) to serializable formats."""
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type not serializable: {type(obj)}")

def format_results(results):
    logging.info(results)
    """Formats SQL results into readable text using Gemini."""
    try:
        formatted_data = json.dumps(results, indent=2, default=serialize_dates)  # Convert non-serializable types
        logging.info(formatted_data)
        prompt = f"Format the following database query results into a readable sentence with insights:\n\n{formatted_data}"
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Error formatting results: {e}")
        return f"Error formatting results: {str(e)}"