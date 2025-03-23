import re
import logging
import google.generativeai as genai
from transformers import pipeline
from thefuzz import fuzz  # For fuzzy matching
from app.core.config import config
from app.services.redis_service import get_last_n_conversations

# Configure Gemini API
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load a Zero-Shot Classification Model
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

# **VALID TOPICS**: Queries should be related to these topics.
VALID_TOPICS = [
    "loan details", "emi payment", "interest rate", "loan tenure", "loan type", "cibil score",
    "disbursed loans", "pending loans", "overdue emi", "user information", "banking details",
    "financial history", "monthly emi", "loan principal", "emi due date"
]

# **Sensitive keywords** (strictly forbidden)
SENSITIVE_KEYWORDS = ["cvv", "password", "aadhar", "pan"]

# **Restricted SQL operations** (only SELECT queries allowed)
RESTRICTED_KEYWORDS = ["insert", "update", "delete", "drop", "alter"]


def fuzzy_match(query: str, valid_topics: list, threshold: int = 80) -> bool:
    """Returns True if the query meaningfully matches a valid topic using fuzzy matching."""
    return any(fuzz.partial_ratio(query.lower(), topic.lower()) >= threshold for topic in valid_topics)


def classify_query(user_input: str) -> str:
    """Classifies the user query using zero-shot NLP and rule-based filtering."""

    # **1️⃣ Check for sensitive data**
    if any(re.search(rf"\b{kw}\b", user_input, re.IGNORECASE) for kw in SENSITIVE_KEYWORDS):
        return "sensitive"

    # **2️⃣ Check for restricted SQL commands**
    if any(re.search(rf"\b{kw}\b", user_input, re.IGNORECASE) for kw in RESTRICTED_KEYWORDS):
        return "restricted"

    # **3️⃣ Check if query matches valid topics (fuzzy matching)**
    if fuzzy_match(user_input, VALID_TOPICS):
        return "valid"

    # **4️⃣ NLP-Based Classification (Fallback)**
    result = classifier(user_input, ["valid", "unwanted", "restricted", "sensitive"])
    classification = result["labels"][0].lower()

    # **5️⃣ Explicitly return "unwanted" if NLP also marks it as such**
    if classification in ["unwanted", "restricted", "sensitive"]:
        return classification

    # **If NLP doesn't classify it explicitly as valid, treat it as unwanted**
    return "unwanted"



def generate_sql(user_input: str, thread_id: str = None) -> str:
    """Generates SQL query using Gemini AI with context from previous user queries."""

    # **Step 1: NLP Classification Before Gemini**
    classification = classify_query(user_input)

    if classification in ["unwanted", "restricted", "sensitive"]:
        logging.info(f"Query classified as {classification}.")
        return classification  # Return classification result directly

    # **Step 2: Fetch Last 5 Conversations for Context**
    previous_queries = get_last_n_conversations(thread_id, n=5) if thread_id else []
    context_text = "\n".join(previous_queries) if previous_queries else "No previous queries."

    # **Step 3: Gemini Processing (Your Prompt Stays Unchanged)**
    system_instruction = (
        "You are an AI assistant that converts user queries into SQL queries. "
        "You must follow these rules:\n"
        "- Return 'unwanted' if the query is not about loans, banking, or EMIs.\n"
        "- Return 'restricted' if the query tries to generate non-SELECT queries.\n"
        "- Return 'sensitive' if it asks for CVV,password,pan and aadhar details or database structure and other database structure related questions.\n"
        "- Otherwise, generate a SQL query for the 'loan', 'emi', 'users' and 'user_information' table.\n\n"
        "you are supposed to understand the schema and return the columns which wll be used for plotting graph later on"
        "UNDERSTAND ALL THE REQUIRED COLUMNS FROM THE TABLES TO GENERATE A PERFECT SQL QUERY PLEASE"

        """We have four tables: loan, emi, user_information, users.

The loan table contains the following columns:

- loan_id (Primary Key)
- disbursed_date (Only populated if status is 'DISBURSED', otherwise NULL)
- interest (Interest rate in percentage)
- principal (Principal loan amount)
- status (ENUM: 'DISBURSED', 'PENDING', 'REJECTED')
- tenure (Loan tenure in months)
- type (ENUM: 'HOME_LOAN', 'CAR_LOAN', 'PERSONAL_LOAN', 'EDUCATION_LOAN', 'PROFESSIONAL_LOAN')
- user_id (Should never be disclosed)

The emi table contains the following columns:

- emi_id (Primary Key)
- due_date (Date when EMI is due)
- emi_amount (EMI amount for that month)
- late_fee (Late fee applicable if status is 'OVERDUE', otherwise NULL)
- status (ENUM: 'PAID', 'OVERDUE', 'PENDING')
- loan_id (Foreign Key referencing loan.loan_id)

The users table has the following
 - user_id (Primary key)
 -address (address of the user)
 -email (email of the user)
 - is_active (whether his account is active or not, id is_active =1 then it is active)
 - name  (name of the user)
 - phone_number (phone number of the user)

 The user_information table has the following
 -id (user_information id , no need to disclose this)
 -aadhar (aadhar number)
 -cibil (CIBIL SCORE of the user)
 -income_type ('UNEMPLOYED','SALARIED','SELF_EMPLOYED',)
 -pan (pan number of the user)
 -salary (salary of the user)
 -user_id (foreign key referencing users.users.user_id)

The loan table and emi table are connected through loan_id.
If anything to do with disbursed_date or emi_date is asked, use MONTH(), YEAR(), DAY() etc and MySQL specific syntax and not other SQL formats. Always give in one line only even if it has multiple lines.

Now, generate an SQL query based on this schema. Ensure that user_id is never disclosed in the query results and only the sql query is given with ; at the end. 
"""
        "## Previous User Queries:\n"
        f"{context_text}\n\n"
        "## New User Query:\n"
        f"{user_input}\n"
    )

    # **Step 4: Call Gemini**
    response = model.generate_content([system_instruction])
    output = response.text.strip().strip("`").strip("sql").strip()

    # **Step 5: Final Validation (Gemini Check)**
    if output.lower() in ["unwanted", "restricted", "sensitive"]:
        logging.info(f"Gemini flagged query as {output}.")
        return output  # Return Gemini’s classification if flagged

    # **Log & Return Final SQL**
    logging.info(f"Generated SQL: {output}")
    return output
