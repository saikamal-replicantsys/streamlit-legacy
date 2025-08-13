import os
import json
import asyncio
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, ValidationError, field_validator
from tenacity import retry, stop_after_attempt, wait_exponential
from autogen import ConversableAgent
from dotenv import load_dotenv
from datetime import datetime
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InvoiceLineItem(BaseModel):
    item_code: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[float] = None
    uom: Optional[str] = None
    unit_price: Optional[float] = None
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None
    total_price: Optional[float] = None

    @field_validator("quantity", "unit_price", "tax_rate", "tax_amount", "total_price", mode="before")
    @classmethod
    def parse_numbers(cls, v):
        if isinstance(v, str):
            try:
                return float(v.replace(",", ""))
            except Exception:
                return None
        return v


class InvoiceResponse(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    po_number: Optional[str] = None
    supplier_name: Optional[str] = None
    supplier_address: Optional[str] = None
    supplier_gstin_vat: Optional[str] = None
    supplier_email: Optional[str] = None
    bill_to: Optional[str] = None
    ship_to: Optional[str] = None
    client_gstin_vat: Optional[str] = None
    payment_terms: Optional[str] = None
    due_date: Optional[str] = None
    currency: Optional[str] = None
    subtotal_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    total_amount: Optional[float] = None
    discount_amount: Optional[float] = None
    line_items: List[InvoiceLineItem] = []
    notes: Optional[str] = None
    terms_conditions: List[str] = []
    confidence_score: float = 0.0
    requires_review: bool = True
    missing_fields: List[str] = []
    source_file: str = "unknown"
    success: bool = True
    message: str = ""


LLM_CONFIG = {
    "model": "llama3-70b-8192",
    "api_key": os.getenv("GROQ_API_KEY"),
    "base_url": "https://api.groq.com/openai/v1",
    "api_type": "openai",
    "temperature": 0.1,
    "max_tokens": 1500,
    "cache_seed": 42,
    "timeout": 30,
}


EXTRACTION_PROMPT_TEMPLATE = """Extract the following fields from the INVOICE document below and return ONLY valid JSON:
Required top-level fields:
- invoice_number
- invoice_date (ISO-like if possible)
- po_number
- supplier_name
- supplier_address
- supplier_gstin_vat (if present)
- supplier_email (if present)
- bill_to (client/billing name and address if present)
- ship_to (if separate and present)
- client_gstin_vat (if present)
- payment_terms
- due_date (if present)
- currency (symbol or code e.g. INR, ₹, USD, $)
- subtotal_amount (numeric)
- tax_amount (numeric)
- total_amount (numeric)
- discount_amount (numeric if present)
- line_items: array of {item_code, description, quantity, uom, unit_price, tax_rate, tax_amount, total_price}
- notes (if present)
- terms_conditions: array of strings (if present)
- confidence_score (0.0-1.0)
- requires_review (boolean)
- missing_fields: array of strings

IMPORTANT for numeric fields: return numeric values only; currency should be a separate field.

Return only valid JSON. Do not include any explanatory text.
Document to analyze:
"""


class InvoiceFieldGenerator:
    def __init__(self):
        if not LLM_CONFIG.get("api_key"):
            raise ValueError("GROQ_API_KEY not set in environment.")

        self.agent = ConversableAgent(
            name="invoice_field_generator",
            system_message="You extract structured INVOICE data. Return valid JSON only.",
            llm_config=LLM_CONFIG,
            human_input_mode="NEVER",
            code_execution_config=False,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
    async def generate_async(self, raw_text: str, source_file: str = "unknown") -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._generate_sync, raw_text, source_file)

    def _generate_sync(self, raw_text: str, source_file: str) -> Dict[str, Any]:
        if not raw_text or not raw_text.strip():
            return self._error("Empty or invalid input text")

        if len(raw_text) > 8000:
            raw_text = raw_text[:8000] + "... [truncated]"

        prompt = f"{EXTRACTION_PROMPT_TEMPLATE}\n\n\"\"\"\n{raw_text}\n\"\"\""
        try:
            reply = self.agent.generate_reply([{"role": "user", "content": prompt}])
            parsed = self._parse(reply)
            parsed["source_file"] = source_file
            parsed["success"] = True
            return parsed
        except Exception as e:
            logger.error(f"Invoice extraction error: {e}")
            return self._error(str(e))

    def _parse(self, reply: Any) -> Dict[str, Any]:
        if isinstance(reply, str):
            reply = self._extract_json(reply)
        if not isinstance(reply, dict):
            raise ValueError("Invalid response shape from LLM")
        try:
            validated = InvoiceResponse(**reply)
            return validated.dict()
        except ValidationError:
            # Best-effort return
            return reply

    def _extract_json(self, s: str) -> dict:
        import re, json as _json
        try:
            return _json.loads(s)
        except Exception:
            pass
        m = re.search(r"\{.*\}", s, re.DOTALL)
        if m:
            try:
                return _json.loads(m.group())
            except Exception:
                pass
        cleaned = s.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return _json.loads(cleaned.strip())

    def _error(self, msg: str) -> Dict[str, Any]:
        return {"success": False, "error": msg, "confidence_score": 0.0, "requires_review": True}


class InvoiceDatabase:
    def __init__(self, db_path: str = "invoice_database.json"):
        self.db_path = db_path
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        self._init()

    def _init(self):
        if not os.path.exists(self.db_path):
            data = {"invoices": {}, "metadata": {"created_date": datetime.now().isoformat(), "version": "1.0", "total_invoices": 0}}
            self._save(data)

    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"invoices": {}, "metadata": {"created_date": datetime.now().isoformat(), "version": "1.0", "total_invoices": 0}}

    def _save(self, data: Dict[str, Any]):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def save_invoice(self, po_number: str, filename: str, invoice_data: Dict[str, Any]) -> bool:
        data = self._load()
        key = f"{po_number}_{filename}"
        invoice_data["po_number"] = po_number
        invoice_data["filename"] = filename
        invoice_data["processed_date"] = datetime.now().isoformat()
        invoice_data["invoice_key"] = key
        data["invoices"][key] = invoice_data
        data["metadata"]["total_invoices"] = len(data["invoices"])
        data["metadata"]["last_updated"] = datetime.now().isoformat()
        self._save(data)
        return True

    def get_invoices_by_po(self, po_number: str) -> List[Dict[str, Any]]:
        data = self._load()
        return [inv for inv in data["invoices"].values() if inv.get("po_number") == po_number]

    def get_all_invoices(self) -> List[Dict[str, Any]]:
        data = self._load()
        return list(data["invoices"].values())

    def get_stats(self) -> Dict[str, Any]:
        data = self._load()
        invoices = data["invoices"].values()
        return {
            "total_invoices": len(invoices),
            "unique_pos": len(set(inv.get("po_number") for inv in invoices)),
            "unique_suppliers": len(set(inv.get("supplier_name") for inv in invoices if inv.get("supplier_name"))),
            "total_value": sum(inv.get("total_amount", 0) or 0 for inv in invoices),
            "database_created": data["metadata"].get("created_date"),
            "last_updated": data["metadata"].get("last_updated"),
        }



