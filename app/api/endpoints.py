
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from app.services.query_generator import generate_sql
from app.services.database import execute_sql_query
from app.services.result_formatter import format_results
from app.models.models import *
from app.models.admin import AdminSignup, AdminLogin, TokenResponse
from app.services.auth_services import admin_signup, admin_login
from app.core.security import get_current_admin
from app.services.visualization_service import get_chart_suggestion, generate_plotly_chart
from app.services.redis_service import *
from app.services.mongo_service import *
from app.services.excel_service import generate_excel, get_excel_path
import uuid
import os
import logging
from datetime import datetime
from app.core.config import *

router = APIRouter()

@router.post("/admin/signup/", response_model=dict)
async def signup(admin: AdminSignup):
    """Registers a new admin"""
    response = await admin_signup(admin)
    if "error" in response:
        raise HTTPException(status_code=400, detail=response["error"])
    return response

@router.post("/admin/login/", response_model=TokenResponse)
async def login(admin: AdminLogin):
    """Logs in an admin and returns JWT token"""
    token_data = await admin_login(admin.email, admin.password)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return token_data

import time
import random

def generate_id():
    """Generate a unique string ID without using uuid"""
    timestamp = int(time.time() * 1000)  # Milliseconds since epoch
    random_part = random.randint(1000, 9999)
    return f"{timestamp}_{random_part}"

@router.post("/generate-response/")
async def process_user_input(request: UserInputRequest, admin: dict = Depends(get_current_admin)):
    """Process user query after authentication"""
    admin_id = admin["admin_id"]
    sql_query = generate_sql(request.user_input, request.thread_id if hasattr(request, "thread_id") else None)

    logging.info(sql_query)
    if sql_query.lower() == "unwanted":
        return {"message": "I will answer only loan-related questions."}
    elif sql_query.lower() == "restricted":
        return {"message": "You can only read the data; modifications or creations are not allowed."}
    elif sql_query.lower() == "ensitive":
        return {"message": "I won’t provide any sensitive data of users."}

    elif sql_query.lower().startswith("select"):
        query_results = execute_sql_query(sql_query)
        logging.info(f"Query Results Type: {type(query_results)}")
        formatted_response = format_results(query_results)
        # chart_type = get_chart_suggestion(query_results, request.user_input)
        # chart_img = generate_plotly_chart(query_results, chart_type, request.user_input)

        conversation_id = generate_id()

        # ✅ Create conversation record
        conversation_record = {
            "conversation_id": conversation_id,
            "query": request.user_input,
            "response": formatted_response,
            "visualization": "chart_img",
            "timestamp": datetime.utcnow().isoformat(),
            "data_type": ["chart_type"] if "chart_type" else [],
            "excel_path": EXCEL_STORAGE_PATH+f"/{conversation_id}"
        }

        # ✅ If thread_id exists, insert only into conversations
        if hasattr(request, "thread_id") and request.thread_id:
            append_result = append_conversation(request.thread_id, conversation_record)
            insert_into_conversations(request.thread_id, admin_id, conversation_record)

            response_data = {
                "sql_query": sql_query,
                "results": formatted_response,
                "chart_type": "chart_type",
                "chart_image_url": "chart_img",
                "message": "",
                "thread_id": request.thread_id,
                "conversation_count": append_result["total_conversations"],
                "conversation_id": conversation_id,
                "excel_path": EXCEL_STORAGE_PATH+f"/{conversation_id}"
            }

        # ✅ If no thread_id, create a new thread & insert first conversation
        else:
            thread_id = generate_id()

            insert_into_threads(thread_id, admin_id, request.user_input)  # ✅ Insert new thread
            insert_into_conversations(thread_id, admin_id, conversation_record)  # ✅ Insert first conversation

            # ✅ Push to Redis
            thread_data = {
                "thread_id": thread_id,
                "admin_id": admin_id,
                "chat_name": request.user_input,
                "conversations": [conversation_record]
            }
            insert_into_redis(thread_data)

            response_data = {
                "sql_query": sql_query,
                "results": formatted_response,
                "chart_type": "chart_type",
                "chart_image_url": "chart_img",
                "message": "",
                "thread_id": thread_id,
                "conversation_id": conversation_id,
                "excel_path":EXCEL_STORAGE_PATH+f"/{conversation_id}"
            }

        await generate_excel(conversation_id, query_results)
        return response_data

@router.get("/admin/dashboard/")
async def dashboard(admin: dict = Depends(get_current_admin)):
    """Protected admin dashboard"""
    return {"message": f"Welcome, {admin['email']}!"}

@router.get("/download-excel/{conversation_id}/")
async def download_excel(conversation_id: str, admin: dict = Depends(get_current_admin)):
    """Endpoint to download an Excel file based on conversation ID."""
    file_path = get_excel_path(conversation_id)

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"conversation_{conversation_id}.xlsx"
    )

@router.delete("/migrate-thread/{thread_id}")
async def migrate_and_delete_thread(thread_id: str, admin: dict = Depends(get_current_admin)):
    """
    Migrate a thread to MongoDB and delete it from Redis.
    """
    try:
        result = delete_from_redis(thread_id)

        if isinstance(result, tuple):  
            raise HTTPException(status_code=result[1], detail=result[0]["message"])

        return {"message": "Thread successfully migrated and deleted from Redis."}

    except Exception as e:
        logging.error(f"Error migrating thread {thread_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/threads")
