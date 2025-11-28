#!/usr/bin/env python3
"""
Gemini-based Invoice Field Extraction - HIGH ACCURACY with Multi-Layer Validation
Features:
1. Cross-validation: Extracted values MUST exist in OCR text
2. Confidence scoring: Each field gets a confidence score
3. Flexible field matching: Handles variations in field names
4. Human review flagging: Flags uncertain extractions for review
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import time

# Import Google Generative AI
try:
    import google.generativeai as genai
except ImportError:
    print("ERROR: google-generativeai not installed!")
    print("Install with: pip install google-generativeai")
    exit(1)


class ValidatedGeminiExtractor:
    """Extract invoice fields with multi-layer validation"""
    
    def __init__(self, api_key: str, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Create directory for flagged files needing review
        self.review_dir = self.output_dir / "needs_review"
        self.review_dir.mkdir(exist_ok=True)
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('models/gemini-2.5-pro')  # Using Pro for highest accuracy
        
        # Rate limiting (Pro has lower rate limits on free tier)
        self.request_count = 0
        self.max_requests_per_minute = 2  # Pro: 2 RPM on free tier (can increase with paid)
        self.last_request_time = time.time()
    
    def rate_limit(self):
        """Simple rate limiting"""
        self.request_count += 1
        current_time = time.time()
        
        if current_time - self.last_request_time > 60:
            self.request_count = 0
            self.last_request_time = current_time
        
        if self.request_count >= self.max_requests_per_minute:
            wait_time = 60 - (current_time - self.last_request_time)
            if wait_time > 0:
                print(f"  Rate limit, waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                self.request_count = 0
                self.last_request_time = time.time()
    
    def extract_text_from_ocr(self, ocr_data: Dict) -> str:
        """Extract all text from OCR JSON"""
        try:
            text_parts = []
            if 'pages' in ocr_data:
                for page in ocr_data['pages']:
                    if 'text' in page:
                        text_parts.append(page['text'])
            return '\n'.join(text_parts)
        except Exception as e:
            print(f"Error extracting text: {e}")
            return ""
    
    def normalize_date_format(self, date_str: str) -> Optional[str]:
        """
        Convert any date format to YYYY/MM/DD
        Handles: MM/DD/YY, MM/DD/YYYY, M/D/YY, YYYY-MM-DD, etc.
        """
        if not date_str or date_str == "null":
            return None
        
        # Remove extra whitespace
        date_str = date_str.strip()
        
        # Already in YYYY/MM/DD or YYYY-MM-DD format?
        if re.match(r'^\d{4}[/-]\d{2}[/-]\d{2}$', date_str):
            return date_str.replace('-', '/')
        
        # Try to parse various formats
        date_patterns = [
            (r'^(\d{1,2})[/-](\d{1,2})[/-](\d{2})$', 'MM/DD/YY'),  # 5/07/25
            (r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$', 'MM/DD/YYYY'),  # 5/07/2025
            (r'^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$', 'YYYY/MM/DD'),  # 2025/5/7
        ]
        
        for pattern, format_type in date_patterns:
            match = re.match(pattern, date_str)
            if match:
                if format_type == 'MM/DD/YY':
                    month, day, year = match.groups()
                    # Assume 20xx for years 00-50, 19xx for 51-99
                    year_full = f"20{year}" if int(year) <= 50 else f"19{year}"
                    return f"{year_full}/{int(month):02d}/{int(day):02d}"
                
                elif format_type == 'MM/DD/YYYY':
                    month, day, year = match.groups()
                    return f"{year}/{int(month):02d}/{int(day):02d}"
                
                elif format_type == 'YYYY/MM/DD':
                    year, month, day = match.groups()
                    return f"{year}/{int(month):02d}/{int(day):02d}"
        
        # If no pattern matched, return original (let validation catch it)
        return date_str
    
    def create_extraction_prompt(self, ocr_text: str) -> str:
        """Create a comprehensive prompt with field name variations"""
        
        prompt = f"""You are a precise invoice data extraction system with STRICT accuracy requirements.

