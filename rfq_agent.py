# rfq_agent.py
from autogen import ConversableAgent
from dotenv import load_dotenv
import os
import json
import asyncio
from typing import Dict, Any, Optional
from pydantic import BaseModel, ValidationError, field_validator
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
import time

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Debug: Check if GROQ_API_KEY is loaded
groq_key = os.getenv("GROQ_API_KEY")
if groq_key:
    logger.info(f"GROQ_API_KEY loaded successfully (first 10 chars: {groq_key[:10]}...)")
else:
    logger.error("GROQ_API_KEY not found in environment variables")
    logger.info(f"Current working directory: {os.getcwd()}")
    # Try to load .env explicitly
    from pathlib import Path
    env_path = Path('.env')
    if env_path.exists():
        logger.info(f".env file found at: {env_path.absolute()}")
        load_dotenv(env_path)
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            logger.info("GROQ_API_KEY loaded after explicit .env loading")
        else:
            logger.error("GROQ_API_KEY still not found after explicit loading")
    else:
        logger.error(f".env file not found at: {env_path.absolute()}")

# Pydantic models for validation
class LineItem(BaseModel):
    part_number: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[int] = None
    target_price: Optional[float] = None
    currency: Optional[str] = None 
    
    @field_validator("quantity", mode="before")
    @classmethod
    def parse_quantity(cls, v):
        if isinstance(v, str):
            return int(v.replace(",", ""))
        return v

    @field_validator("target_price", mode="before")
    @classmethod
    def parse_target_price(cls, v):
        if isinstance(v, str):
            return float(v.replace(",", ""))
        return v

class RFQResponse(BaseModel):
    title: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_contact: Optional[str] = None
    client_phone: Optional[str] = None
    rfq_to: Optional[str] = None
    delivery_location: Optional[str] = None
    delivery_deadline: Optional[str] = None
    response_due_date: Optional[str] = None
    description: Optional[str] = None
    line_items: list[LineItem] = []
    requested_documents: list[str] = []
    confidence_score: float = 0.0
    missing_fields: list[str] = []
    requires_review: bool = True
    source_file: str = "email-body"
    success: bool = True
    message: str = ""

LLM_CONFIG = {
    "model": "llama3-70b-8192",
    "api_key": os.getenv("GROQ_API_KEY"),
    "base_url": "https://api.groq.com/openai/v1",
    "api_type": "openai",
    "temperature": 0.1,
    "max_tokens": 1200,  # Increased for better responses
    "cache_seed": 42,
    "timeout": 30,  # Add timeout
}

# Extract prompt template to constant
# Extract prompt template to constant
# Extract prompt template to constant
EXTRACTION_PROMPT_TEMPLATE = """Extract the following fields from the RFQ text below and return ONLY valid JSON:
Required fields:
- title: Document title or subject
- client_name: Client/company name
- client_email: Contact email address
- client_contact: Contact person name
- client_phone: Phone number
- rfq_to: Who the RFQ is addressed to
- delivery_location: Where items should be delivered
- delivery_deadline: When delivery is needed
- response_due_date: When response is due
- description: Brief description of requirements
- line_items: Array of objects with part_number, description, quantity, target_price (numeric value only), currency (currency symbol or word as found in text)
- requested_documents: Array of required document types
- confidence_score: Float 0.0-1.0 indicating extraction confidence
- missing_fields: Array of field names that couldn't be extracted
- requires_review: Boolean indicating if human review is needed

IMPORTANT: For line_items, separate price and currency:
- target_price: Extract only the numeric value (e.g., "100", "50.75", "1000")
- currency: Extract currency as found in text - can be symbol ($, €, £, ₹) or word (dollars, euros, pounds, rupees) or code (USD, EUR, GBP, INR)
- Examples:
  * "$100" → target_price: "100", currency: "$"
  * "50 euros" → target_price: "50", currency: "euros"  
  * "75 GBP" → target_price: "75", currency: "GBP"
  * "₹500" → target_price: "500", currency: "₹"
  * "25" (no currency) → target_price: "25", currency: null

Return only valid JSON. Do not include any explanatory text.
Text to analyze:
"""

