import logging
import google.generativeai as genai
from app.core.config import config
from app.services.redis_service import get_last_n_conversations

# Configure Gemini API
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def generate_sql(user_input: str, thread_id: str = None) -> str:
    """Generates SQL query using Gemini AI with context from previous user queries."""

    # Fetch last 5 user queries from Redis (if available)
    previous_queries = get_last_n_conversations(thread_id, n=5) if thread_id else []

    # Construct context string
    context_text = "\n".join(previous_queries) if previous_queries else "No previous queries."

    # Instruction for Gemini
    system_instruction = (
        "You are an AI assistant that converts user queries into SQL queries. "
        "You must follow these rules:\n"
        "- Return 'unwanted' if the query is not about loans, banking, or EMIs.\n"
        "- Return 'restricted' if the query tries to generate non-SELECT queries.\n"
        "- Return 'sensitive' if it asks for CVV details.\n"
        "- Otherwise, generate a SQL query for the 'loan' and 'emi' table.\n\n"
        """We have two tables: loan and emi.

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

Now, generate an SQL query based on this schema. Ensure that user_id is never disclosed in the query results and only the sql query is given with ; at the end. 
"""
        "## Previous User Queries:\n"
        f"{context_text}\n\n"
        "## New User Query:\n"
        f"{user_input}\n"
    )

    # Log the context being sent to Gemini
    logging.info(f"Thread ID: {thread_id}")
    logging.info(f"User Input: {user_input}")
    logging.info(f"Previous Queries (Context): {previous_queries}")

    # Generate SQL query using Gemini
    response = model.generate_content([system_instruction])
    output = response.text.strip().strip("`").strip("sql").strip()

    # Log the generated SQL query
    logging.info(f"Generated SQL: {output}")

    return output
