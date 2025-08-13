# quotation_parsing_agent.py
from autogen import ConversableAgent
from dotenv import load_dotenv
import os
import json
import asyncio
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, ValidationError, field_validator
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
import time
from pathlib import Path
import sqlite3
from datetime import datetime

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

# Pydantic models for quotation data
class QuotationLineItem(BaseModel):
    item_number: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    currency: Optional[str] = None
    specifications: Optional[str] = None
    
    @field_validator("quantity", mode="before")
    @classmethod
    def parse_quantity(cls, v):
        if isinstance(v, str):
            return int(v.replace(",", ""))
        return v

    @field_validator("unit_price", "total_price", mode="before")
    @classmethod
    def parse_price(cls, v):
        if isinstance(v, str):
            return float(v.replace(",", ""))
        return v

class QuotationResponse(BaseModel):
    quotation_number: Optional[str] = None
    quotation_date: Optional[str] = None
    valid_until: Optional[str] = None
    supplier_name: Optional[str] = None
    supplier_address: Optional[str] = None
    supplier_contact: Optional[str] = None
    supplier_phone: Optional[str] = None
    supplier_email: Optional[str] = None
    client_name: Optional[str] = None
    client_address: Optional[str] = None
    client_contact: Optional[str] = None
    delivery_location: Optional[str] = None
    delivery_terms: Optional[str] = None
    payment_terms: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    tax_amount: Optional[float] = None
    discount_amount: Optional[float] = None
    line_items: List[QuotationLineItem] = []
    terms_conditions: List[str] = []
    confidence_score: float = 0.0
    missing_fields: List[str] = []
    requires_review: bool = True
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

EXTRACTION_PROMPT_TEMPLATE = """Extract the following fields from the quotation document below and return ONLY valid JSON:
Required fields:
- quotation_number: Quotation reference number
- quotation_date: Date when quotation was issued
- valid_until: Date until which quotation is valid
- supplier_name: Name of the supplier/company providing the quotation
- supplier_address: Supplier's address
- supplier_contact: Contact person at supplier
- supplier_phone: Supplier's phone number
- supplier_email: Supplier's email address
- client_name: Client/customer name
- client_address: Client's address
- client_contact: Client contact person
- delivery_location: Where items should be delivered
- delivery_terms: Delivery terms and conditions
- payment_terms: Payment terms and conditions
- total_amount: Total quotation amount (numeric value only)
- currency: Currency symbol or code (e.g., $, €, £, ₹, USD, EUR, GBP, INR)
- tax_amount: Tax amount if specified
- discount_amount: Discount amount if specified
- line_items: Array of objects with item_number, description, quantity, unit_price, total_price, currency, specifications
- terms_conditions: Array of terms and conditions
- confidence_score: Float 0.0-1.0 indicating extraction confidence
- missing_fields: Array of field names that couldn't be extracted
- requires_review: Boolean indicating if human review is needed

IMPORTANT: For prices, separate numeric value and currency:
- unit_price, total_price, total_amount, tax_amount, discount_amount: Extract only numeric values
- currency: Extract currency as found in text - can be symbol ($, €, £, ₹) or word (dollars, euros, pounds, rupees) or code (USD, EUR, GBP, INR)

Return only valid JSON. Do not include any explanatory text.
Document to analyze:
"""

