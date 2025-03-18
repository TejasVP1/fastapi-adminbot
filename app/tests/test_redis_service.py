import json
import pytest
import redis
from unittest.mock import patch, MagicMock
from app.services.redis_service import (
    insert_into_redis,
    append_conversation,
    get_from_redis,
    store_excel_path,
    get_excel_path
)

# Mock Redis client
@pytest.fixture
def mock_redis():
    with patch("app.services.redis_service.redis_client") as mock_redis_client:
        yield mock_redis_client


def test_insert_into_redis(mock_redis):
    """Test inserting a chat thread into Redis."""
    mock_redis.hset = MagicMock()
    mock_redis.rpush = MagicMock()
    mock_redis.expire = MagicMock()

    data = {
        "thread_id": "123",
        "admin_id": "admin_1",
        "chat_name": "Support Chat",
        "conversations": [
            {"conversation_id": "conv_1", "query": "Hello?"},
            {"conversation_id": "conv_2", "query": "How are you?"}
        ]
    }

    response = insert_into_redis(data)

    assert response == {"message": "Chat thread inserted successfully", "thread_id": "123"}
    mock_redis.hset.assert_called_once()
    mock_redis.expire.assert_called()


def test_append_conversation(mock_redis):
    """Test appending a conversation to an existing thread in Redis."""
    mock_redis.rpush = MagicMock()
    mock_redis.expire = MagicMock()
    mock_redis.llen = MagicMock(return_value=3)

    thread_id = "123"
    conversation = {"conversation_id": "conv_3", "query": "What's up?"}

    response = append_conversation(thread_id, conversation)

    assert response["status"] == "success"
    assert response["total_conversations"] == 3
    mock_redis.rpush.assert_called_once()
    mock_redis.expire.assert_called()


def test_get_from_redis(mock_redis):
    """Test retrieving a thread from Redis."""
    mock_redis.exists.return_value = True
    mock_redis.hgetall.return_value = {
        "thread_id": "123",
        "admin_id": "admin_1",
        "chat_name": "Support Chat"
    }
    mock_redis.lrange.return_value = [json.dumps({"conversation_id": "conv_1", "query": "Hello?"})]

    with patch("app.services.redis_service.get_excel_path", return_value="/path/to/excel.xlsx"):
        response = get_from_redis("123")

    assert response["thread_details"]["thread_id"] == "123"
    assert len(response["conversations"]) == 1
    assert response["conversations"][0]["excel_path"] == "/path/to/excel.xlsx"


def test_get_from_redis_thread_not_found(mock_redis):
    """Test retrieving a non-existent thread from Redis."""
    mock_redis.exists.return_value = False

    response, status_code = get_from_redis("999")

    assert response == {"message": "Thread not found"}
    assert status_code == 404


def test_store_excel_path(mock_redis):
    """Test storing an Excel file path in Redis."""
    mock_redis.set = MagicMock()
    mock_redis.expire = MagicMock()

    conversation_id = "conv_1"
    file_path = "/path/to/excel.xlsx"

    store_excel_path(conversation_id, file_path)

    mock_redis.set.assert_called_with(f"excel:{conversation_id}", file_path)
    mock_redis.expire.assert_called_with(f"excel:{conversation_id}", 10800)


def test_get_excel_path(mock_redis):
    """Test retrieving an Excel file path from Redis."""
    mock_redis.get.return_value = "/path/to/excel.xlsx"

    file_path = get_excel_path("conv_1")

    assert file_path == "/path/to/excel.xlsx"
    mock_redis.get.assert_called_with("excel:conv_1")
