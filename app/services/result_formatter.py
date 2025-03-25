import logging
import json
import google.generativeai as genai
from app.core.config import config
import datetime
from decimal import Decimal
from app.core.metrics import track_method_performance

# Configure Gemini API
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

def serialize_dates(obj):
    """Convert non-serializable types (datetime, Decimal, bytes) to serializable formats."""
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, bytes):  # Convert bytes to string
        return obj.decode() if obj.decode(errors="ignore") else obj.hex()
    raise TypeError(f"Type not serializable: {type(obj)}")

@track_method_performance('format_results')
def format_results(results,user_inp):
    # logging.info(results)
    """Formats SQL results into readable text using Gemini."""
    try:
        formatted_data = json.dumps(results, indent=2, default=serialize_dates)  # Convert non-serializable types
        # logging.info(formatted_data)
        prompt = f"Based on the user question \n\n {user_inp} Format the following database query results into a readable sentence with insights which help to grow their business :\n\n{formatted_data}"
        response = model.generate_content(prompt)
        logging.info(f"Chatbot response: {response.text.strip()}")
        
        return response.text.strip()
    except json.JSONDecodeError as e:
        logging.error(f"JSON formatting error: {e}")
        return "Error processing data for insights."

    except genai.types.APIError as e:
        logging.error(f"Gemini API error: {e}")
        return "AI service is currently unavailable. Please try again later."

    except Exception as e:
        logging.error(f"Unexpected error formatting results: {e}", exc_info=True)
        return "An unexpected error occurred while generating insights."
