import os
import re
import json
import email
import imaplib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from email.header import decode_header

from pydantic import BaseModel

from fileparser import FileParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


EMAIL_PROVIDERS = {
    'gmail': {'imap_server': 'imap.gmail.com', 'imap_port': 993, 'use_ssl': True},
    'outlook': {'imap_server': 'outlook.office365.com', 'imap_port': 993, 'use_ssl': True},
    'yahoo': {'imap_server': 'imap.mail.yahoo.com', 'imap_port': 993, 'use_ssl': True},
    'custom': {'imap_server': '', 'imap_port': 993, 'use_ssl': True},
}


class EmailConfig(BaseModel):
    provider: str
    email_address: str
    password: str
    imap_server: Optional[str] = None
    imap_port: Optional[int] = None
    use_ssl: bool = True


class EmailAttachment(BaseModel):
    filename: str
    content: bytes
    content_type: str
    size: int
    message_id: str


class HRDocumentEmail(BaseModel):
    email_id: str
    subject: str
    sender: str
    date: datetime
    body: str
    employee_id: Optional[str] = None
    attachments: List[EmailAttachment] = []


class HROnboardingEmailAgent:
    """
    HR Onboarding Email Agent
    - Scans email inbox for messages containing a specific Employee ID in the subject
    - Saves all candidate-required documents (attachments) under hr_onboarding_storage/by_employee_id/emp_<ID>/
    - Writes a summary.json per employee ID
    """

    def __init__(self, config_path: str = "email_config.json"):
        self.config_path = config_path
        self.email_config: Optional[EmailConfig] = None
        self.imap_connection: Optional[imaplib.IMAP4] = None
        self.file_parser = FileParser()

        self.storage_path = Path("hr_onboarding_storage")
        self.by_emp_path = self.storage_path / "by_employee_id"
        self.storage_path.mkdir(exist_ok=True)
        self.by_emp_path.mkdir(exist_ok=True)

        # Allowed document types common in onboarding
        self.allowed_extensions = {
            '.pdf', '.docx', '.doc', '.xlsx', '.xls', '.csv', '.txt',
            '.jpg', '.jpeg', '.png', '.zip'
        }

        self._load_email_config()

    def _load_email_config(self) -> bool:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    cfg = json.load(f)
                provider = cfg.get('provider', 'custom')
                defaults = EMAIL_PROVIDERS.get(provider, EMAIL_PROVIDERS['custom'])
                cfg.setdefault('imap_server', defaults['imap_server'])
                cfg.setdefault('imap_port', defaults['imap_port'])
                cfg.setdefault('use_ssl', defaults['use_ssl'])
                self.email_config = EmailConfig(**cfg)
                return True
            except Exception as e:
                logger.error(f"Failed to load email config: {e}")
        return False

    async def connect_to_email(self) -> bool:
        if not self.email_config:
            return False
        try:
            if self.email_config.use_ssl:
                self.imap_connection = imaplib.IMAP4_SSL(self.email_config.imap_server, self.email_config.imap_port)
            else:
                self.imap_connection = imaplib.IMAP4(self.email_config.imap_server, self.email_config.imap_port)
            self.imap_connection.login(self.email_config.email_address, self.email_config.password)
            self.imap_connection.select('INBOX')
            return True
        except Exception as e:
            logger.error(f"Email connect error: {e}")
            return False

    def disconnect_from_email(self):
        if self.imap_connection:
            try:
                self.imap_connection.close()
                self.imap_connection.logout()
            except Exception:
                pass
            finally:
                self.imap_connection = None

    def _decode_header(self, header_value: str) -> str:
        if not header_value:
            return ""
        parts = decode_header(header_value)
        out = ""
        for part, enc in parts:
            if isinstance(part, bytes):
                out += part.decode(enc or 'utf-8', errors='ignore')
            else:
                out += str(part)
        return out

    def extract_employee_id(self, subject: str) -> Optional[str]:
        if not subject:
            return None
        s = subject.strip()
        # Heuristics: look for EMP/Employee ID patterns or standalone alphanumeric IDs
        patterns = [
            r"employee\s*id\s*[:#-]?\s*([A-Za-z0-9_-]{3,20})",
            r"emp\s*id\s*[:#-]?\s*([A-Za-z0-9_-]{3,20})",
            r"\bemp[-_]?([A-Za-z0-9]{2,})\b",
        ]
        for p in patterns:
            m = re.search(p, s, re.IGNORECASE)
            if m:
                return m.group(1)
        return None

    async def _search_emails(self, days_back: int = 365, max_results: int = 1000) -> List[str]:
        if not self.imap_connection:
            if not await self.connect_to_email():
                return []
        try:
            since_date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
            typ, message_ids = self.imap_connection.search(None, f'SINCE "{since_date}"')
            if typ != 'OK' or not message_ids[0]:
                return []
            all_ids = message_ids[0].split()
            return list(reversed(all_ids))[:max_results]
        except Exception as e:
            logger.error(f"Search emails error: {e}")
            return []

    async def _get_email_details(self, email_id: str) -> Optional[HRDocumentEmail]:
        if not self.imap_connection:
            return None
        try:
            typ, data = self.imap_connection.fetch(email_id if isinstance(email_id, bytes) else email_id.encode(), '(RFC822)')
            if typ != 'OK' or not data or not data[0]:
                return None
            msg = email.message_from_bytes(data[0][1])
            subject = self._decode_header(msg.get('Subject', ''))
            sender = self._decode_header(msg.get('From', ''))
            date_str = msg.get('Date', '')
            try:
                from email.utils import parsedate_to_datetime
                email_date = parsedate_to_datetime(date_str)
            except Exception:
                email_date = datetime.now()

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    cdisp = str(part.get("Content-Disposition"))
                    if ctype == "text/plain" and "attachment" not in cdisp:
                        try:
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            break
                        except Exception:
                            continue
            else:
                try:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                except Exception:
                    body = str(msg.get_payload())

            attachments: List[EmailAttachment] = []
            for part in msg.walk():
                cdisp = str(part.get("Content-Disposition"))
                if "attachment" in cdisp:
                    filename = part.get_filename()
                    if filename:
                        filename = self._decode_header(filename)
                        payload = part.get_payload(decode=True)
                        if payload:
                            ext = Path(filename).suffix.lower()
                            if ext in self.allowed_extensions:
                                attachments.append(EmailAttachment(
                                    filename=filename,
                                    content=payload,
                                    content_type=part.get_content_type(),
                                    size=len(payload),
                                    message_id=email_id.decode() if isinstance(email_id, bytes) else str(email_id)
                                ))

            return HRDocumentEmail(
                email_id=email_id.decode() if isinstance(email_id, bytes) else str(email_id),
                subject=subject,
                sender=sender,
                date=email_date,
                body=body,
                employee_id=self.extract_employee_id(subject),
                attachments=attachments,
            )
        except Exception as e:
            logger.error(f"Get email details error: {e}")
            return None

    async def save_attachment(self, attachment: EmailAttachment, employee_id: str) -> str:
        emp_dir = self.by_emp_path / f"emp_{employee_id}"
        emp_dir.mkdir(parents=True, exist_ok=True)
        file_path = emp_dir / attachment.filename
        # Avoid overwriting identical name; if exists, add timestamp prefix
        if file_path.exists():
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = emp_dir / f"{ts}_{attachment.filename}"
        with open(file_path, 'wb') as f:
            f.write(attachment.content)
        return str(file_path)

    async def process_emails_by_employee_id(self, employee_id: str) -> Dict[str, Any]:
        if not self.imap_connection:
            if not await self.connect_to_email():
                return {"success": False, "error": "Failed to connect to email server"}
        try:
            email_ids = await self._search_emails(days_back=365, max_results=1000)
            matching: List[str] = []
            for eid in email_ids:
                details = await self._get_email_details(eid)
                if details and (employee_id.lower() in details.subject.lower()):
                    matching.append(details.email_id)

            processed: List[Dict[str, Any]] = []
            for eid in matching:
                details = await self._get_email_details(eid)
                if not details:
                    continue
                for att in details.attachments:
                    saved_path = await self.save_attachment(att, employee_id)
                    processed.append({
                        'email_subject': details.subject,
                        'sender': details.sender,
                        'date': details.date.isoformat(),
                        'filename': att.filename,
                        'saved_path': saved_path,
                        'size': att.size,
                    })

            emp_dir = self.by_emp_path / f"emp_{employee_id}"
            emp_dir.mkdir(exist_ok=True)
            summary = {
                'employee_id': employee_id,
                'processed_date': datetime.now().isoformat(),
                'total_emails': len(matching),
                'total_documents': len(processed),
                'documents': processed,
            }
            with open(emp_dir / "summary.json", 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            return summary
        except Exception as e:
            logger.error(f"Process by employee ID error: {e}")
            return {"success": False, "error": str(e)}

    def get_documents_by_employee_id(self, employee_id: str) -> Dict[str, Any]:
        emp_dir = self.by_emp_path / f"emp_{employee_id}"
        summary_file = emp_dir / "summary.json"
        if summary_file.exists():
            with open(summary_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"error": f"No documents found for employee ID {employee_id}"}

    def get_all_employee_ids(self) -> List[str]:
        employee_ids: List[str] = []
        for d in self.by_emp_path.iterdir():
            if d.is_dir() and d.name.startswith("emp_"):
                employee_ids.append(d.name.replace("emp_", ""))
        return sorted(employee_ids)



