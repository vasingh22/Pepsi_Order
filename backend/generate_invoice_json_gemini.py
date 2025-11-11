"""
Script to generate invoice JSON files using Google Gemini API.
Reads standardized JSON files and uses Gemini to extract all relevant invoice fields.

SETUP:
1. Install the required package:
   pip install google-generativeai

2. Get your Gemini API key from:
   https://makersuite.google.com/app/apikey

3. Set the API key as an environment variable:
   export GEMINI_API_KEY="your-api-key-here"
   
   Or on Windows:
   set GEMINI_API_KEY=your-api-key-here

USAGE:
   python generate_invoice_json_gemini.py

The script will:
- Read all JSON files from results_standardized/
- Use Gemini API to intelligently extract all relevant invoice fields
- Save invoice JSON files to results_invoice/
- Skip files that have already been processed
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
import time

try:
    import google.generativeai as genai
except ImportError:
    print("ERROR: google-generativeai package not installed.")
    print("Please install it using: pip install google-generativeai")
    exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_gemini(api_key: Optional[str] = None, model_name: Optional[str] = None) -> genai.GenerativeModel:
    """
    Initialize Gemini API client.
    
    Args:
        api_key: Gemini API key. If not provided, reads from GEMINI_API_KEY env var.
        model_name: Model name to use. If not provided, tries common model names.
    
    Returns:
        Initialized Gemini model instance.
    """
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "Gemini API key not found. Please set GEMINI_API_KEY environment variable "
            "or pass it as an argument. Get your API key from: "
            "https://makersuite.google.com/app/apikey"
        )
    
    genai.configure(api_key=api_key)
    
    # First, try to list available models and use one that works
    try:
        logger.info("Listing available Gemini models...")
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # Extract model name from full path (e.g., "models/gemini-pro" -> "gemini-pro")
                model_name_clean = m.name.split('/')[-1] if '/' in m.name else m.name
                available_models.append(model_name_clean)
        
        logger.info(f"Found {len(available_models)} available model(s): {available_models}")
        
        if available_models:
            # If user specified a model, check if it's available
            if model_name and model_name in available_models:
                logger.info(f"Using user-specified model: {model_name}")
                return genai.GenerativeModel(model_name)
            
            # Otherwise, try models in order of preference
            preferred_models = [
                'gemini-1.5-flash',
                'gemini-1.5-pro',
                'gemini-pro',
                'gemini-1.0-pro',
            ]
            
            for preferred in preferred_models:
                if preferred in available_models:
                    logger.info(f"Using preferred model: {preferred}")
                    return genai.GenerativeModel(preferred)
            
            # If no preferred model is available, use the first one
            first_model = available_models[0]
            logger.info(f"Using first available model: {first_model}")
            return genai.GenerativeModel(first_model)
        else:
            logger.warning("No models with generateContent support found")
    except Exception as list_error:
        logger.warning(f"Could not list models: {list_error}")
        logger.info("Falling back to trying common model names...")
    
    # Fallback: Try common model names if listing failed
    model_names_to_try = model_name and [model_name] or [
        'gemini-1.5-flash',     # Fast and efficient
        'gemini-1.5-pro',       # Latest 1.5 pro
        'gemini-pro',           # Most commonly available
        'gemini-1.0-pro',       # Stable 1.0 version
    ]
    
    last_error = None
    for model_name_attempt in model_names_to_try:
        try:
            logger.info(f"Attempting to initialize model: {model_name_attempt}")
            model = genai.GenerativeModel(model_name_attempt)
            # Test the model with a simple call
            test_response = model.generate_content("test", generation_config={"max_output_tokens": 1})
            logger.info(f"Gemini API initialized successfully with model: {model_name_attempt}")
            return model
        except Exception as e:
            last_error = e
            logger.warning(f"Failed to initialize/test model {model_name_attempt}: {e}")
            continue
    
    # If everything failed, raise the last error
    raise RuntimeError(
        f"Failed to initialize any Gemini model. Last error: {last_error}. "
        "Please check your API key and available models. "
        "You can check available models at: https://ai.google.dev/models/gemini"
    )


def create_extraction_prompt(standardized_json: Dict[str, Any]) -> str:
    """
    Create a comprehensive prompt for Gemini to extract invoice fields.
    
    Args:
        standardized_json: The standardized JSON data from OCR processing.
    
    Returns:
        Formatted prompt string for Gemini.
    """
    # Convert JSON to string for the prompt
    json_str = json.dumps(standardized_json, indent=2, ensure_ascii=False)
    
    prompt = f"""You are an expert invoice data extraction system. Analyze the following standardized JSON data extracted from an invoice/order document and extract ALL relevant and important fields.

The input JSON contains:
- document_summary: Basic document metadata
- document_fingerprint: Document characteristics (vendor, language, currency, etc.)
- fields: Extracted fields like purchase_order_number, purchase_order_date, etc.
- addresses: Ship-to and Bill-to addresses (raw and normalized)
- line_items: Product/item line details
- totals: Subtotal, tax, grand_total with verification
- anomalies: Any detected issues

Your task is to extract and structure ALL relevant invoice fields into a comprehensive JSON object. Include:

1. **Core Invoice Fields:**
   - store_name / seller_name
   - buyer_name / customer_name
   - invoice_number / order_number / PO_number
   - invoice_date / order_date / PO_date
   - delivery_date (if present)
   - gst_number / tax_id (if present)

2. **Address Information:**
   - seller_address (complete, cleaned)
   - buyer_address (complete, cleaned)
   - ship_to_address (if different from buyer)
   - contact information (phone, email if present)

3. **Line Items:**
   - Extract ALL line items with:
     - name / description
     - quantity
     - unit / UOM
     - rate / unit_price
     - amount / total
     - hsn_code / product_code / SKU (if present)
     - material_id / item_id (if present)
     - discount (if present)

