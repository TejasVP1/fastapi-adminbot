import pytest
from unittest.mock import patch, MagicMock
import pymysql
from app.services.database import (
    get_database,
    get_db_connection,
    execute_sql_query
)

@pytest.fixture
def mock_mongo():
    """Mock MongoDB database connection."""
    with patch("app.services.database.client") as mock_client, \
         patch("app.services.database.db") as mock_db:
        yield mock_client, mock_db


@pytest.fixture
def mock_mysql():
    """Mock MySQL connection."""
    with patch("app.services.database.pymysql.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        # Mock MySQL cursor behavior
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        yield mock_connect, mock_conn, mock_cursor


def test_get_database(mock_mongo):
    """Test MongoDB database retrieval."""
    _, mock_db = mock_mongo
    mock_db.name = "test_db"

    db_instance = get_database()
    assert db_instance.name == "test_db"


def test_get_db_connection_success(mock_mysql):
    """Test MySQL connection establishment."""
    mock_connect, mock_conn, _ = mock_mysql

    conn = get_db_connection()
    assert conn == mock_conn
    mock_connect.assert_called_once()


def test_get_db_connection_failure():
    """Test MySQL connection failure handling."""
    with patch("app.services.database.pymysql.connect", side_effect=pymysql.MySQLError("Connection failed")):
        with pytest.raises(RuntimeError, match="Database connection error: Connection failed"):
            get_db_connection()


def test_execute_sql_query_success(mock_mysql):
    """Test successful SQL query execution."""
    _, mock_conn, mock_cursor = mock_mysql
    mock_cursor.fetchall.return_value = [{"id": 1, "name": "John"}]

    result = execute_sql_query("SELECT * FROM users")

    assert result == [{"id": 1, "name": "John"}]
    mock_conn.cursor.assert_called_once()
    mock_cursor.execute.assert_called_once_with("SELECT * FROM users")


def test_execute_sql_query_failure(mock_mysql):
    """Test handling of MySQL query errors."""
    _, mock_conn, mock_cursor = mock_mysql
    mock_cursor.execute.side_effect = pymysql.MySQLError("Query failed")

    result = execute_sql_query("SELECT * FROM users")

    assert "error" in result
    assert "Query failed" in result["error"]
    mock_conn.close.assert_called_once()
