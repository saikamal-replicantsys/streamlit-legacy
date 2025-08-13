# email_parsing_agent.py
import os
import re
import json
import email
import imaplib
import smtplib
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl
from email.header import decode_header
import hashlib

# Internal imports
from fileparser import FileParser
from rfq_agent import RFQFieldGenerator
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Email provider configurations
EMAIL_PROVIDERS = {
    'gmail': {
        'imap_server': 'imap.gmail.com',
        'imap_port': 993,
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'use_ssl': True
    },
    'outlook': {
        'imap_server': 'outlook.office365.com',
        'imap_port': 993,
        'smtp_server': 'smtp-mail.outlook.com',
        'smtp_port': 587,
        'use_ssl': True
    },
    'yahoo': {
        'imap_server': 'imap.mail.yahoo.com',
        'imap_port': 993,
        'smtp_server': 'smtp.mail.yahoo.com',
        'smtp_port': 587,
        'use_ssl': True
    },
    'custom': {
        'imap_server': '',
        'imap_port': 993,
        'smtp_server': '',
        'smtp_port': 587,
        'use_ssl': True
    }
}

class EmailConfig(BaseModel):
    """Model for email configuration"""
    provider: str  # gmail, outlook, yahoo, custom
    email_address: str
    password: str
    imap_server: Optional[str] = None
    imap_port: Optional[int] = None
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    use_ssl: bool = True

class EmailAttachment(BaseModel):
    """Model for email attachment data"""
    filename: str
    content: bytes
    content_type: str
    size: int
    message_id: str

class QuoteEmail(BaseModel):
    """Model for quote-related email data"""
    email_id: str
    subject: str
    sender: str
    date: datetime
    body: str
    indent_id: Optional[str] = None
    attachments: List[EmailAttachment] = []
    processed: bool = False
    extracted_quotes: List[Dict[str, Any]] = []

