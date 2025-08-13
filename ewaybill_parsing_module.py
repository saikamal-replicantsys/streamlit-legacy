import os
import json
import asyncio
from typing import Dict, Any, Optional
from pydantic import BaseModel, ValidationError
from autogen import ConversableAgent
from dotenv import load_dotenv

load_dotenv()

LLM_CONFIG = {
    "model": "llama3-70b-8192",
    "api_key": os.getenv("GROQ_API_KEY"),
    "base_url": "https://api.groq.com/openai/v1",
    "api_type": "openai",
    "temperature": 0.1,
    "max_tokens": 800,
    "timeout": 30,
}


class EWayBillResponse(BaseModel):
    eway_bill_number: Optional[str] = None
    eway_bill_date: Optional[str] = None
    po_number: Optional[str] = None
    supplier_name: Optional[str] = None
    vehicle_number: Optional[str] = None
    source: Optional[str] = None
    destination: Optional[str] = None
    notes: Optional[str] = None
    success: bool = True
    confidence_score: float = 0.0
    requires_review: bool = True


PROMPT = """Extract E-Way Bill details and return ONLY valid JSON with fields:
- eway_bill_number, eway_bill_date, po_number, supplier_name, vehicle_number, source, destination,
- notes, confidence_score (0.0-1.0), requires_review (boolean)
Return only JSON.
Document:
"""


class EWayBillFieldGenerator:
    def __init__(self):
        if not LLM_CONFIG.get("api_key"):
            raise ValueError("GROQ_API_KEY not set in environment.")
        self.agent = ConversableAgent(
            name="ewaybill_field_generator",
            system_message="You extract structured E-Way Bill data. Return valid JSON only.",
            llm_config=LLM_CONFIG,
            human_input_mode="NEVER",
            code_execution_config=False,
        )

    async def generate_async(self, raw_text: str, source_file: str = "unknown") -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._generate_sync, raw_text, source_file)

    def _generate_sync(self, raw_text: str, source_file: str) -> Dict[str, Any]:
        if not raw_text or not raw_text.strip():
            return {"success": False, "error": "Empty text"}
        if len(raw_text) > 8000:
            raw_text = raw_text[:8000] + "... [truncated]"
        prompt = f"{PROMPT}\n\n```\n{raw_text}\n```"
        try:
            reply = self.agent.generate_reply([{"role": "user", "content": prompt}])
            data = self._parse(reply)
            data["source_file"] = source_file
            data["success"] = True
            return data
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _parse(self, reply: Any) -> Dict[str, Any]:
        if isinstance(reply, str):
            import re
            try:
                return json.loads(reply)
            except Exception:
                m = re.search(r"\{.*\}", reply, re.DOTALL)
                if not m:
                    raise
                return json.loads(m.group())
        if not isinstance(reply, dict):
            raise ValueError("Invalid response shape")
        try:
            return EWayBillResponse(**reply).dict()
        except ValidationError:
            return reply