CRITICAL RULES:
1. Extract ONLY data that EXACTLY exists in the text
2. If you cannot find a field with HIGH CONFIDENCE, return null
3. Return valid JSON only, no additional text
4. Be aware that field names VARY - use semantic understanding
5. For dates: Convert to YYYY/MM/DD format (e.g., "5/07/25" becomes "2025/05/07")

FIELD NAME VARIATIONS TO HANDLE:

1. Company Name (FileName):
   - IMPORTANT: Extract the CUSTOMER/RECIPIENT company name from "Ship To" or "Invoice To" address
   - This is the company RECEIVING the goods, NOT the vendor/supplier
   - Usually the first line after "Ship To:" or "Invoice To:" or "Bill To:"
   - Example: If "Ship To: ABC Company", then FileName = "ABC Company"

2. Vendor Number (SourceOrderID):
   - May appear as: "Vendor:", "v endor:", "Vendor #:", "Supplier #:", "Vendor ID:"
   - Usually a 2-4 digit number near top of invoice
   
3. Purchase Order Number:
   - May appear as: "PO#", "PO:", "P.O.#", "Purchase Order", "Order #", "PO Number"
   - Usually prominent at top right
   
4. Delivery Date (RDD):
   - May appear as: "ETA Date", "Delivery Date", "RDD", "Requested Delivery Date", "Arrival Date", "Due Date", "Ship Date"
   - Usually in format: MM/DD/YY or MM/DD/YYYY
   - MUST CONVERT TO: YYYY/MM/DD format
   - Example: "5/07/25" → "2025/05/07", "12/31/2024" → "2024/12/31"
   
5. Shipping Address:
   - May appear under: "Ship To", "Ship To:", "Deliver To", "Delivery Address"
   - Must include: Street address, City, State, ZIP code
   
6. Billing Address:
   - May appear under: "Invoice To", "Bill To", "Sold To", "Billing Address"
   - Must include: Street address, City, State, ZIP code
   
7. Material IDs/Vendor Item Numbers:
   - May appear as: "Vendor Item", "Item #", "Material ID", "SKU", "Product Code", "Item Code"
   - Usually 4-5 digit codes in the line items table
   - Extract ALL item numbers from the products table
   
8. Line Item Count:
   - Count ONLY actual product rows in the table
   - Do NOT count: headers, footers, totals, blank rows

EXTRACTION REQUIREMENTS:

For EACH field, also provide:
- "confidence": "high", "medium", or "low"
- "source_text": The exact text snippet you extracted from (max 50 chars)

OUTPUT FORMAT:
{{
  "FileName": {{
    "value": "Customer/Recipient Company Name from Ship To address or null",
    "confidence": "high/medium/low",
    "source_text": "exact snippet from Ship To section"
  }},
  "SourceOrderID": {{
    "value": "vendor number or null",
    "confidence": "high/medium/low",
    "source_text": "exact snippet from OCR"
  }},
  "PONumber": {{
    "value": "PO number or null",
    "confidence": "high/medium/low",
    "source_text": "exact snippet from OCR"
  }},
  "RDD": {{
    "value": "date in YYYY/MM/DD format or null",
    "confidence": "high/medium/low",
    "source_text": "original date from OCR before conversion"
  }},
  "ShippingAddress": {{
    "value": "complete address with street, city, state, ZIP or null",
    "confidence": "high/medium/low",
    "source_text": "first line of address from OCR"
  }},
  "BillingAddress": {{
    "value": "complete address with street, city, state, ZIP or null",
    "confidence": "high/medium/low",
    "source_text": "first line of address from OCR"
  }},
  "MaterialIDList": {{
    "value": ["id1", "id2", ...] or [],
    "confidence": "high/medium/low",
    "source_text": "sample: first 2-3 IDs from OCR"
  }},
  "LineItemCount": {{
    "value": number,
    "confidence": "high/medium/low",
    "source_text": "where you counted from"
  }}
}}

OCR TEXT:
{ocr_text[:10000]}

