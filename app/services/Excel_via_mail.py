
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
import logging
import traceback
import subprocess  # For PDF password protection
import openpyxl
from openpyxl.worksheet.worksheet import Worksheet




logger = logging.getLogger(__name__)

def send_email_with_attachment(recipient_email: str, file_path: str, password: str):
    """Sends an email with an Excel or PDF attachment, password-protected."""
    try:
        file_type = file_path.split(".")[-1].lower()
        protected_file_path = file_path  # default to the original file
        if file_type == "xlsx":
            # Load the workbook
            workbook = openpyxl.load_workbook(file_path)

            # Protect all sheets in the workbook
            for sheet_name in workbook.sheetnames:
                sheet: Worksheet = workbook[sheet_name]
                sheet.protection.set_password(password)

            # Save the protected workbook to a new file
            protected_file_path = file_path.replace(".xlsx", "_protected.xlsx")
            workbook.save(protected_file_path)
            logger.info(f"Excel file password protected and saved to {protected_file_path}")
            # logger.info(f"Excel file password protected")

        elif file_type == "pdf":
            # Password protect PDF using qpdf (install: `apt-get install qpdf` or `brew install qpdf`)
            protected_file_path = file_path.replace(".pdf", "_protected.pdf")

            cmd = [
                "qpdf",
                "--encrypt", password, password, "256", # encryption key length
                "--modify-permission=print", # Allow printing
                "--", file_path, protected_file_path
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                logger.info(f"PDF file password protected and saved to {protected_file_path}")
            except subprocess.CalledProcessError as e:
                logger.error(f"qpdf error: {e.stderr}")
                raise Exception(f"Failed to password protect PDF: {e.stderr}")
        else:
            raise ValueError("Unsupported file type.  Must be 'xlsx' or 'pdf'")

        # Email configuration
        sender_email = "loans24otp@gmail.com"  # Replace
        sender_password = "laca zuzp pmuw xrac"  # Replace

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = "Your Loan Data"

        body = f"Please find attached your loan data file.  The password to open the file is: {password}"
        msg.attach(MIMEText(body, 'plain'))

        # Attach the file
        with open(protected_file_path, "rb") as f:
            attachment = MIMEApplication(f.read(), _subtype="octet-stream")  # Generic type

            attachment.add_header(
                'Content-Disposition', 'attachment',
                filename=os.path.basename(protected_file_path)
            )
            msg.attach(attachment)

        # Send the email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:  # Or your SMTP server
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)

        logger.info(f"Email sent to {recipient_email} with password-protected file.")

    except Exception as e:
        logger.error(f"Email sending error: {str(e)}")
        logger.debug(traceback.format_exc())
        raise

    finally:
        # Clean up the protected file
        if file_type in ("xlsx", "pdf"):
            try:
                os.remove(protected_file_path)
                logger.debug(f"Deleted temporary password-protected file: {protected_file_path}")
            except Exception as cleanup_err:
                logger.warning(f"Failed to delete temporary file: {cleanup_err}")