class RFQFieldGenerator:
    def __init__(self):
        if not LLM_CONFIG.get("api_key"):
            raise ValueError("GROQ_API_KEY not set in environment.")
        
        self.agent = ConversableAgent(
            name="field_generator",
            system_message="You are an expert at extracting structured RFQ data from raw text. Return valid JSON only with no additional text or explanations.",
            llm_config=LLM_CONFIG,
            human_input_mode="NEVER",
            code_execution_config=False,
        )
        logger.info("RFQ Field Generator initialized successfully")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def generate_async(self, raw_text: str, source_file: str = "email-body") -> Dict[str, Any]:
        """Async version of generate method with retry logic"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._generate_sync, raw_text, source_file
        )
        # return await asyncio.get_event_loop().run_in_executor(
        #     None, self._generate_sync, raw_text, source_file
        # )

    def generate(self, raw_text: str, source_file: str = "email-body") -> Dict[str, Any]:
        """Synchronous version for backward compatibility"""
        return self._generate_sync(raw_text, source_file)

    def _generate_sync(self, raw_text: str, source_file: str) -> Dict[str, Any]:
        """Internal synchronous generation method"""
        if not raw_text or not raw_text.strip():
            logger.warning("Empty raw text provided")
            return self._create_error_response("Empty or invalid input text")

        # Truncate very long text to avoid token limits
        if len(raw_text) > 8000:
            raw_text = raw_text[:8000] + "... [truncated]"
            logger.warning(f"Text truncated to 8000 characters for processing")

        prompt = f"{EXTRACTION_PROMPT_TEMPLATE}\n\"\"\"\n{raw_text}\n\"\"\""
        
        try:
            logger.info("📤 Sending prompt to LLM...")
            # start_time = asyncio.get_event_loop().time() if hasattr(asyncio, 'get_running_loop') else 0
            
        # try:
            start_time = time.perf_counter()
        # except RuntimeError:
        #     start_time = 0


            reply = self.agent.generate_reply([{"role": "user", "content": prompt}])
            
            if hasattr(asyncio, 'get_running_loop'):
                # duration = asyncio.get_event_loop().time() - start_time
                duration = time.perf_counter() - start_time
                logger.info(f"📥 LLM response received in {duration:.2f}s")
            else:
                logger.info("📥 LLM response received")

            # Parse and validate response
            parsed_response = self._parse_and_validate_response(reply, source_file)
            logger.info (f"parsed response:  {parsed_response}")
            logger.info(f"📄 Successfully parsed RFQ fields with confidence: {parsed_response.get('confidence_score', 0.0)}")
            return parsed_response.dict() if hasattr(parsed_response, 'dict') else parsed_response

        except Exception as e:
            loop = None
            start_time = 0
            logger.error(f"❌ Exception during generation: {str(e)}")
            return self._create_error_response(str(e))
        

    def _parse_and_validate_response(self, reply: Any, source_file: str) -> Dict[str, Any]:
        """Parse LLM response and validate using Pydantic"""
        
        # Handle string responses
        if isinstance(reply, str):
            reply = self._extract_json_from_string(reply)
        
        if not isinstance(reply, dict):
            raise ValueError("LLM did not return a valid dictionary structure")

        try:
            # Validate using Pydantic model
            validated_response = RFQResponse(**reply)
            validated_response.source_file = source_file
            validated_response.success = True
            validated_response.message = f"RFQ processed from {source_file}"
            
            return validated_response.dict()
            
        except ValidationError as e:
            logger.warning(f"Validation failed, using fallback: {str(e)}")
            return self._create_fallback_response(reply, source_file, str(e))

    def _extract_json_from_string(self, response_str: str) -> dict:
        """Extract JSON from string response with multiple fallback strategies"""
        
        # Strategy 1: Direct JSON parse
        try:
            return json.loads(response_str)
        except json.JSONDecodeError:
            pass

        # Strategy 2: Find JSON block in text
        import re
        json_match = re.search(r'\{.*\}', response_str, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Strategy 3: Clean common issues
        cleaned = response_str.strip()
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        
        try:
            return json.loads(cleaned.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Unable to parse JSON from LLM response: {str(e)}")

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "success": False,
            "error": error_message,
            "confidence_score": 0.0,
            "requires_review": True,
            "missing_fields": ["all"],
            "source_file": "unknown"
        }

    def _create_fallback_response(self, raw_reply: dict, source_file: str, validation_error: str) -> Dict[str, Any]:
        """Create fallback response when validation fails but we have some data"""
        fallback = RFQResponse()
        
        # Copy over any valid fields
        for field_name, field_value in raw_reply.items():
            if hasattr(fallback, field_name):
                try:
                    setattr(fallback, field_name, field_value)
                except:
                    continue
        
        fallback.source_file = source_file
        fallback.success = True
        fallback.message = f"RFQ processed with validation warnings: {validation_error}"
        fallback.requires_review = True
        fallback.confidence_score = max(0.3, fallback.confidence_score)  # Minimum confidence for partial data
        
        return fallback.dict()

# Async wrapper function for easier usage
async def generate_rfq_fields_async(raw_text: str, source_file: str = "email-body") -> Dict[str, Any]:
    """Convenience function for async RFQ field generation"""
    generator = RFQFieldGenerator()
    return await generator.generate_async(raw_text, source_file)