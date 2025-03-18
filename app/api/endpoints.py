from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
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
from app.services.extract_tables_service import *
from app.core.config import *
from app.core.helper import *
import os
import logging
import traceback
from datetime import datetime, timedelta
from app.core.config import config
from app.services.database import db

# Configure logging
logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/admin/login/", response_model=TokenResponse)
async def login(admin: AdminLogin):
    """Logs in an admin and returns JWT token"""
    try:
        token_data = await admin_login(admin.email, admin.password)
        if not token_data:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        return token_data
    except HTTPException as he:
        # Re-raise HTTP exceptions as they're already handled
        raise he
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error during login")

@router.post("/generate-response/")
async def process_user_input(request: UserInputRequest, admin: dict = Depends(get_current_admin)):
    """Process user query, generate SQL, execute query and return formatted results with visualization"""
    try:
        admin_id = admin["admin_id"]        
        # Generate SQL from user input
        try:
            sql_query = generate_sql(request.user_input, request.thread_id if hasattr(request, "thread_id") else None)
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to generate SQL query")

        # Handle special query cases
        if sql_query.lower() == "unwanted":
            return {"message": "I will answer only loan-related questions."}
        elif sql_query.lower() == "restricted":
            return {"message": "You can only read the data; modifications or creations are not allowed."}
        elif sql_query.lower() == "ensitive":
            return {"message": "I won't provide any sensitive data of users."}

        elif sql_query.lower().startswith("select"):
            # Execute SQL query
            try:
                query_results = execute_sql_query(sql_query)
            except Exception as e:
                logger.debug(traceback.format_exc())
                raise HTTPException(status_code=500, detail="Failed to execute database query")
            
            # Format results
            try:
                formatted_response = format_results(query_results)
                tables, cols = extract_tables_and_columns(sql_query)
                logger.debug(f"Extracted tables: {tables}, columns: {cols}")
            except Exception as e:
                logger.debug(traceback.format_exc())
                raise HTTPException(status_code=500, detail="Failed to format query results")

            conversation_id = generate_id()
            logger.debug(f"Generated conversation ID: {conversation_id}")

            # Create conversation record
            conversation_record = {
                "conversation_id": conversation_id,
                "query": request.user_input,
                "response": formatted_response,
                "visualization": "chart_img",
                "timestamp": datetime.utcnow().isoformat(),
                "data_type": tables,
                "cols": cols,
                "rows": len(query_results),
                "excel_path": EXCEL_STORAGE_PATH+f"/{conversation_id}"
            }

            # If thread_id exists, insert only into conversations
            if hasattr(request, "thread_id") and request.thread_id:
                try:
                    logger.info(f"Appending to existing thread {request.thread_id}")
                    append_result = append_conversation(request.thread_id, conversation_record)
                    insert_into_conversations(request.thread_id, admin_id, conversation_record)
                except Exception as e:
                    logger.error(f"Failed to update existing thread: {str(e)}")
                    logger.debug(traceback.format_exc())
                    raise HTTPException(status_code=500, detail="Failed to update conversation history")

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

            # If no thread_id, create a new thread & insert first conversation
            else:
                thread_id = generate_id()
                logger.info(f"Creating new thread with ID: {thread_id}")
                
                try:
                    insert_into_threads(thread_id, admin_id, request.user_input)
                    insert_into_conversations(thread_id, admin_id, conversation_record)
                except Exception as e:
                    logger.error(f"Failed to create new thread: {str(e)}")
                    logger.debug(traceback.format_exc())
                    raise HTTPException(status_code=500, detail="Failed to create new conversation thread")

                # Push to Redis
                try:
                    thread_data = {
                        "thread_id": thread_id,
                        "admin_id": admin_id,
                        "chat_name": request.user_input,
                        "conversations": [conversation_record]
                    }
                    insert_into_redis(thread_data)
                    logger.debug("Successfully inserted thread data into Redis")
                except Exception as e:
                    logger.error(f"Redis insertion error: {str(e)}")
                    logger.debug(traceback.format_exc())
                    # Continue even if Redis fails, as it might be a caching layer

                response_data = {
                    "sql_query": sql_query,
                    "results": formatted_response,
                    "chart_type": "chart_type",
                    "chart_image_url": "chart_img",
                    "message": "",
                    "thread_id": thread_id,
                    "conversation_id": conversation_id,
                    "excel_path": EXCEL_STORAGE_PATH+f"/{conversation_id}"
                }

            # Generate Excel file
            try:
                await generate_excel(conversation_id, query_results)
            except Exception as e:
                logger.error(f"Excel generation error: {str(e)}")
                logger.debug(traceback.format_exc())
                # Continue even if Excel generation fails

            return response_data
        else:
            logger.warning(f"Invalid SQL query generated: {sql_query}")
            raise HTTPException(status_code=400, detail="Failed to generate a valid SQL query")
            
    except HTTPException as he:
        # Re-raise HTTP exceptions as they're already handled
        raise he
    except Exception as e:
        logger.error(f"Unhandled error in process_user_input: {str(e)}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail="An unexpected error occurred processing your request")

@router.get("/download-excel/{conversation_id}/")
async def download_excel(conversation_id: str, admin: dict = Depends(get_current_admin)):
    """Endpoint to download an Excel file based on conversation ID with authorization check"""
    try:
        logger.info(f"Excel download requested for conversation {conversation_id} by admin {admin['email']}")
        
        file_path = get_excel_path(conversation_id)
        logger.debug(f"Excel file path: {file_path}")

        if not file_path or not os.path.exists(file_path):
            logger.warning(f"Excel file not found for conversation {conversation_id}")
            raise HTTPException(status_code=404, detail="File not found")

        logger.info(f"Serving Excel file for conversation {conversation_id}")
        return FileResponse(
            file_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"conversation_{conversation_id}.xlsx"
        )
    except HTTPException as he:
        # Re-raise HTTP exceptions as they're already handled
        raise he
    except Exception as e:
        logger.error(f"Excel download error: {str(e)}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to download Excel file")

@router.get("/threads")
async def fetch_threads_and_conversations(
    admin: dict = Depends(get_current_admin), 
    thread_id: str = None, 
    page: int = 1, 
    limit: int = 10
):
    """
    Fetch all threads for an admin or fetch paginated conversations for a specific thread
    """
    try:
        admin_id = admin["admin_id"]
        logger.info(f"Fetching {'conversations for thread ' + thread_id if thread_id else 'all threads'} for admin {admin_id}")

        if thread_id:  # Fetch paginated conversations if thread_id exists
            try:
                conversation_data = get_conversations_by_thread(admin_id, thread_id, page, limit)
                if not conversation_data["conversations"]:
                    logger.warning(f"No conversations found for thread {thread_id}")
                    raise HTTPException(status_code=404, detail="No conversation found for this thread.")
                
                logger.info(f"Retrieved {len(conversation_data['conversations'])} conversations for thread {thread_id}")
                return conversation_data
            except HTTPException as he:
                raise he
            except Exception as e:
                logger.error(f"Error retrieving conversations: {str(e)}")
                logger.debug(traceback.format_exc())
                raise HTTPException(status_code=500, detail="Failed to retrieve conversations")

        else:  # Fetch all threads if thread_id is NOT provided
            try:
                threads = get_threads_by_admin(admin_id, page, limit)
                logger.info(f"Retrieved {len(threads) if threads else 0} threads for admin {admin_id}")
                
                if not threads:
                    return {"message": "No chat history found.", "threads": []}

                return {"threads": threads}
            except Exception as e:
                logger.error(f"Error retrieving threads: {str(e)}")
                logger.debug(traceback.format_exc())
                raise HTTPException(status_code=500, detail="Failed to retrieve threads")

    except HTTPException as he:
        # Re-raise HTTP exceptions as they're already handled
        raise he
    except Exception as e:
        logger.error(f"Unhandled error in fetch_threads_and_conversations: {str(e)}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal Server Error")

otp_collection = db["otp"]
@router.post("/admin/request-otp/")
async def request_otp(background_tasks: BackgroundTasks):
    """Generate and send OTP to the configured admin email for registration verification"""
    try:
        logger.info(f"OTP requested for admin email: {config.ADMIN_EMAIL}")
        
        # Generate a 6-digit OTP
        otp = generate_otp(6)
        logger.debug("OTP generated successfully")
        
        # Store OTP in MongoDB with expiration time (5 minutes)
        expiry_time = datetime.utcnow() + timedelta(minutes=5)
        
        try:
            # Check if there's an existing OTP for this email and update it
            existing_otp = otp_collection.find_one({"email": config.ADMIN_EMAIL})
            if existing_otp:
                logger.debug(f"Updating existing OTP for {config.ADMIN_EMAIL}")
                otp_collection.update_one(
                    {"email": config.ADMIN_EMAIL},
                    {"$set": {
                        "otp": otp,
                        "expiry_time": expiry_time,
                        "created_at": datetime.utcnow()
                    }}
                )
            else:
                logger.debug(f"Creating new OTP for {config.ADMIN_EMAIL}")
                otp_collection.insert_one({
                    "email": config.ADMIN_EMAIL,
                    "otp": otp,
                    "expiry_time": expiry_time,
                    "created_at": datetime.utcnow()
                })
            logger.info(f"OTP stored in database for {config.ADMIN_EMAIL}")
        except Exception as db_error:
            logger.error(f"Database error storing OTP: {str(db_error)}")
            logger.debug(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Failed to store OTP")
        
        # Send OTP email in background
        background_tasks.add_task(send_email, config.ADMIN_EMAIL, otp)
        logger.info(f"OTP email queued for sending to {config.ADMIN_EMAIL}")
        
        return {"message": f"OTP sent to {config.ADMIN_EMAIL}", "email": config.ADMIN_EMAIL}
    
    except HTTPException as he:
        # Re-raise HTTP exceptions as they're already handled
        raise he
    except Exception as e:
        logger.error(f"Error generating or sending OTP: {str(e)}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to generate and send OTP")

@router.post("/admin/signup/", response_model=dict)
async def signup(admin: AdminSignup):
    """Register a new admin account with OTP verification"""
    try:
        logger.info(f"Processing admin signup for {config.ADMIN_EMAIL}")
        
        # Validate OTP
        try:
            # Check if OTP exists and is valid
            otp_record = otp_collection.find_one({"email": config.ADMIN_EMAIL})
            
            if not otp_record:
                logger.warning(f"No OTP found for {config.ADMIN_EMAIL}")
                raise HTTPException(status_code=400, detail="No OTP found. Please request an OTP first.")
            
            if otp_record["otp"] != admin.otp:
                logger.warning(f"Invalid OTP provided for {config.ADMIN_EMAIL}")
                raise HTTPException(status_code=400, detail="Invalid OTP. Please try again.")
            
            # Check if OTP has expired
            if datetime.utcnow() > otp_record["expiry_time"]:
                logger.warning(f"Expired OTP for {config.ADMIN_EMAIL}")
                raise HTTPException(status_code=400, detail="OTP has expired. Please request a new OTP.")
            
            logger.info(f"OTP validation successful for {config.ADMIN_EMAIL}")
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"OTP validation error: {str(e)}")
            logger.debug(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Failed to validate OTP")
        
        # Proceed with admin signup if OTP is valid
        try:
            response = await admin_signup(admin)
            if "error" in response:
                logger.warning(f"Admin signup failed: {response['error']}")
                raise HTTPException(status_code=400, detail=response["error"])
            
            logger.info(f"Admin signup successful for {config.ADMIN_EMAIL}")
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Admin signup error: {str(e)}")
            logger.debug(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Failed to create admin account")
        
        # Delete the used OTP
        try:
            otp_collection.delete_one({"email": config.ADMIN_EMAIL})
            logger.debug(f"Used OTP deleted for {config.ADMIN_EMAIL}")
        except Exception as e:
            logger.error(f"Failed to delete used OTP: {str(e)}")
            # Continue even if OTP deletion fails
        
        return response
    except HTTPException as he:
        # Re-raise HTTP exceptions as they're already handled
        raise he
    except Exception as e:
        logger.error(f"Unhandled error in admin signup: {str(e)}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error during signup")