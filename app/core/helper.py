import time
import random
import string
from app.core.config import config
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.services.database import client, db
import logging
import traceback

# Configure logging
logger = logging.getLogger(__name__)

def generate_id():
    """Generate a unique string ID based on timestamp and random number"""
    timestamp = int(time.time() * 1000)  # Milliseconds since epoch
    random_part = random.randint(1000, 9999)
    return f"{timestamp}_{random_part}"

def generate_otp(length=6):
    """Generate a random numeric OTP of specified length for verification purposes"""
    digits = string.digits
    return ''.join(random.choice(digits) for _ in range(length))

otp_collection = db["otp"]
async def send_email(email, otp):
    """Send OTP verification email using configured SMTP settings"""
    try:
        logger.info(f"Preparing to send OTP email to {email}")
        message = MIMEMultipart()
        message["From"] = config.EMAIL_USER
        message["To"] = email
        message["Subject"] = "Your OTP for Admin Registration"
        
        body = f"""
        <html>
        <body>
            <h2>Admin Registration OTP</h2>
            <p>Your One-Time Password (OTP) for admin registration is: <strong>{otp}</strong></p>
            <p>This OTP will expire in 5 minutes.</p>
        </body>
        </html>
        """
        
        message.attach(MIMEText(body, "html"))
        
        server = smtplib.SMTP(config.EMAIL_HOST, config.EMAIL_PORT)
        server.starttls()
        server.login(config.EMAIL_USER, config.EMAIL_PASSWORD)
        server.sendmail(config.EMAIL_USER, email, message.as_string())
        server.quit()
        logger.info(f"OTP email sent successfully to {email}")
        return True
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending email to {email}: {str(e)}")
        logger.debug(traceback.format_exc())
        return False
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {str(e)}")
        logger.debug(traceback.format_exc())
        return False