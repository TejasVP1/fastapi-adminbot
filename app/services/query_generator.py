import re
import logging
import google.generativeai as genai
import spacy
from thefuzz import fuzz  # For fuzzy matching
from app.core.config import config
from app.services.redis_service import get_last_n_conversations

# Load spaCy NLP model
nlp = spacy.load("en_core_web_sm")

# Configure Gemini API
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# **Valid Loan-Related Topics**
VALID_TOPICS = [
    "loan details", "emi payment", "interest rate", "loan tenure", "loan type", "cibil score",
    "disbursed loans", "pending loans", "overdue emi", "user information", "banking details",
    "financial history", "monthly emi", "loan principal", "emi due date"
]

# **Restricted SQL operations** (only SELECT queries allowed)
RESTRICTED_KEYWORDS = ["insert", "update", "delete", "drop", "alter", "modify", "change", "set"]

# **Sensitive keywords** (strictly forbidden)
SENSITIVE_KEYWORDS = ["cvv", "password", "aadhar", "pan", "account number"]

TOKEN_MAP = {
    "t1": "loan",
    "t2": "emi",
    "t3": "users",
    "t4": "user_information",

    # Loan Table
    "c1": "loan_id",
    "c2": "disbursed_date",
    "c3": "interest",
    "c4": "principal",
    "c5": "status",
    "c6": "tenure",
    "c7": "type",
    "c8": "user_id",  # Foreign key
    
    # EMI Table
    "c9": "due_date",
    "c10": "emi_amount",
    "c11": "late_fee",
    
    # Users Table
    "c12": "email",
    "c13": "address",
    "c14": "is_active",
    "c15": "name",
    "c16": "phone_number",
    
    # User Information Table
    "c17": "cibil",
    "c18": "salary",
    "c19": "income_type",
}

REVERSE_TOKEN_MAP = {v: k for k, v in TOKEN_MAP.items()}


def tokenize_schema(schema: str) -> str:
    """Replaces column and table names with tokens."""
    for key, value in TOKEN_MAP.items():
        schema = schema.replace(key, value)
    return schema

def detokenize_sql(sql_query: str) -> str:
    """Correctly replaces tokens with actual table & column names."""
    
    # Replace table names first
    for key, value in TOKEN_MAP.items():
        if key.startswith("t"):  # Match table tokens
            sql_query = re.sub(rf'\b{key}\b', value, sql_query)
    
    # Replace column names after tables
    for key, value in TOKEN_MAP.items():
        if key.startswith("c"):  # Match column tokens
            sql_query = re.sub(rf'\b{key}\b', value, sql_query)

    return sql_query



def fuzzy_match(query: str, valid_topics: list, threshold: int = 80) -> bool:
    """Returns True if the query meaningfully matches a valid topic using fuzzy matching."""
    return any(fuzz.partial_ratio(query.lower(), topic.lower()) >= threshold for topic in valid_topics)

def classify_query(user_input: str) -> str:
    """Classifies the user query using NLP, regex, and fuzzy matching."""

    # **1️⃣ NLP Analysis Using spaCy**
    doc = nlp(user_input.lower())

    # **2️⃣ Check for Sensitive Data**
    if any(word in user_input.lower() for word in SENSITIVE_KEYWORDS):
        return "sensitive"

    # **3️⃣ Check for Restricted SQL Commands**
    if any(word in user_input.lower() for word in RESTRICTED_KEYWORDS):
        return "restricted"

    # **4️⃣ Check if Query Matches Valid Topics (Fuzzy Matching)**
    if fuzzy_match(user_input, VALID_TOPICS):
        return "valid"

    # **5️⃣ Identify "Modify" or Non-SELECT Actions in NLP**
    for token in doc:
        if token.lemma_ in ["modify", "change", "update", "edit", "set"]:
            return "restricted"

    # **6️⃣ If No Match, It's Unwanted**
    return "unwanted"

def generate_sql(user_input: str, thread_id: str = None) -> str:
    """Generates SQL query using Gemini AI with proper classification checks."""

    # **Step 1: NLP Classification Before Gemini**
    # classification = classify_query(user_input)

    # if classification in ["unwanted", "restricted", "sensitive"]:
    #     logging.info(f"Query classified as {classification}.")
    #     return classification  # Return classification result directly

    # **Step 2: Fetch Last 5 Conversations for Context**
    previous_queries = get_last_n_conversations(thread_id, n=5) if thread_id else []
    context_text = "\n".join(previous_queries) if previous_queries else "No previous queries."

    # **Step 3: Tokenize the Schema**
    original_schema = """
We have four tables: loan, emi, user_information, users.

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

The users table has the following:
- user_id (Primary key)
- address (address of the user)
- email (email of the user)
- is_active (1 if active, 0 otherwise)
- name  (name of the user)
- phone_number (phone number of the user)

The user_information table has the following:
- id (user_information id, no need to disclose this)
- aadhar (aadhar number)
- cibil (CIBIL SCORE of the user)
- income_type ('UNEMPLOYED', 'SALARIED', 'SELF_EMPLOYED')
- pan (pan number of the user)
- salary (salary of the user)
- user_id (foreign key referencing users.user_id)
"""
    tokenized_schema = tokenize_schema(original_schema)

    # **Step 4: Gemini Processing**
    system_instruction = (
        "You are an AI assistant that converts user queries into SQL queries. "
        "Ensure the following rules:\n"
        "- Return 'unwanted' if the query is not about loans, banking, or EMIs.\n"
        "- Return 'restricted' if the query tries to generate non-SELECT queries.\n"
        "- Return 'sensitive' if it asks for CVV, password, PAN, or Aadhaar details.\n"
        "- Otherwise, generate a SQL query based on the given schema (tables t1, t2, t3, t4).\n"
        "- Ensure that c8 (user_id) is never disclosed in query results.\n"
        "- Return only the SQL query, ending with a semicolon.\n\n"
        "If anything to do with disbursed_date or emi_date is asked, use MONTH(), YEAR(), DAY() etc and MySQL specific syntax and not other SQL formats. Always give in one line only even if it has multiple lines."

"Now, generate an SQL query based on this schema. Ensure that user_id is never disclosed in the query results and only the sql query is given with ; at the end. "
        f"## Schema:\n{tokenized_schema}\n\n"
        f"## Previous User Queries:\n{context_text}\n\n"
        f"## New User Query:\n{user_input}\n"
        
    )
    print("tokenization")
    logging.info(tokenize_schema)

    


    response = model.generate_content([system_instruction])
    print("response")
    logging.info(response)
    output = response.text.strip().strip("`").strip("sql").strip()
    logging.info(output)

    # **Step 5: Detokenize the SQL Query**
    final_sql = detokenize_sql(output)
    logging.info(final_sql)

    logging.info(f"Generated SQL: {final_sql}")
    return final_sql
