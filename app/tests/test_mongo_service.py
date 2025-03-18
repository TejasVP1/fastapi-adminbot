import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from app.services.mongo_service import (
    get_conversations_by_thread,
    get_threads_by_admin,
    insert_into_threads,
    insert_into_conversations
)


@pytest.fixture
def mock_mongo():
    """Mock MongoDB collections."""
    with patch("app.services.mongo_service.threads_collection") as mock_threads, \
         patch("app.services.mongo_service.conversations_collection") as mock_conversations:
        yield mock_threads, mock_conversations


def test_get_conversations_by_thread(mock_mongo):
    """Test fetching paginated conversations for a thread."""
    mock_threads, mock_conversations = mock_mongo
    mock_conversations.find.return_value.sort.return_value.skip.return_value.limit.return_value = [
        {"conversation_id": "conv_1", "query": "Hello?", "response": "Hi!", "timestamp": "2024-03-18T12:00:00Z"},
        {"conversation_id": "conv_2", "query": "How are you?", "response": "I'm good!", "timestamp": "2024-03-18T12:01:00Z"},
    ]
    mock_conversations.count_documents.return_value = 2

    result = get_conversations_by_thread("admin_1", "thread_1", page=1, limit=2)

    assert result["total_conversations"] == 2
    assert result["page"] == 1
    assert result["conversations"][0]["query"] == "Hello?"
    mock_conversations.find.assert_called_once()


def test_get_threads_by_admin(mock_mongo):
    """Test fetching paginated threads for an admin."""
    mock_threads, _ = mock_mongo
    mock_threads.find.return_value.skip.return_value.limit.return_value = [
        {"thread_id": "thread_1", "chat_name": "Support Chat"},
        {"thread_id": "thread_2", "chat_name": "Tech Help"},
    ]
    mock_threads.count_documents.return_value = 2

    result = get_threads_by_admin("admin_1", page=1, limit=2)

    assert result["total_threads"] == 2
    assert len(result["threads"]) == 2
    assert result["threads"][0]["chat_name"] == "Support Chat"
    mock_threads.find.assert_called_once()


def test_insert_into_threads(mock_mongo):
    """Test inserting a new thread into MongoDB."""
    mock_threads, _ = mock_mongo
    mock_threads.insert_one = MagicMock()

    insert_into_threads("thread_1", "admin_1", "Support Chat")

    mock_threads.insert_one.assert_called_once()
    inserted_doc = mock_threads.insert_one.call_args[0][0]
    assert inserted_doc["thread_id"] == "thread_1"
    assert inserted_doc["admin_id"] == "admin_1"
    assert inserted_doc["chat_name"] == "Support Chat"
    assert "start_timestamp" in inserted_doc


def test_insert_into_conversations(mock_mongo):
    """Test inserting a conversation and updating thread end_timestamp."""
    _, mock_conversations = mock_mongo
    mock_conversations.insert_one = MagicMock()
    mock_mongo[0].update_one = MagicMock()

    conversation = {
        "conversation_id": "conv_1",
        "query": "What's up?",
        "response": "Not much!",
        "timestamp": datetime.utcnow().isoformat(),
        "excel_path": "/path/to/excel.xlsx"
    }

    insert_into_conversations("thread_1", "admin_1", conversation)

    mock_conversations.insert_one.assert_called_once()
    mock_mongo[0].update_one.assert_called_once()
    inserted_doc = mock_conversations.insert_one.call_args[0][0]
    assert inserted_doc["conversation_id"] == "conv_1"
    assert inserted_doc["query"] == "What's up?"
    assert inserted_doc["response"] == "Not much!"
    assert inserted_doc["excel_path"] == "/path/to/excel.xlsx"
