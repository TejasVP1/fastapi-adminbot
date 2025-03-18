import logging
import json
import google.generativeai as genai
from app.core.config import config
import datetime
from decimal import Decimal

# Configure logging
logger = logging.getLogger(__name__)

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
    """
    Formats SQL results into readable text using Gemini AI.
    
    - Handles serialization for datetime and Decimal types.
    - Validates input before processing.
    - Catches and logs API failures gracefully.
    """
    try:
        # ✅ Ensure results is valid
        if not results:
            logger.warning("Received empty or None results. Returning default message.")
            return "No data available to generate insights."

        if not isinstance(results, (dict, list)):
            logger.error(f"Invalid results format: {type(results)}")
            return "Invalid data format received."

        # ✅ Serialize the results properly
        formatted_data = json.dumps(results, indent=2, default=serialize_dates)
        logger.info(f"Formatted data for AI: {formatted_data}")

        # ✅ Generate response using Gemini
        prompt = f"Format the following database query results into a readable sentence with insights:\n\n{formatted_data}"
        response = model.generate_content(prompt)

        # ✅ Ensure response is valid
        if not response or not response.text:
            logger.error("Received empty response from Gemini AI.")
            return "AI could not generate insights at this time. Please try again later."

        return response.text.strip()

    except json.JSONDecodeError as e:
        logger.error(f"JSON formatting error: {e}")
        return "Error processing data for insights."

    except google.generativeai.types.APIError as e:
        logger.error(f"Gemini API error: {e}")
        return "AI service is currently unavailable. Please try again later."

    except Exception as e:
        logger.error(f"Unexpected error formatting results: {e}", exc_info=True)
        return "An unexpected error occurred while generating insights."