Extract the fields with confidence scores. Return ONLY the JSON object."""

        return prompt
    
    def validate_exact_match(self, value: str, ocr_text: str, field_name: str) -> Tuple[bool, float]:
        """
        Validate that extracted value exists EXACTLY in OCR text
        Returns: (is_valid, confidence_score)
        """
        if not value or value == "null":
            return True, 1.0  # null is valid
        
        value_str = str(value).strip()
        
        # Exact match
        if value_str in ocr_text:
            return True, 1.0
        
        # Try with different formatting
        # For dates: try with - instead of /
        if '/' in value_str:
            if value_str.replace('/', '-') in ocr_text:
                return True, 0.95
        
        # For PO numbers: try without spaces/dashes
        if field_name == "PONumber":
            cleaned = value_str.replace(' ', '').replace('-', '')
            if cleaned in ocr_text.replace(' ', '').replace('-', ''):
                return True, 0.9
        
        # For addresses: check if major components exist
        if "Address" in field_name and value_str:
            parts = value_str.split(',')
            matches = sum(1 for part in parts if part.strip() in ocr_text)
            if matches >= len(parts) * 0.7:  # At least 70% of parts found
                return True, 0.7 + (matches / len(parts) * 0.2)
        
        # Not found
        return False, 0.0
    
    def validate_material_ids(self, material_ids: List[str], ocr_text: str) -> Tuple[List[str], float, List[str]]:
        """
        Validate each material ID exists in OCR
        Returns: (valid_ids, confidence, invalid_ids)
        """
        valid_ids = []
        invalid_ids = []
        
        for mat_id in material_ids:
            mat_id_str = str(mat_id).strip()
            if mat_id_str in ocr_text:
                valid_ids.append(mat_id_str)
            else:
                invalid_ids.append(mat_id_str)
        
        if not material_ids:
            return [], 0.0, []
        
        confidence = len(valid_ids) / len(material_ids)
        return valid_ids, confidence, invalid_ids
    
    def validate_line_count(self, extracted_count: int, material_count: int, ocr_text: str) -> Tuple[bool, float]:
        """
        Validate line item count makes sense
        Returns: (is_reasonable, confidence)
        """
        # Line count should match or be close to material count
        if extracted_count == material_count:
            return True, 1.0
        
        # Allow some variance (headers, subtotals)
        diff = abs(extracted_count - material_count)
        if diff <= 3:
            return True, 0.8
        
        # Check if count seems reasonable for OCR text length
        # Typical line item ~ 100-200 chars
        estimated_max_lines = len(ocr_text) / 100
        if extracted_count <= estimated_max_lines:
            return True, 0.6
        
        return False, 0.3
    
    def compute_overall_confidence(self, validations: Dict) -> float:
        """Compute overall confidence score from all validations"""
        scores = []
        weights = {
            'PONumber': 3.0,  # Most important
            'MaterialIDList': 2.5,
            'RDD': 2.0,
            'ShippingAddress': 1.5,
            'BillingAddress': 1.0,
            'SourceOrderID': 1.0,
            'FileName': 0.5,
            'LineItemCount': 0.5
        }
        
        for field, validation in validations.items():
            weight = weights.get(field, 1.0)
            confidence = validation.get('confidence_score', 0.0)
            scores.append(confidence * weight)
        
        if not scores:
            return 0.0
        
        return sum(scores) / sum(weights.values())
    
    def extract_with_validation(self, ocr_text: str, filename: str) -> Optional[Tuple[Dict, Dict]]:
        """
        Extract with Gemini and validate each field
        Returns: (extracted_data, validation_report)
        """
        
        try:
            # Rate limiting
            self.rate_limit()
            
            # Create prompt
            prompt = self.create_extraction_prompt(ocr_text)
            
            # Call Gemini API
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()
            
            # Parse JSON
            extracted = json.loads(response_text)
            
            # Validate each field
            validation_report = {}
            
            # Validate each field
            for field_name in ['FileName', 'SourceOrderID', 'PONumber', 'RDD', 'ShippingAddress', 'BillingAddress']:
                if field_name in extracted and isinstance(extracted[field_name], dict):
                    value = extracted[field_name].get('value')
                    gemini_confidence = extracted[field_name].get('confidence', 'low')
                    source_text = extracted[field_name].get('source_text', '')
                    
                    # Normalize date format if this is RDD field
                    if field_name == 'RDD' and value:
                        normalized_date = self.normalize_date_format(value)
                        if normalized_date and normalized_date != value:
                            print(f"  📅 Date normalized: {value} → {normalized_date}")
                            value = normalized_date
                    
                    # Validate against OCR
                    is_valid, confidence_score = self.validate_exact_match(value, ocr_text, field_name)
                    
                    validation_report[field_name] = {
                        'value': value,
                        'is_valid': is_valid,
                        'confidence_score': confidence_score,
                        'gemini_confidence': gemini_confidence,
                        'source_text': source_text,
                        'needs_review': not is_valid or confidence_score < 0.7
                    }
            
            # Validate Material IDs
            if 'MaterialIDList' in extracted and isinstance(extracted['MaterialIDList'], dict):
                material_ids = extracted['MaterialIDList'].get('value', [])
                valid_ids, confidence, invalid_ids = self.validate_material_ids(material_ids, ocr_text)
                
                validation_report['MaterialIDList'] = {
                    'value': valid_ids,
                    'is_valid': len(invalid_ids) == 0,
                    'confidence_score': confidence,
                    'gemini_confidence': extracted['MaterialIDList'].get('confidence', 'low'),
                    'source_text': extracted['MaterialIDList'].get('source_text', ''),
                    'invalid_ids': invalid_ids,
                    'needs_review': len(invalid_ids) > 0 or confidence < 0.8
                }
            
            # Validate Line Count
            if 'LineItemCount' in extracted and isinstance(extracted['LineItemCount'], dict):
                line_count = extracted['LineItemCount'].get('value', 0)
                material_count = len(validation_report.get('MaterialIDList', {}).get('value', []))
                is_reasonable, confidence = self.validate_line_count(line_count, material_count, ocr_text)
                
                validation_report['LineItemCount'] = {
                    'value': line_count,
                    'is_valid': is_reasonable,
                    'confidence_score': confidence,
                    'gemini_confidence': extracted['LineItemCount'].get('confidence', 'low'),
                    'source_text': extracted['LineItemCount'].get('source_text', ''),
                    'needs_review': not is_reasonable or confidence < 0.7
                }
            
            # Compute overall confidence
            overall_confidence = self.compute_overall_confidence(validation_report)
            validation_report['_overall'] = {
                'confidence_score': overall_confidence,
                'needs_review': overall_confidence < 0.75
            }
            
            return extracted, validation_report
            
        except json.JSONDecodeError as e:
            print(f"  ✗ JSON parsing error: {e}")
            return None, None
        except Exception as e:
            print(f"  ✗ Gemini API error: {e}")
            return None, None
    
    def build_final_output(self, extracted: Dict, validation_report: Dict, ocr_text: str) -> Dict:
        """Build final output with validated data"""
        
        # Extract validated values
        filename = validation_report.get('FileName', {}).get('value')
        source_order_id = validation_report.get('SourceOrderID', {}).get('value')
        po_number = validation_report.get('PONumber', {}).get('value')
        rdd = validation_report.get('RDD', {}).get('value')
        shipping_address = validation_report.get('ShippingAddress', {}).get('value')
        billing_address = validation_report.get('BillingAddress', {}).get('value')
        material_ids = validation_report.get('MaterialIDList', {}).get('value', [])
        line_item_count = validation_report.get('LineItemCount', {}).get('value', 0)
        
        # Standard validations
        material_count = len(material_ids)
        count_check = material_count > 0
        line_item_match = (line_item_count == material_count) if material_count > 0 and line_item_count > 0 else False
        
        po_validation = {
            'Length>5': len(str(po_number)) > 5 if po_number else False,
            'OnlyNumeric': str(po_number).isdigit() if po_number else False
        }
        
        mandatory_fields = [po_number, rdd, shipping_address]
        all_mandatory = all(field is not None and field != "" for field in mandatory_fields)
        
        # Build output
        result = {
            "Invoice_Header_Fields": {
                "FileName": filename,
                "SourceOrderID": source_order_id,
                "PONumber": po_number,
                "RDD": rdd,
                "ShippingAddress": shipping_address,
                "BillingAddress": billing_address
            },
            "Line_Item_Fields": {
                "MaterialIDList": material_ids,
                "MaterialIDCount": material_count,
                "LineItemCount": line_item_count
            },
            "Validation_and_Quality_Checks": {
                "Count>0": count_check,
                "LineItem=IDs": line_item_match,
                "Length>5": po_validation['Length>5'],
                "OnlyNumeric": po_validation['OnlyNumeric'],
                "All Mandatory Fields extracted": all_mandatory
            },
            "Confidence_and_Validation": {
                "overall_confidence": validation_report.get('_overall', {}).get('confidence_score', 0.0),
                "needs_human_review": validation_report.get('_overall', {}).get('needs_review', True),
                "field_confidences": {
                    field: {
                        "score": validation_report.get(field, {}).get('confidence_score', 0.0),
                        "is_valid": validation_report.get(field, {}).get('is_valid', False),
                        "needs_review": validation_report.get(field, {}).get('needs_review', True)
                    }
                    for field in ['PONumber', 'RDD', 'ShippingAddress', 'BillingAddress', 'MaterialIDList', 'LineItemCount']
                }
            }
        }
        
        return result
    
    def process_single_file(self, ocr_file_path: Path) -> Optional[Dict]:
        """Process a single OCR file with full validation"""
        
        try:
            # Load OCR data
            with open(ocr_file_path, 'r', encoding='utf-8') as f:
                ocr_data = json.load(f)
            
            # Extract text
            ocr_text = self.extract_text_from_ocr(ocr_data)
            if not ocr_text:
                print(f"  ✗ No text extracted from OCR")
                return None
            
            # Extract with validation
            extracted, validation_report = self.extract_with_validation(ocr_text, ocr_file_path.name)
            if not extracted or not validation_report:
                return None
            
            # Build final output
            result = self.build_final_output(extracted, validation_report, ocr_text)
            
            return result
            
        except Exception as e:
            print(f"  ✗ Error processing file: {e}")
            return None
    
    def process_all_files(self) -> Dict[str, Any]:
        """Process all OCR files"""
        
        json_files = sorted(
            self.input_dir.glob('*.json'),
            key=lambda x: self._extract_number_from_filename(x.name)
        )
        
        print(f"Found {len(json_files)} JSON files to process")
        print(f"Using Gemini model: {self.model._model_name}")
        print(f"Validation: Multi-layer with confidence scoring")
        print()
        
        stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'complete_extractions': 0,
            'needs_review': 0,
            'high_confidence': 0,
            'errors': []
        }
        
        for idx, json_file in enumerate(json_files, 1):
            print(f"Processing [{idx}/{len(json_files)}]: {json_file.name}", end=' ')
            
            try:
                result = self.process_single_file(json_file)
                
                if result:
                    output_filename = f"{json_file.stem}_extracted.json"
                    
                    # Check if needs review
                    needs_review = result.get('Confidence_and_Validation', {}).get('needs_human_review', True)
                    confidence = result.get('Confidence_and_Validation', {}).get('overall_confidence', 0.0)
                    
                    # Save to appropriate directory
                    if needs_review:
                        output_path = self.review_dir / output_filename
                        stats['needs_review'] += 1
                    else:
                        output_path = self.output_dir / output_filename
                        stats['high_confidence'] += 1
                    
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    
                    stats['successful'] += 1
                    
                    if result['Validation_and_Quality_Checks']['All Mandatory Fields extracted']:
                        stats['complete_extractions'] += 1
                    
                    # Summary
                    po = result['Invoice_Header_Fields']['PONumber']
                    mat_count = result['Line_Item_Fields']['MaterialIDCount']
                    review_flag = "⚠️ REVIEW" if needs_review else "✓"
                    print(f"{review_flag} PO: {po or 'None'}, Materials: {mat_count}, Confidence: {confidence:.2f}")
                else:
                    stats['failed'] += 1
                    print("✗ Failed")
                
                stats['total'] += 1
                
            except Exception as e:
                stats['failed'] += 1
                stats['errors'].append(f"{json_file.name}: {str(e)}")
                print(f"✗ Error: {e}")
        
        return stats
    
    def _extract_number_from_filename(self, filename: str) -> int:
        """Extract number from filename for sorting"""
        match = re.search(r'_(\d+)\.pdf', filename)
        if match:
            return int(match.group(1))
        return 0
    
    def generate_summary_report(self, stats: Dict[str, Any]):
        """Generate summary report"""
        
        print("\n" + "="*70)
        print("VALIDATED GEMINI EXTRACTION SUMMARY")
        print("="*70)
        print(f"Total files processed: {stats['total']}")
        print(f"Successful extractions: {stats['successful']}")
        print(f"Complete extractions: {stats['complete_extractions']}")
        print(f"High confidence (auto-approved): {stats['high_confidence']}")
        print(f"Needs human review: {stats['needs_review']}")
        print(f"Failed extractions: {stats['failed']}")
        print(f"Success rate: {stats['successful']/stats['total']*100:.1f}%")
        print(f"Auto-approval rate: {stats['high_confidence']/stats['total']*100:.1f}%")
        
        if stats['errors']:
            print(f"\nErrors: {len(stats['errors'])}")
            for error in stats['errors'][:10]:
                print(f"  - {error}")
        
        print("="*70)
        print(f"\nFiles saved to:")
        print(f"  - High confidence: {self.output_dir}/")
        print(f"  - Needs review: {self.review_dir}/")
        print("="*70)
        
        # Save summary
        summary_path = self.output_dir / "validation_summary.txt"
        with open(summary_path, 'w') as f:
            f.write(f"Validated Gemini Extraction Summary - {datetime.now()}\n")
            f.write(f"Total: {stats['total']}\n")
            f.write(f"Successful: {stats['successful']}\n")
            f.write(f"Complete: {stats['complete_extractions']}\n")
            f.write(f"High Confidence: {stats['high_confidence']}\n")
            f.write(f"Needs Review: {stats['needs_review']}\n")
            f.write(f"Failed: {stats['failed']}\n")
            f.write(f"\nErrors:\n")
            for error in stats['errors']:
                f.write(f"  {error}\n")


def main():
    """Main execution"""
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("="*70)
        print("ERROR: GEMINI_API_KEY environment variable not set!")
        print("="*70)
        print("\nSet your API key:")
        print("  export GEMINI_API_KEY='your-api-key-here'")
        print("\nGet key from: https://makersuite.google.com/app/apikey")
        print("="*70)
        exit(1)
    
    INPUT_DIR = "/Users/vasingh/Desktop/Backend/results_ocr-final"
    OUTPUT_DIR = "/Users/vasingh/Desktop/Backend/extracted_invoice_fields_validated"
    
    print("="*70)
    print("VALIDATED GEMINI Invoice Field Extraction")
    print("="*70)
    print(f"Input: {INPUT_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"\nUsing: Gemini 1.5 Pro (Highest Accuracy)")
    print("\nFeatures:")
    print("  ✓ Multi-layer validation (extracted values checked against OCR)")
    print("  ✓ Confidence scoring for each field")
    print("  ✓ Flexible field name matching (handles variations)")
    print("  ✓ Auto-flags uncertain extractions for human review")
    print("  ✓ Prevents hallucination with cross-validation")
    print("  ✓ Date normalization to YYYY/MM/DD format")
    print("  ✓ Company name from Ship To address")
    print()
    
    extractor = ValidatedGeminiExtractor(api_key, INPUT_DIR, OUTPUT_DIR)
    stats = extractor.process_all_files()
    extractor.generate_summary_report(stats)
    
    print(f"\n✓ Extraction complete!")
    print(f"  High confidence files: {OUTPUT_DIR}/")
    print(f"  Files needing review: {OUTPUT_DIR}/needs_review/")


if __name__ == "__main__":
    main()