4. **Financial Information:**
   - subtotal
   - tax_details (type, rate, amount)
   - discount_total (if present)
   - shipping_charges (if present)
   - grand_total
   - currency

5. **Payment Information:**
   - payment_terms
   - payment_mode
   - due_date (if calculable)

6. **Additional Metadata:**
   - Include ALL fields from document_summary
   - Include ALL fields from document_fingerprint
   - Include ALL fields from the original fields object
   - Include anomalies if present
   - Preserve any other important fields you find

**IMPORTANT RULES:**
- Extract EVERYTHING that could be relevant - don't leave out any important data
- Normalize dates to YYYY-MM-DD format
- Normalize numbers (remove currency symbols, handle commas)
- Clean addresses (remove OCR artifacts, format properly)
- If a field is missing, use null or empty string, don't omit it
- Preserve the structure but make it clean and usable
- Include confidence scores if available in the source data
- For line items, ensure all numeric fields are properly parsed (not strings)

Return ONLY a valid JSON object. Do not include markdown formatting, code blocks, or explanations. Start with {{ and end with }}.

Input JSON:
{json_str}

Extracted Invoice JSON:"""

    return prompt


def extract_with_gemini(
    model: genai.GenerativeModel,
    standardized_json: Dict[str, Any],
    max_retries: int = 3,
    retry_delay: float = 2.0
) -> Dict[str, Any]:
    """
    Extract invoice fields using Gemini API.
    
    Args:
        model: Initialized Gemini model
        standardized_json: Standardized JSON data to extract from
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
    
    Returns:
        Extracted invoice JSON as dictionary
    """
    prompt = create_extraction_prompt(standardized_json)
    
    for attempt in range(max_retries):
        try:
            logger.debug(f"Calling Gemini API (attempt {attempt + 1}/{max_retries})...")
            
            # Configure generation parameters for JSON output
            generation_config = {
                "temperature": 0.1,  # Low temperature for consistent extraction
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,  # Large output for comprehensive extraction
            }
            
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Extract text from response
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parse JSON
            try:
                invoice_json = json.loads(response_text)
                logger.debug("Successfully parsed JSON response from Gemini")
                return invoice_json
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON response (attempt {attempt + 1}): {e}")
                logger.debug(f"Response text (first 500 chars): {response_text[:500]}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    # Last attempt failed - try to extract JSON from the response
                    logger.warning("Attempting to extract JSON from response text...")
                    # Try to find JSON object in the response
                    start_idx = response_text.find('{')
                    end_idx = response_text.rfind('}')
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        try:
                            invoice_json = json.loads(response_text[start_idx:end_idx+1])
                            logger.info("Successfully extracted JSON from response text")
                            return invoice_json
                        except json.JSONDecodeError:
                            pass
                    
                    raise ValueError(f"Could not parse JSON from Gemini response: {e}")
        
        except Exception as e:
            logger.warning(f"Gemini API call failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
            else:
                raise
    
    raise RuntimeError(f"Failed to extract invoice data after {max_retries} attempts")


def process_standardized_json(
    source_path: Path,
    output_dir: Path,
    model: genai.GenerativeModel
) -> bool:
    """
    Process a single standardized JSON file and generate invoice JSON.
    
    Args:
        source_path: Path to standardized JSON file
        output_dir: Directory to save invoice JSON
        model: Initialized Gemini model
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Processing: {source_path.name}")
        
        # Read standardized JSON
        with open(source_path, "r", encoding="utf-8") as f:
            standardized_data = json.load(f)
        
        # Extract invoice fields using Gemini
        invoice_json = extract_with_gemini(model, standardized_data)
        
        # Save invoice JSON
        output_path = output_dir / f"{source_path.stem}_invoice.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(invoice_json, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Successfully generated: {output_path.name}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to process {source_path.name}: {e}", exc_info=True)
        return False


def main():
    """Main function to process all standardized JSON files."""
    # Setup paths
    script_dir = Path(__file__).parent.absolute()
    standardized_dir = script_dir / "results_standardized"
    output_dir = script_dir / "results_invoice"
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)
    
    # Check if standardized directory exists
    if not standardized_dir.exists():
        logger.error(f"Standardized JSON directory not found: {standardized_dir}")
        return
    
    # Initialize Gemini
    try:
        model = initialize_gemini()
    except Exception as e:
        logger.error(f"Failed to initialize Gemini API: {e}")
        return
    
    # Find all JSON files
    json_files = list(standardized_dir.glob("*.json"))
    total_files = len(json_files)
    
    if total_files == 0:
        logger.warning(f"No JSON files found in {standardized_dir}")
        return
    
    logger.info(f"Found {total_files} standardized JSON files to process")
    
    # Process each file
    successful = 0
    failed = 0
    
    for i, json_file in enumerate(json_files, 1):
        logger.info(f"Processing file {i}/{total_files}")
        
        # Check if output already exists
        output_path = output_dir / f"{json_file.stem}_invoice.json"
        if output_path.exists():
            logger.info(f"Output already exists for {json_file.name}. Skipping.")
            successful += 1
            continue
        
        if process_standardized_json(json_file, output_dir, model):
            successful += 1
        else:
            failed += 1
        
        # Add a small delay to avoid rate limiting
        if i < total_files:
            time.sleep(0.5)
    
    # Summary
    logger.info("=" * 60)
    logger.info(f"Processing complete!")
    logger.info(f"Successfully processed: {successful}/{total_files}")
    logger.info(f"Failed: {failed}/{total_files}")
    logger.info(f"Invoice JSON files saved to: {output_dir}")


if __name__ == "__main__":
    main()