class EmailParsingAgent:
    """
    Email Parsing Agent for Purchase & Procurement Department
    Automatically fetches quotation files from email inbox based on indent IDs
    Supports Gmail, Outlook, Yahoo, and custom IMAP/SMTP servers
    """
    
    def __init__(self, config_path: str = "email_config.json"):
        self.config_path = config_path
        self.email_config = None
        self.imap_connection = None
        self.file_parser = FileParser()
        self.rfq_generator = RFQFieldGenerator()
        self.quotes_storage_path = Path("quotes_storage")
        self.by_indent_path = self.quotes_storage_path / "by_indent_id"
        
        # Ensure storage directories exist
        self.quotes_storage_path.mkdir(exist_ok=True)
        self.by_indent_path.mkdir(exist_ok=True)
        
        # Email filtering patterns - more flexible
        self.indent_patterns = [
            r'indent\s*id\s*:?\s*(\d+)',          # "indent id: 1234" or "indent id 1234"
            r'indent\s*#?\s*(\d+)',               # "indent 1234" or "indent #1234"
            r'\bid\s*:?\s*(\d+)',                 # "id: 1234" or "id 1234"
            r'req(?:uest)?\s*id\s*:?\s*(\d+)',    # "req id: 1234" or "request id 1234"
            r'requirement\s*id\s*:?\s*(\d+)',     # "requirement id: 1234"
            r'rfq\s*:?\s*(\d+)',                  # "rfq: 1234" or "rfq 1234"
            r'quotation\s*:?\s*(\d+)',            # "quotation: 1234"
            r'quote\s*:?\s*(\d+)'                 # "quote: 1234"
        ]
        
        # Supported quote file extensions
        self.quote_file_extensions = {'.pdf', '.xlsx', '.xls', '.docx', '.doc', '.csv', '.txt'}
        
        # Load email configuration if exists
        self._load_email_config()
        
        logger.info("Email Parsing Agent initialized")

    def _load_email_config(self) -> bool:
        """Load email configuration from file"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                self.email_config = EmailConfig(**config_data)
                logger.info(f"Email configuration loaded for {self.email_config.email_address}")
                return True
            except Exception as e:
                logger.error(f"Error loading email config: {str(e)}")
                return False
        return False

    def save_email_config(self, config: EmailConfig) -> bool:
        """Save email configuration to file"""
        try:
            # Merge with provider defaults
            provider_config = EMAIL_PROVIDERS.get(config.provider, EMAIL_PROVIDERS['custom'])
            
            if not config.imap_server:
                config.imap_server = provider_config['imap_server']
            if not config.imap_port:
                config.imap_port = provider_config['imap_port']
            if not config.smtp_server:
                config.smtp_server = provider_config['smtp_server']
            if not config.smtp_port:
                config.smtp_port = provider_config['smtp_port']
            
            self.email_config = config
            
            with open(self.config_path, 'w') as f:
                json.dump(config.dict(), f, indent=2)
            
            logger.info(f"Email configuration saved for {config.email_address}")
            return True
        except Exception as e:
            logger.error(f"Error saving email config: {str(e)}")
            return False

    async def connect_to_email(self) -> bool:
        """Connect to email server using IMAP"""
        if not self.email_config:
            logger.error("No email configuration available")
            return False
        
        try:
            # Create IMAP connection
            if self.email_config.use_ssl:
                self.imap_connection = imaplib.IMAP4_SSL(
                    self.email_config.imap_server, 
                    self.email_config.imap_port
                )
            else:
                self.imap_connection = imaplib.IMAP4(
                    self.email_config.imap_server, 
                    self.email_config.imap_port
                )
            
            # Login
            self.imap_connection.login(
                self.email_config.email_address, 
                self.email_config.password
            )
            
            # Select inbox
            self.imap_connection.select('INBOX')
            
            logger.info(f"Successfully connected to {self.email_config.provider} email server")
            return True
            
        except Exception as e:
            logger.error(f"Email connection failed: {str(e)}")
            logger.error(f"Provider: {self.email_config.provider}")
            logger.error(f"Server: {self.email_config.imap_server}:{self.email_config.imap_port}")
            logger.error(f"Email: {self.email_config.email_address}")
            logger.error(f"SSL: {self.email_config.use_ssl}")
            return False

    def disconnect_from_email(self):
        """Disconnect from email server"""
        if self.imap_connection:
            try:
                self.imap_connection.close()
                self.imap_connection.logout()
                logger.info("Disconnected from email server")
            except:
                pass
            finally:
                self.imap_connection = None

    def extract_indent_id(self, subject: str) -> Optional[str]:
        """
        Extract indent ID from email subject using various patterns
        """
        if not subject:
            return None
            
        subject_lower = subject.lower().strip()
        logger.info(f"Extracting indent ID from: '{subject}'")
        
        for i, pattern in enumerate(self.indent_patterns, 1):
            match = re.search(pattern, subject_lower, re.IGNORECASE)
            if match:
                indent_id = match.group(1)
                logger.info(f"✅ Pattern {i} matched: '{pattern}' -> Indent ID: {indent_id}")
                return indent_id
            else:
                logger.debug(f"❌ Pattern {i} no match: '{pattern}'")
        
        logger.info(f"❌ No indent ID found in subject: '{subject}'")
        return None

    async def search_emails(self, days_back: int = 30, max_results: int = 100) -> List[str]:
        """
        Search for emails containing potential quotes/RFQs using IMAP
        Robust search strategy: Start simple and expand if needed
        """
        if not self.imap_connection:
            if not await self.connect_to_email():
                return []
        
        try:
            # Strategy 1: Try keyword-based search first
            logger.info("Trying keyword-based search...")
            quote_keywords = ['indent', 'quotation', 'quote', 'rfq', 'proposal', 'request', 'purchase', 'tender']
            
            found_emails = set()
            
            # Search for each keyword
            for keyword in quote_keywords:
                try:
                    typ, message_ids = self.imap_connection.search(None, f'SUBJECT "{keyword}"')
                    if typ == 'OK' and message_ids[0]:
                        keyword_emails = message_ids[0].split()
                        found_emails.update(keyword_emails)
                        logger.info(f"Keyword '{keyword}': found {len(keyword_emails)} emails")
                except Exception as e:
                    logger.warning(f"Search for keyword '{keyword}' failed: {str(e)}")
            
            # Strategy 2: If no emails found with keywords, try date-based search
            if not found_emails:
                logger.info("No emails found with keywords, trying date-based search...")
                since_date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
                try:
                    typ, message_ids = self.imap_connection.search(None, f'SINCE "{since_date}"')
                    if typ == 'OK' and message_ids[0]:
                        found_emails.update(message_ids[0].split())
                        logger.info(f"Date search: found {len(found_emails)} emails since {since_date}")
                except Exception as e:
                    logger.warning(f"Date search failed: {str(e)}")
            
            # Strategy 3: If still no emails, get recent emails (fallback)
            if not found_emails:
                logger.info("No emails found with date filter, getting recent emails...")
                try:
                    typ, message_ids = self.imap_connection.search(None, 'ALL')
                    if typ == 'OK' and message_ids[0]:
                        all_emails = message_ids[0].split()
                        # Get last 50 emails
                        found_emails.update(all_emails[-50:] if len(all_emails) > 50 else all_emails)
                        logger.info(f"Fallback search: found {len(found_emails)} recent emails")
                except Exception as e:
                    logger.warning(f"Fallback search failed: {str(e)}")
            
            if not found_emails:
                logger.warning("No emails found with any search strategy")
                return []
            
            # Convert to list and sort (most recent first)
            email_list = sorted(list(found_emails), reverse=True)
            
            # Now filter emails that actually contain relevant content
            logger.info(f"Filtering {len(email_list)} emails for relevant content...")
            filtered_emails = []
            
            for i, email_id in enumerate(email_list[:max_results * 2]):  # Check more than we need
                try:
                    # Get just the headers first (faster)
                    typ, header_data = self.imap_connection.fetch(email_id, '(BODY.PEEK[HEADER])')
                    if typ == 'OK' and header_data[0]:
                        header_text = header_data[0][1].decode('utf-8', errors='ignore')
                        subject_match = re.search(r'Subject: (.+)', header_text, re.IGNORECASE)
                        
                        if subject_match:
                            subject = subject_match.group(1).strip()
                            subject_lower = subject.lower()
                            
                            # Check if subject contains relevant keywords
                            has_keyword = any(keyword in subject_lower for keyword in quote_keywords)
                            
                            # For potential matches, check for attachments
                            has_attachments = False
                            if has_keyword or 'attachment' in header_text.lower():
                                try:
                                    typ, full_data = self.imap_connection.fetch(email_id, '(BODYSTRUCTURE)')
                                    if typ == 'OK' and full_data[0]:
                                        # Simple check for attachments in body structure
                                        has_attachments = 'attachment' in str(full_data[0]).lower()
                                except:
                                    pass
                            
                            if has_keyword or has_attachments:
                                filtered_emails.append(email_id)
                                logger.info(f"✅ Email {i+1}: '{subject[:50]}...' (keyword={has_keyword}, attachments={has_attachments})")
                                
                                if len(filtered_emails) >= max_results:
                                    break
                            else:
                                logger.debug(f"❌ Email {i+1}: '{subject[:50]}...' (no relevance)")
                        
                except Exception as e:
                    logger.warning(f"Error checking email {email_id}: {str(e)}")
                    # Include problematic emails to be safe
                    filtered_emails.append(email_id)
            
            # Final result
            result = [msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id) for msg_id in filtered_emails]
            logger.info(f"✅ Search complete: {len(result)} relevant emails found")
            
            return result
            
        except Exception as error:
            logger.error(f"Email search error: {error}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def _decode_header(self, header_value: str) -> str:
        """Decode email header value"""
        if not header_value:
            return ""
        
        decoded_parts = decode_header(header_value)
        decoded_string = ""
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                if encoding:
                    decoded_string += part.decode(encoding)
                else:
                    decoded_string += part.decode('utf-8', errors='ignore')
            else:
                decoded_string += str(part)
        
        return decoded_string

    async def get_email_details(self, email_id: str) -> Optional[QuoteEmail]:
        """
        Get detailed information about a specific email using IMAP
        """
        if not self.imap_connection:
            return None
            
        try:
            # Fetch email message
            typ, message_data = self.imap_connection.fetch(email_id.encode(), '(RFC822)')
            
            if typ != 'OK' or not message_data[0]:
                return None
            
            # Parse email message
            email_message = email.message_from_bytes(message_data[0][1])
            
            # Extract metadata
            subject = self._decode_header(email_message.get('Subject', ''))
            sender = self._decode_header(email_message.get('From', ''))
            date_str = email_message.get('Date', '')
            
            # Parse date
            try:
                from email.utils import parsedate_to_datetime
                email_date = parsedate_to_datetime(date_str)
            except:
                email_date = datetime.now()
            
            # Extract email body
            body = self._extract_email_body(email_message)
            
            # Extract indent ID from subject
            indent_id = self.extract_indent_id(subject)
            
            # Get attachments
            attachments = self._get_attachments(email_message, email_id)
            
            quote_email = QuoteEmail(
                email_id=email_id,
                subject=subject,
                sender=sender,
                date=email_date,
                body=body,
                indent_id=indent_id,
                attachments=attachments
            )
            
            logger.info(f"Retrieved email: {subject[:50]}... with {len(attachments)} attachments")
            return quote_email
            
        except Exception as e:
            logger.error(f"Error getting email details for {email_id}: {str(e)}")
            return None

    def _extract_email_body(self, email_message) -> str:
        """
        Extract text content from email message
        """
        body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        body = part.get_payload(decode=True).decode('utf-8')
                        break
                    except:
                        try:
                            body = part.get_payload(decode=True).decode('latin-1')
                            break
                        except:
                            continue
                elif content_type == "text/html" and "attachment" not in content_disposition and not body:
                    try:
                        body = part.get_payload(decode=True).decode('utf-8')
                        # Could add HTML stripping here if needed
                    except:
                        continue
        else:
            try:
                body = email_message.get_payload(decode=True).decode('utf-8')
            except:
                try:
                    body = email_message.get_payload(decode=True).decode('latin-1')
                except:
                    body = str(email_message.get_payload())
        
        return body

    def _get_attachments(self, email_message, email_id: str) -> List[EmailAttachment]:
        """
        Extract attachments from email message
        """
        attachments = []
        
        for part in email_message.walk():
            content_disposition = str(part.get("Content-Disposition"))
            
            if "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    # Decode filename if needed
                    filename = self._decode_header(filename)
                    
                    # Check if it's a potential quote file
                    file_ext = Path(filename).suffix.lower()
                    if file_ext in self.quote_file_extensions:
                        try:
                            # Get attachment data
                            attachment_data = part.get_payload(decode=True)
                            content_type = part.get_content_type()
                            
                            if attachment_data:
                                attachments.append(EmailAttachment(
                                    filename=filename,
                                    content=attachment_data,
                                    content_type=content_type,
                                    size=len(attachment_data),
                                    message_id=email_id
                                ))
                                
                        except Exception as e:
                            logger.error(f"Error extracting attachment {filename}: {str(e)}")
        
        logger.info(f"Found {len(attachments)} quote attachments")
        return attachments

    async def save_attachment(self, attachment: EmailAttachment, indent_id: str) -> str:
        """
        Save attachment to local storage organized by indent ID
        Avoids duplicates by checking existing files with same name and content
        """
        # Create indent-specific directory
        indent_dir = self.by_indent_path / f"indent_{indent_id}"
        indent_dir.mkdir(exist_ok=True)
        
        # Use exact filename (without timestamp) to check for duplicates
        exact_filename = attachment.filename
        exact_file_path = indent_dir / exact_filename
        
        # Calculate hash of new file content for comparison
        new_file_hash = hashlib.md5(attachment.content).hexdigest()
        
        # Check if file with exact name already exists
        if exact_file_path.exists():
            try:
                # Read existing file and calculate its hash
                with open(exact_file_path, 'rb') as f:
                    existing_content = f.read()
                existing_file_hash = hashlib.md5(existing_content).hexdigest()
                
                # If hashes match, file is identical - no need to save
                if new_file_hash == existing_file_hash:
                    logger.info(f"📄 File already exists (duplicate): {exact_file_path}")
                    logger.info(f"    Skipping save - using existing file")
                    return str(exact_file_path)
                else:
                    logger.info(f"📄 File exists but content differs: {exact_file_path}")
                    logger.info(f"    Existing hash: {existing_file_hash}")
                    logger.info(f"    New hash: {new_file_hash}")
                    # Continue to save with timestamp for different content
                    
            except Exception as e:
                logger.warning(f"Error reading existing file {exact_file_path}: {str(e)}")
                # Continue to save with timestamp as fallback
        
        # If file doesn't exist or content is different, save the new file
        if not exact_file_path.exists():
            # Save with exact filename if it doesn't exist
            file_path = exact_file_path
            logger.info(f"💾 Saving new file: {file_path}")
        else:
            # Save with timestamp prefix if content is different
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{attachment.filename}"
            file_path = indent_dir / filename
            logger.info(f"💾 Saving updated file: {file_path}")
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(attachment.content)
        
        logger.info(f"✅ Saved attachment: {file_path}")
        return str(file_path)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def process_quote_file(self, file_path: str, email_context: str = "") -> Dict[str, Any]:
        """
        Process quote file and extract structured data
        """
        try:
            logger.info(f"Processing quote file: {file_path}")
            
            # Parse file content
            logger.info("Parsing file content...")
            parsed_data = await self.file_parser.parse_file_async(file_path)
            
            if not parsed_data.get('success', False):
                error_msg = f"File parsing failed: {parsed_data.get('error', 'Unknown error')}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
            
            raw_text = parsed_data.get('raw_text', '')
            logger.info(f"File parsed successfully. Text length: {len(raw_text)} characters")
            
            if not raw_text.strip():
                error_msg = "No text content extracted from file"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
            
            # Combine with email context for better extraction
            combined_text = f"Email Context:\n{email_context}\n\nFile Content:\n{raw_text}"
            
            # Extract structured quote data
            logger.info("Extracting structured quote data...")
            quote_data = await self.rfq_generator.generate_async(
                combined_text, 
                source_file=Path(file_path).name
            )
            
            if quote_data.get('success', False):
                logger.info(f"Quote extraction successful! Confidence: {quote_data.get('confidence_score', 0):.2f}")
            else:
                logger.warning(f"Quote extraction failed: {quote_data.get('error', 'Unknown error')}")
            
            return quote_data
            
        except Exception as e:
            error_msg = f"Error processing quote file {file_path}: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {"success": False, "error": error_msg}

    async def process_emails_by_indent(self, indent_id: str) -> Dict[str, Any]:
        """
        Process all emails for a specific indent ID
        """
        if not self.imap_connection:
            if not await self.connect_to_email():
                return {"success": False, "error": "Failed to connect to email server"}
        
        try:
            # Search for emails with specific indent ID using multiple strategies
            logger.info(f"Searching for emails with indent ID: {indent_id}")
            
            found_emails = set()
            search_patterns = [
                f'SUBJECT "indent {indent_id}"',
                f'SUBJECT "indent id {indent_id}"', 
                f'SUBJECT "id {indent_id}"',
                f'SUBJECT "{indent_id}"'
            ]
            
            # Try each search pattern
            for pattern in search_patterns:
                try:
                    typ, message_ids = self.imap_connection.search(None, pattern)
                    if typ == 'OK' and message_ids[0]:
                        pattern_emails = message_ids[0].split()
                        found_emails.update(pattern_emails)
                        logger.info(f"Pattern '{pattern}': found {len(pattern_emails)} emails")
                except Exception as e:
                    logger.warning(f"Search pattern '{pattern}' failed: {str(e)}")
            
            # If no emails found with specific searches, try broader search
            if not found_emails:
                logger.info("No emails found with specific patterns, trying broader search...")
                all_emails = await self.search_emails(days_back=365, max_results=1000)  # Search full year
                
                # Filter emails that contain the indent ID in subject
                for email_id in all_emails:
                    try:
                        email_details = await self.get_email_details(email_id)
                        if email_details and email_details.indent_id == indent_id:
                            found_emails.add(email_id.encode() if isinstance(email_id, str) else email_id)
                    except Exception as e:
                        logger.warning(f"Error checking email {email_id} for indent ID: {str(e)}")
            
            email_ids = [msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id) for msg_id in found_emails]
            logger.info(f"Found {len(email_ids)} emails for indent ID {indent_id}")
            
            if not email_ids:
                logger.warning(f"No emails found for indent ID {indent_id}")
                return {
                    'indent_id': indent_id,
                    'processed_date': datetime.now().isoformat(),
                    'total_emails': 0,
                    'total_quotes': 0,
                    'quotes': [],
                    'success': True
                }
            
            processed_quotes = []
            
            for email_id in email_ids:
                email_details = await self.get_email_details(email_id)
                if email_details and email_details.attachments:
                    
                    # Process each attachment
                    for attachment in email_details.attachments:
                        # Check if this quote has already been processed
                        existing_quote = self._is_quote_already_processed(
                            indent_id, 
                            email_details.subject, 
                            attachment.filename
                        )
                        
                        if existing_quote:
                            # Use existing quote data instead of reprocessing
                            logger.info(f"📋 Using existing quote data for: {attachment.filename}")
                            processed_quotes.append(existing_quote)
                            continue
                        
                        # Save attachment (with duplicate detection)
                        saved_path = await self.save_attachment(attachment, indent_id)
                        
                        # Process quote data only if not already processed
                        quote_data = await self.process_quote_file(
                            saved_path, 
                            email_details.body
                        )
                        
                        processed_quotes.append({
                            'email_subject': email_details.subject,
                            'sender': email_details.sender,
                            'date': email_details.date.isoformat(),
                            'filename': attachment.filename,
                            'saved_path': saved_path,
                            'quote_data': quote_data
                        })
            
            # Create indent directory if it doesn't exist
            indent_dir = self.by_indent_path / f"indent_{indent_id}"
            indent_dir.mkdir(exist_ok=True)
            
            # Save summary
            summary = {
                'indent_id': indent_id,
                'processed_date': datetime.now().isoformat(),
                'total_emails': len(email_ids),
                'total_quotes': len(processed_quotes),
                'quotes': processed_quotes
            }
            
            # Save summary to file
            summary_path = indent_dir / "summary.json"
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error processing emails for indent {indent_id}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def scan_all_emails(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Scan entire inbox for quote-related emails and organize by indent ID
        """
        if not self.imap_connection:
            if not await self.connect_to_email():
                return []
        
        # Get all potential quote emails
        email_ids = await self.search_emails(days_back=days_back)
        logger.info(f"Processing {len(email_ids)} emails for scan")
        
        indent_summaries = {}
        unassigned_quotes = []
        processed_count = 0
        
        for i, email_id in enumerate(email_ids, 1):
            logger.info(f"Processing email {i}/{len(email_ids)}: {email_id}")
            
            email_details = await self.get_email_details(email_id)
            
            if not email_details:
                logger.warning(f"Failed to get details for email {email_id}")
                continue
            
            processed_count += 1
            logger.info(f"Email details: subject='{email_details.subject}', indent_id='{email_details.indent_id}', attachments={len(email_details.attachments)}")
            
            if email_details.indent_id:
                # Process email with indent ID
                logger.info(f"Processing email with indent ID: {email_details.indent_id}")
                if email_details.indent_id not in indent_summaries:
                    # Process all emails for this indent ID at once
                    summary = await self.process_emails_by_indent(email_details.indent_id)
                    if summary.get('success', True):  # Accept even if success key missing
                        indent_summaries[email_details.indent_id] = summary
                    else:
                        logger.error(f"Failed to process indent {email_details.indent_id}: {summary.get('error', 'Unknown error')}")
            else:
                # Handle emails without clear indent ID
                logger.info("Processing email without indent ID")
                if email_details.attachments:
                    for attachment in email_details.attachments:
                        try:
                            # Check if this unassigned quote has already been processed
                            existing_quote = self._is_quote_already_processed(
                                "unknown", 
                                email_details.subject, 
                                attachment.filename
                            )
                            
                            if existing_quote:
                                # Use existing quote data instead of reprocessing
                                logger.info(f"📋 Using existing unassigned quote data for: {attachment.filename}")
                                unassigned_quotes.append(existing_quote)
                                continue
                            
                            saved_path = await self.save_attachment(attachment, "unknown")
                            quote_data = await self.process_quote_file(saved_path, email_details.body)
                            
                            unassigned_quotes.append({
                                'email_subject': email_details.subject,
                                'sender': email_details.sender,
                                'date': email_details.date.isoformat(),
                                'filename': attachment.filename,
                                'saved_path': saved_path,
                                'quote_data': quote_data
                            })
                        except Exception as e:
                            logger.error(f"Error processing unassigned email attachment: {str(e)}")
        
        # If we have unassigned quotes, create a summary for them
        if unassigned_quotes:
            unknown_summary = {
                'indent_id': 'Unknown',
                'processed_date': datetime.now().isoformat(),
                'total_emails': processed_count - len(indent_summaries),
                'total_quotes': len(unassigned_quotes),
                'quotes': unassigned_quotes
            }
            indent_summaries['Unknown'] = unknown_summary
        
        # Save overall summary
        master_summary = {
            'scan_date': datetime.now().isoformat(),
            'days_scanned': days_back,
            'total_emails_processed': len(email_ids),
            'indent_summaries': list(indent_summaries.values()),
            'unassigned_quotes': unassigned_quotes
        }
        
        summary_path = self.quotes_storage_path / "master_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(master_summary, f, indent=2, default=str)
        
        logger.info(f"Email scan complete. Processed {len(email_ids)} emails.")
        return list(indent_summaries.values())

    def get_quotes_by_indent(self, indent_id: str) -> Dict[str, Any]:
        """
        Get all quotes for a specific indent ID
        """
        indent_dir = self.by_indent_path / f"indent_{indent_id}"
        summary_file = indent_dir / "summary.json"
        
        if summary_file.exists():
            with open(summary_file, 'r') as f:
                return json.load(f)
        
        return {"error": f"No quotes found for indent ID {indent_id}"}

    def get_all_indent_ids(self) -> List[str]:
        """
        Get list of all processed indent IDs
        """
        indent_ids = []
        
        for dir_path in self.by_indent_path.iterdir():
            if dir_path.is_dir() and dir_path.name.startswith("indent_"):
                indent_id = dir_path.name.replace("indent_", "")
                if indent_id != "unassigned":
                    indent_ids.append(indent_id)
        
        return sorted(indent_ids)

    def _is_quote_already_processed(self, indent_id: str, email_subject: str, filename: str) -> Optional[Dict[str, Any]]:
        """
        Check if a quote has already been processed by looking at existing summary
        Returns the existing quote data if found, None otherwise
        """
        summary_path = self.by_indent_path / f"indent_{indent_id}" / "summary.json"
        
        if not summary_path.exists():
            return None
        
        try:
            with open(summary_path, 'r') as f:
                summary = json.load(f)
            
            # Check if this email+filename combination already exists
            for quote in summary.get('quotes', []):
                if (quote.get('email_subject') == email_subject and 
                    quote.get('filename') == filename):
                    logger.info(f"📋 Quote already processed: {filename} from '{email_subject[:50]}...'")
                    return quote
            
            return None
            
        except Exception as e:
            logger.warning(f"Error reading summary file {summary_path}: {str(e)}")
            return None

    async def simple_email_test(self) -> Dict[str, Any]:
        """
        Simple test to verify email connection and basic search
        """
        logger.info("🧪 Starting simple email test...")
        
        try:
            # Test 1: Connection
            if not self.imap_connection:
                success = await self.connect_to_email()
                if not success:
                    return {"success": False, "error": "Failed to connect to email"}
            
            logger.info("✅ Email connection successful")
            
            # Test 2: Get total email count
            typ, message_ids = self.imap_connection.search(None, 'ALL')
            total_emails = len(message_ids[0].split()) if typ == 'OK' and message_ids[0] else 0
            logger.info(f"📧 Total emails in inbox: {total_emails}")
            
            # Test 3: Search for "indent" keyword
            typ, indent_ids = self.imap_connection.search(None, 'SUBJECT "indent"')
            indent_count = len(indent_ids[0].split()) if typ == 'OK' and indent_ids[0] else 0
            logger.info(f"📧 Emails with 'indent' in subject: {indent_count}")
            
            # Test 4: Get last 5 emails and check subjects
            typ, recent_ids = self.imap_connection.search(None, 'ALL')
            if typ == 'OK' and recent_ids[0]:
                all_ids = recent_ids[0].split()
                last_5 = all_ids[-5:] if len(all_ids) >= 5 else all_ids
                
                subjects = []
                for email_id in reversed(last_5):  # Most recent first
                    try:
                        typ, header_data = self.imap_connection.fetch(email_id, '(BODY.PEEK[HEADER.FIELDS (SUBJECT)])')
                        if typ == 'OK' and header_data[0]:
                            header_text = header_data[0][1].decode('utf-8', errors='ignore')
                            subject_match = re.search(r'Subject: (.+)', header_text, re.IGNORECASE)
                            if subject_match:
                                subject = subject_match.group(1).strip()
                                subjects.append(subject)
                                logger.info(f"📧 Recent email: '{subject}'")
                                
                                # Check if this is our target email
                                if "indent" in subject.lower() and "1234" in subject:
                                    logger.info(f"🎯 Found target email: '{subject}'")
                    except Exception as e:
                        logger.warning(f"Error getting subject for email {email_id}: {str(e)}")
            
            # Test 5: Test our search function
            logger.info("🔍 Testing search_emails function...")
            found_emails = await self.search_emails(days_back=90, max_results=10)
            logger.info(f"📧 search_emails found: {len(found_emails)} emails")
            
            for i, email_id in enumerate(found_emails[:3], 1):
                email_details = await self.get_email_details(email_id)
                if email_details:
                    logger.info(f"   {i}. '{email_details.subject}' (Indent: {email_details.indent_id}, Attachments: {len(email_details.attachments)})")
            
            return {
                "success": True,
                "total_emails": total_emails,
                "indent_emails": indent_count,
                "search_found": len(found_emails),
                "recent_subjects": subjects[:5] if 'subjects' in locals() else []
            }
            
        except Exception as e:
            error_msg = f"Simple test error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    async def test_email_processing(self, max_emails: int = 10) -> Dict[str, Any]:
        """
        Test email processing functionality - for debugging
        """
        logger.info("Starting email processing test...")
        
        if not self.imap_connection:
            if not await self.connect_to_email():
                return {"success": False, "error": "Failed to connect to email"}
        
        try:
            # Get recent emails
            email_ids = await self.search_emails(days_back=30, max_results=max_emails)
            logger.info(f"Found {len(email_ids)} emails to process")
            
            processed_results = []
            
            for i, email_id in enumerate(email_ids[:max_emails], 1):
                logger.info(f"Processing email {i}/{len(email_ids[:max_emails])}")
                
                # Get email details
                email_details = await self.get_email_details(email_id)
                
                if email_details:
                    result = {
                        'email_id': email_id,
                        'subject': email_details.subject,
                        'sender': email_details.sender,
                        'date': email_details.date.isoformat(),
                        'indent_id': email_details.indent_id,
                        'attachments_count': len(email_details.attachments),
                        'processed_quotes': []
                    }
                    
                    # Process attachments if any
                    if email_details.attachments:
                        for attachment in email_details.attachments:
                            try:
                                # Save attachment
                                saved_path = await self.save_attachment(
                                    attachment, 
                                    email_details.indent_id or "test"
                                )
                                
                                # Process quote
                                quote_data = await self.process_quote_file(
                                    saved_path, 
                                    email_details.body
                                )
                                
                                result['processed_quotes'].append({
                                    'filename': attachment.filename,
                                    'saved_path': saved_path,
                                    'quote_data': quote_data
                                })
                                
                            except Exception as e:
                                logger.error(f"Error processing attachment {attachment.filename}: {str(e)}")
                    
                    processed_results.append(result)
                else:
                    logger.warning(f"Failed to get details for email {email_id}")
            
            return {
                "success": True,
                "total_emails": len(email_ids),
                "processed_emails": len(processed_results),
                "results": processed_results
            }
            
        except Exception as e:
            logger.error(f"Test processing error: {str(e)}")
            return {"success": False, "error": str(e)}

# Convenience functions for UI integration
async def scan_email_inbox(email_agent: EmailParsingAgent, days_back: int = 30) -> List[Dict[str, Any]]:
    """Convenience function for scanning email inbox"""
    return await email_agent.scan_all_emails(days_back=days_back)

async def process_indent_emails(email_agent: EmailParsingAgent, indent_id: str) -> Dict[str, Any]:
    """Convenience function for processing specific indent ID emails"""
    return await email_agent.process_emails_by_indent(indent_id)