async def fetch_threads_and_conversations(
    admin: dict = Depends(get_current_admin), 
    thread_id: str = None, 
    page: int = 1, 
    limit: int = 10
):
    """
    Fetch all threads for an admin OR fetch paginated conversations if thread_id is provided.
    """
    try:
        admin_id = admin["admin_id"]  # Extract admin_id from authenticated user

        if thread_id:  # Fetch paginated conversations if thread_id exists
            conversation_data = get_conversations_by_thread(admin_id, thread_id, page, limit)

            if not conversation_data["conversations"]:
                raise HTTPException(status_code=404, detail="No conversation found for this thread.")

            return conversation_data

        else:  # Fetch all threads if thread_id is NOT provided
            threads = get_threads_by_admin(admin_id,page,limit)

            if not threads:
                return {"message": "No chat history found.", "threads": []}

            return {"threads": threads}

    except Exception as e:
        logging.error(f"Error fetching data for admin {admin_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")




# from fastapi import APIRouter, HTTPException
# from app.services.query_generator import generate_sql
# from app.services.database import execute_sql_query
# from app.services.result_formatter import format_results
# from app.models.models import *
# from fastapi import APIRouter, HTTPException, Depends
# from app.models.admin import AdminSignup, AdminLogin, TokenResponse
# from app.services.auth_services import admin_signup, admin_login
# from app.core.security import get_current_admin
# from app.services.visualization_service import get_chart_suggestion, generate_plotly_chart
# from app.services.redis_service import *
# import uuid
# from datetime import datetime
# import os
# from fastapi.responses import FileResponse
# from app.services.excel_service import generate_excel
# from app.services.redis_service import get_excel_path

# router = APIRouter()
# @router.post("/generate-response/")
# async def process_user_input(
#     request: UserInputRequest, 
#     admin: dict = Depends(get_current_admin)
# ):  
#     admin_id = admin["admin_id"]
#     sql_query = generate_sql(request.user_input, request.thread_id if hasattr(request, "thread_id") else None)

#     logging.info(sql_query)
#     if sql_query.lower() in ["unwanted", "restricted", "sensitive"]:
#         return {"message": sql_query}
    
#     elif sql_query.lower().startswith("select"):
#         query_results = execute_sql_query(sql_query)
#         logging.info(f"Query Results Type: {type(query_results)}")
#         formatted_response = format_results(query_results)
#         chart_type = get_chart_suggestion(query_results, request.user_input)
#         chart_img = generate_plotly_chart(query_results, chart_type, request.user_input)

#         conversation_id = str(uuid.uuid4())  # Generate UUID

#         conversation_record = ConversationRecord(
#             conversation_id=conversation_id,
#             query=request.user_input,
#             response=formatted_response,
#             visualization=chart_img,
#             timestamp=datetime.utcnow().isoformat(),
#             data_type=[chart_type] if chart_type else []
#         )

#         if hasattr(request, "thread_id") and request.thread_id:
#             append_result = append_conversation(request.thread_id, conversation_record.dict())
#             response_data = {
#                 "sql_query": sql_query,
#                 "results": formatted_response,
#                 "chart_type": chart_type,
#                 "chart_image_url": chart_img,
#                 "message": "Conversation appended",
#                 "thread_id": request.thread_id,
#                 "conversation_count": append_result["total_conversations"],
#                 "conversation_id": conversation_id
#             }
#         else:
#             thread_id = str(uuid.uuid4())
#             thread_data = ThreadInsertRequest(
#                 thread_id=thread_id,
#                 admin_id=admin_id,
#                 chat_name=request.user_input,
#                 conversations=[conversation_record]
#             )
#             insert_into_redis(thread_data.dict())
#             response_data = {
#                 "sql_query": sql_query,
#                 "results": formatted_response,
#                 "chart_type": chart_type,
#                 "chart_image_url": chart_img,
#                 "message": "New chat thread created",
#                 "thread_id": thread_id,
#                 "conversation_id": conversation_id
#             }

#         # ✅ Generate Excel asynchronously
#         await generate_excel(conversation_id, query_results)

#         return response_data

# @router.post("/admin/signup/", response_model=dict)
# async def signup(admin: AdminSignup):
#     """Registers a new admin"""
#     response = await admin_signup(admin)
#     if "error" in response:
#         raise HTTPException(status_code=400, detail=response["error"])
#     return response

# @router.post("/admin/login/", response_model=TokenResponse)
# async def login(admin: AdminLogin):
#     """Logs in an admin and returns JWT token"""
#     token_data = await admin_login(admin.email, admin.password)
#     if not token_data:
#         raise HTTPException(status_code=401, detail="Invalid email or password")
#     return token_data

# @router.get("/admin/dashboard/")
# async def dashboard(admin: dict = Depends(get_current_admin)):
#     """Protected admin dashboard"""
#     return {"message": f"Welcome, {admin['email']}!"}


# @router.get("/download-excel/{conversation_id}/")
# async def download_excel(conversation_id: str, admin: dict = Depends(get_current_admin)):
#     """Endpoint to download an Excel file based on conversation ID."""
#     file_path = get_excel_path(conversation_id)
    
#     if not file_path or not os.path.exists(file_path):
#         raise HTTPException(status_code=404, detail="File not found")

#     return FileResponse(
#         file_path,
#         media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         filename=f"conversation_{conversation_id}.xlsx"
#     )

# @router.delete("/migrate-thread/{thread_id}")
# async def migrate_and_delete_thread(thread_id: str, admin: dict = Depends(get_current_admin)):
#     """
#     Migrate a thread to MongoDB and delete it from Redis.
#     """
#     try:
#         result = delete_from_redis(thread_id)
        
#         if isinstance(result, tuple):  # Check if it returned an error
#             raise HTTPException(status_code=result[1], detail=result[0]["message"])

#         return {"message": "Thread successfully migrated and deleted from Redis."}

#     except Exception as e:
#         logging.error(f"Error migrating thread {thread_id}: {str(e)}")
#         raise HTTPException(status_code=500, detail="Internal Server Error")
