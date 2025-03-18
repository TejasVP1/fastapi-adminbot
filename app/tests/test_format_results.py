import pytest
import json
import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock
from app.services.result_formatter import format_results, serialize_dates

# Sample test data
sample_results = [
    {"loan_id": 1, "disbursed_date": datetime.date(2023, 5, 10), "interest": Decimal("7.5")},
    {"loan_id": 2, "disbursed_date": datetime.date(2024, 1, 15), "interest": Decimal("6.2")}
]

@pytest.mark.parametrize(
    "input_data, expected_json",
    [
        # Test case 1: Standard serialization
        ({"date": datetime.date(2024, 3, 18), "amount": Decimal("1234.56")},
         '{"date": "2024-03-18", "amount": 1234.56}'),

        # Test case 2: Nested structures
        ({"user": {"name": "John", "salary": Decimal("5000.75")}},
         '{"user": {"name": "John", "salary": 5000.75}}')
    ]
)
def test_serialize_dates(input_data, expected_json):
    """Test serialization of various data types."""
    assert json.dumps(input_data, default=serialize_dates) == expected_json


@patch("app.services.result_formatter.model.generate_content")
def test_format_results_valid(mock_gemini):
    """Test formatting results with valid input."""
    
    mock_gemini.return_value.text = "The loan details show an average interest rate of 6.85%."
    
    output = format_results(sample_results)
    
    assert "average interest rate" in output
    mock_gemini.assert_called_once()


@patch("app.services.result_formatter.model.generate_content")
def test_format_results_empty(mock_gemini):
    """Test formatting when results are empty."""
    
    mock_gemini.return_value.text = "No data available."
    
    output = format_results([])
    
    assert output == "No data available."
    mock_gemini.assert_called_once()


@patch("app.services.result_formatter.model.generate_content")
def test_format_results_large_data(mock_gemini):
    """Test formatting with large data input."""
    
    large_data = [{"loan_id": i, "interest": Decimal("5.5")} for i in range(1000)]
    
    mock_gemini.return_value.text = "The dataset contains 1000 records with a consistent interest rate of 5.5%."
    
    output = format_results(large_data)
    
    assert "1000 records" in output
    mock_gemini.assert_called_once()
