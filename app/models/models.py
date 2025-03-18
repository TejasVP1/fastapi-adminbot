from pydantic import BaseModel
from typing import List, Optional
from typing import Optional
from uuid import UUID

class UserInputRequest(BaseModel):
    user_input: str
    thread_id: str = None  # Optional UUID field
    
class ConversationRecord(BaseModel):
    conversation_id: str
    query: str
    response: str
    visualization: Optional[str] = None
    timestamp: str
    data_type: List[str]
    excel_path: str

class ThreadInsertRequest(BaseModel):
    thread_id: str
    admin_id: str
    chat_name: str
    conversations: List[ConversationRecord] = []