class QuotationFieldGenerator:
    def __init__(self):
        if not LLM_CONFIG.get("api_key"):
            raise ValueError("GROQ_API_KEY not set in environment.")
        
        self.agent = ConversableAgent(
            name="quotation_field_generator",
            system_message="You are an expert at extracting structured quotation data from documents. Return valid JSON only with no additional text or explanations.",
            llm_config=LLM_CONFIG,
            human_input_mode="NEVER",
            code_execution_config=False,
        )
        logger.info("Quotation Field Generator initialized successfully")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def generate_async(self, raw_text: str, source_file: str = "unknown") -> Dict[str, Any]:
        """Async version of generate method with retry logic"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._generate_sync, raw_text, source_file
        )

    def generate(self, raw_text: str, source_file: str = "unknown") -> Dict[str, Any]:
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
            start_time = time.perf_counter()

            reply = self.agent.generate_reply([{"role": "user", "content": prompt}])
            
            duration = time.perf_counter() - start_time
            logger.info(f"📥 LLM response received in {duration:.2f}s")

            # Parse and validate response
            parsed_response = self._parse_and_validate_response(reply, source_file)
            logger.info(f"📄 Successfully parsed quotation fields with confidence: {parsed_response.get('confidence_score', 0.0)}")
            return parsed_response.dict() if hasattr(parsed_response, 'dict') else parsed_response

        except Exception as e:
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
            validated_response = QuotationResponse(**reply)
            validated_response.source_file = source_file
            validated_response.success = True
            validated_response.message = f"Quotation processed from {source_file}"
            
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
        fallback = QuotationResponse()
        
        # Copy over any valid fields
        for field_name, field_value in raw_reply.items():
            if hasattr(fallback, field_name):
                try:
                    setattr(fallback, field_name, field_value)
                except:
                    continue
        
        fallback.source_file = source_file
        fallback.success = True
        fallback.message = f"Quotation processed with validation warnings: {validation_error}"
        fallback.requires_review = True
        fallback.confidence_score = max(0.3, fallback.confidence_score)  # Minimum confidence for partial data
        
        return fallback.dict()

class QuotationDatabase:
    """JSON-based database manager for quotation parsing results"""
    
    def __init__(self, db_path: str = "quotation_database.json"):
        self.db_path = db_path
        
        # Ensure the directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")
        
        self.init_database()
        logger.info("JSON quotation database initialized successfully")
    
    def init_database(self):
        """Initialize the JSON database file"""
        if not os.path.exists(self.db_path):
            # Create empty database structure
            initial_data = {
                "quotations": {},
                "metadata": {
                    "created_date": datetime.now().isoformat(),
                    "version": "1.0",
                    "total_quotations": 0
                }
            }
            self._save_json_data(initial_data)
            logger.info(f"Created new JSON database: {self.db_path}")
        else:
            logger.info(f"Using existing JSON database: {self.db_path}")
    
    def _load_json_data(self) -> Dict[str, Any]:
        """Load data from JSON file"""
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Return empty structure if file doesn't exist or is corrupted
            return {
                "quotations": {},
                "metadata": {
                    "created_date": datetime.now().isoformat(),
                    "version": "1.0",
                    "total_quotations": 0
                }
            }
    
    def _save_json_data(self, data: Dict[str, Any]):
        """Save data to JSON file"""
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"Error saving JSON data: {str(e)}")
            raise
    
    def save_quotation(self, indent_id: str, filename: str, quotation_data: Dict[str, Any]) -> bool:
        """Save quotation data to JSON database"""
        try:
            # Load existing data
            data = self._load_json_data()
            
            # Create unique key for the quotation
            quotation_key = f"{indent_id}_{filename}"
            
            # Add metadata to quotation data
            quotation_data['indent_id'] = indent_id
            quotation_data['filename'] = filename
            quotation_data['processed_date'] = datetime.now().isoformat()
            quotation_data['quotation_key'] = quotation_key
            
            # Save quotation
            data['quotations'][quotation_key] = quotation_data
            
            # Update metadata
            data['metadata']['total_quotations'] = len(data['quotations'])
            data['metadata']['last_updated'] = datetime.now().isoformat()
            
            # Save to file
            self._save_json_data(data)
            
            logger.info(f"Quotation saved successfully: {indent_id}/{filename}")
            logger.info(f"Total quotations in database: {data['metadata']['total_quotations']}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving quotation: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def get_quotation(self, indent_id: str, filename: str) -> Optional[Dict[str, Any]]:
        """Retrieve quotation data from JSON database"""
        try:
            data = self._load_json_data()
            quotation_key = f"{indent_id}_{filename}"
            
            if quotation_key in data['quotations']:
                return data['quotations'][quotation_key]
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving quotation: {str(e)}")
            return None
    
    def get_quotations_by_indent(self, indent_id: str) -> List[Dict[str, Any]]:
        """Get all quotations for a specific indent ID"""
        try:
            data = self._load_json_data()
            quotations = []
            
            for quotation_key, quotation_data in data['quotations'].items():
                if quotation_data.get('indent_id') == indent_id:
                    quotations.append(quotation_data)
            
            logger.info(f"Found {len(quotations)} quotations for indent ID: {indent_id}")
            return quotations
            
        except Exception as e:
            logger.error(f"Error retrieving quotations by indent: {str(e)}")
            return []
    
    def get_all_quotations(self) -> List[Dict[str, Any]]:
        """Get all quotations from the database"""
        try:
            data = self._load_json_data()
            return list(data['quotations'].values())
        except Exception as e:
            logger.error(f"Error retrieving all quotations: {str(e)}")
            return []
    
    def delete_quotation(self, indent_id: str, filename: str) -> bool:
        """Delete a quotation from the database"""
        try:
            data = self._load_json_data()
            quotation_key = f"{indent_id}_{filename}"
            
            if quotation_key in data['quotations']:
                del data['quotations'][quotation_key]
                data['metadata']['total_quotations'] = len(data['quotations'])
                data['metadata']['last_updated'] = datetime.now().isoformat()
                
                self._save_json_data(data)
                logger.info(f"Quotation deleted successfully: {indent_id}/{filename}")
                return True
            else:
                logger.warning(f"Quotation not found for deletion: {indent_id}/{filename}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting quotation: {str(e)}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            data = self._load_json_data()
            quotations = data['quotations']
            
            stats = {
                "total_quotations": len(quotations),
                "unique_indents": len(set(q.get('indent_id') for q in quotations.values())),
                "unique_suppliers": len(set(q.get('supplier_name') for q in quotations.values() if q.get('supplier_name'))),
                "total_value": sum(q.get('total_amount', 0) for q in quotations.values() if q.get('total_amount')),
                "average_confidence": sum(q.get('confidence_score', 0) for q in quotations.values()) / len(quotations) if quotations else 0,
                "requires_review_count": sum(1 for q in quotations.values() if q.get('requires_review', False)),
                "database_created": data['metadata'].get('created_date'),
                "last_updated": data['metadata'].get('last_updated')
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting database stats: {str(e)}")
            return {}

# Async wrapper function for easier usage
async def generate_quotation_fields_async(raw_text: str, source_file: str = "unknown") -> Dict[str, Any]:
    """Convenience function for async quotation field generation"""
    generator = QuotationFieldGenerator()
    return await generator.generate_async(raw_text, source_file)
