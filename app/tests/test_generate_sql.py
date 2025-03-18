import pytest
from unittest.mock import patch, MagicMock
from app.services.query_generator import generate_sql

@pytest.mark.parametrize(
    "user_input, thread_id, mock_redis_return, expected_output",
    [
        # Test case 1: Unwanted query
        ("Show me stock prices", None, [], "unwanted"),

        # Test case 2: Restricted query (UPDATE query attempt)
        ("Update loan set interest=10 where loan_id=5", None, [], "restricted"),

        # Test case 3: Sensitive information request
        ("Get all users' PAN numbers", None, [], "sensitive"),

        # Test case 4: SQL query generation with no context
        ("Show all loans disbursed this year", None, [],
         "SELECT loan_id, disbursed_date, interest, principal, status, tenure, type FROM loan WHERE YEAR(disbursed_date) = YEAR(CURDATE());"),

        # Test case 5: SQL query generation with context
        ("Get overdue EMIs", "thread_123", ["Show all loans"], 
         "SELECT emi_id, due_date, emi_amount, late_fee, status FROM emi WHERE status='OVERDUE';"),
    ]
)
@patch("app.services.query_generator.get_last_n_conversations")
@patch("app.services.query_generator.model.generate_content")
def test_generate_sql(mock_gemini, mock_redis, user_input, thread_id, mock_redis_return, expected_output):
    """Test SQL query generation with different inputs."""
    
    # Mock Redis return value
    mock_redis.return_value = mock_redis_return
    
    # Mock Gemini AI response
    mock_gemini.return_value.text = f"```sql\n{expected_output}\n```"

    # Call function
    result = generate_sql(user_input, thread_id)

    # Check if function output matches expected SQL or predefined response
    assert result == expected_output, f"Expected {expected_output}, got {result}"
