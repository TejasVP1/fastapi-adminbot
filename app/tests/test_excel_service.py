import pytest
import os
import pandas as pd
from unittest.mock import patch, MagicMock
from app.services.excel_service import generate_excel
from app.core.config import EXCEL_STORAGE_PATH

# Sample test data
test_data = [
    {"name": "Alice", "age": 30, "city": "New York"},
    {"name": "Bob", "age": 25, "city": "Los Angeles"}
]

@pytest.mark.asyncio
@patch("app.services.excel_service.store_excel_path")
async def test_generate_excel_success(mock_store_excel_path, tmp_path):
    """Test successful Excel generation."""
    
    conversation_id = "test123"
    test_excel_path = os.path.join(tmp_path, f"{conversation_id}.xlsx")

    # Patch EXCEL_STORAGE_PATH dynamically
    with patch("app.services.excel_service.EXCEL_STORAGE_PATH", tmp_path):
        await generate_excel(conversation_id, test_data)

    # Check if file was created
    assert os.path.exists(test_excel_path)

    # Check if the Excel file is readable
    df = pd.read_excel(test_excel_path)
    assert df.shape == (2, 3)  # Ensure correct data shape

    # Verify Redis storage function was called
    mock_store_excel_path.assert_called_once_with(conversation_id, test_excel_path)


@pytest.mark.asyncio
@patch("app.services.excel_service.store_excel_path")
async def test_generate_excel_empty_data(mock_store_excel_path, tmp_path):
    """Test Excel generation with empty data."""
    
    conversation_id = "empty_data_test"
    test_excel_path = os.path.join(tmp_path, f"{conversation_id}.xlsx")

    with patch("app.services.excel_service.EXCEL_STORAGE_PATH", tmp_path):
        await generate_excel(conversation_id, [])

    # Ensure file exists but is empty
    assert os.path.exists(test_excel_path)
    df = pd.read_excel(test_excel_path)
    assert df.empty  # Ensure it's empty

    mock_store_excel_path.assert_called_once_with(conversation_id, test_excel_path)


@pytest.mark.asyncio
@patch("app.services.excel_service.store_excel_path")
async def test_generate_excel_error(mock_store_excel_path):
    """Test Excel generation error handling."""
    
    conversation_id = "error_test"

    # Simulate an exception when saving
    with patch("pandas.DataFrame.to_excel", side_effect=OSError("Disk full")):
        with patch("app.services.excel_service.logging.error") as mock_log_error:
            await generate_excel(conversation_id, test_data)

    mock_log_error.assert_called_with("Excel generation failed: Disk full")
    mock_store_excel_path.assert_not_called()  # Ensure Redis is not updated on failure
