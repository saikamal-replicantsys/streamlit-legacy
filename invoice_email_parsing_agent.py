# invoice_email_parsing_agent.py
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


class InvoiceEmail(BaseModel):
    email_id: str
    subject: str
    sender: str
    date: datetime
    body: str
    po_number: Optional[str] = None
    attachments: List[EmailAttachment] = []


class InvoiceEmailParsingAgent:
    """
    Email agent to fetch and organize invoice attachments by PO number in subject.
    """

    def __init__(self, config_path: str = "email_config.json"):
        self.config_path = config_path
        self.email_config: Optional[EmailConfig] = None
        self.imap_connection: Optional[imaplib.IMAP4] = None
        self.file_parser = FileParser()

        self.storage_path = Path("invoices_storage")
        self.by_po_path = self.storage_path / "by_po_number"
        self.storage_path.mkdir(exist_ok=True)
        self.by_po_path.mkdir(exist_ok=True)

        # PO number patterns
        self.po_patterns = [
            r'po\s*#?\s*([A-Za-z0-9-]+)',               # "PO 12345" or "PO#12345"
            r'purchase\s*order\s*#?\s*([A-Za-z0-9-]+)'  # "Purchase Order 12345"
        ]

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

    def extract_po_number(self, subject: str) -> Optional[str]:
        if not subject:
            return None
        s = subject.lower().strip()
        for pattern in self.po_patterns:
            m = re.search(pattern, s, re.IGNORECASE)
            if m:
                return m.group(1)
        return None

    async def _search_emails(self, days_back: int = 30, max_results: int = 200) -> List[str]:
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

    async def _get_email_details(self, email_id: str) -> Optional[InvoiceEmail]:
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
                            attachments.append(EmailAttachment(
                                filename=filename,
                                content=payload,
                                content_type=part.get_content_type(),
                                size=len(payload),
                                message_id=email_id.decode() if isinstance(email_id, bytes) else str(email_id)
                            ))

            return InvoiceEmail(
                email_id=email_id.decode() if isinstance(email_id, bytes) else str(email_id),
                subject=subject,
                sender=sender,
                date=email_date,
                body=body,
                po_number=self.extract_po_number(subject),
                attachments=attachments,
            )
        except Exception as e:
            logger.error(f"Get email details error: {e}")
            return None

    async def save_attachment(self, attachment: EmailAttachment, po_number: str) -> str:
        po_dir = self.by_po_path / f"po_{po_number}"
        po_dir.mkdir(exist_ok=True)
        file_path = po_dir / attachment.filename
        # Avoid overwriting identical file
        if not file_path.exists():
            with open(file_path, 'wb') as f:
                f.write(attachment.content)
        return str(file_path)

    async def process_emails_by_po(self, po_number: str) -> Dict[str, Any]:
        if not self.imap_connection:
            if not await self.connect_to_email():
                return {"success": False, "error": "Failed to connect to email server"}
        try:
            # Get recent emails and filter by PO in subject
            email_ids = await self._search_emails(days_back=365, max_results=1000)
            matching: List[str] = []
            for eid in email_ids:
                details = await self._get_email_details(eid)
                if details and details.po_number == po_number:
                    matching.append(details.email_id)

            processed: List[Dict[str, Any]] = []
            for eid in matching:
                details = await self._get_email_details(eid)
                if not details:
                    continue
                for att in details.attachments:
                    saved_path = await self.save_attachment(att, po_number)
                    processed.append({
                        'email_subject': details.subject,
                        'sender': details.sender,
                        'date': details.date.isoformat(),
                        'filename': att.filename,
                        'saved_path': saved_path,
                        'size': att.size,
                    })

            po_dir = self.by_po_path / f"po_{po_number}"
            po_dir.mkdir(exist_ok=True)
            summary = {
                'po_number': po_number,
                'processed_date': datetime.now().isoformat(),
                'total_emails': len(matching),
                'total_invoices': len(processed),
                'invoices': processed,
            }
            with open(po_dir / "summary.json", 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            return summary
        except Exception as e:
            logger.error(f"Process by PO error: {e}")
            return {"success": False, "error": str(e)}

    def get_invoices_by_po(self, po_number: str) -> Dict[str, Any]:
        po_dir = self.by_po_path / f"po_{po_number}"
        summary_file = po_dir / "summary.json"
        if summary_file.exists():
            with open(summary_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"error": f"No invoices found for PO {po_number}"}

    def get_all_po_numbers(self) -> List[str]:
        po_numbers: List[str] = []
        for d in self.by_po_path.iterdir():
            if d.is_dir() and d.name.startswith("po_"):
                po_numbers.append(d.name.replace("po_", ""))
        return sorted(po_numbers)



