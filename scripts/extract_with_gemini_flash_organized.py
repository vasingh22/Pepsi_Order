#!/usr/bin/env python3
"""
Gemini 1.5 Flash Invoice Extraction with Organized Output
Separates files by status: success, errors, needs_review
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import time
import traceback

# Import Google Generative AI
try:
    import google.generativeai as genai
except ImportError:
    print("ERROR: google-generativeai not installed!")
    print("Install with: pip install google-generativeai")
    exit(1)


class OrganizedGeminiExtractor:
    """Extract invoice fields with organized output by status"""
    
    def __init__(self, api_key: str, input_dir: str, output_base_dir: str):
        self.input_dir = Path(input_dir)
        self.output_base_dir = Path(output_base_dir)
        self.output_base_dir.mkdir(exist_ok=True)
        
        # Create organized subdirectories
        self.success_dir = self.output_base_dir / "successful"
        self.review_dir = self.output_base_dir / "needs_review"
        self.error_dir = self.output_base_dir / "errors"
        
        self.success_dir.mkdir(exist_ok=True)
        self.review_dir.mkdir(exist_ok=True)
        self.error_dir.mkdir(exist_ok=True)
        
        # Configure Gemini Flash (using latest available model)
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')  # Latest Flash model
        
        # Rate limiting
        self.request_count = 0
        self.max_requests_per_minute = 15  # Flash: 15 RPM on free tier
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
                print(f"  ⏱️  Rate limit, waiting {wait_time:.1f}s...")
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
            raise Exception(f"Error extracting text: {e}")
    
    def normalize_date_format(self, date_str: str) -> Optional[str]:
        """Convert any date format to YYYY/MM/DD"""
        if not date_str or date_str == "null":
            return None
        
        date_str = date_str.strip()
        
        # Already in YYYY/MM/DD or YYYY-MM-DD format?
        if re.match(r'^\d{4}[/-]\d{2}[/-]\d{2}$', date_str):
            return date_str.replace('-', '/')
        
        # Try to parse various formats
        date_patterns = [
            (r'^(\d{1,2})[/-](\d{1,2})[/-](\d{2})$', 'MM/DD/YY'),
            (r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$', 'MM/DD/YYYY'),
            (r'^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$', 'YYYY/MM/DD'),
        ]
        
        for pattern, format_type in date_patterns:
            match = re.match(pattern, date_str)
            if match:
                if format_type == 'MM/DD/YY':
                    month, day, year = match.groups()
                    year_full = f"20{year}" if int(year) <= 50 else f"19{year}"
                    return f"{year_full}/{int(month):02d}/{int(day):02d}"
                elif format_type == 'MM/DD/YYYY':
                    month, day, year = match.groups()
                    return f"{year}/{int(month):02d}/{int(day):02d}"
                elif format_type == 'YYYY/MM/DD':
                    year, month, day = match.groups()
                    return f"{year}/{int(month):02d}/{int(day):02d}"
        
        return date_str
    
    def create_extraction_prompt(self, ocr_text: str) -> str:
        """Create extraction prompt"""
        
        prompt = f"""You are a precise invoice data extraction system.

CRITICAL RULES:
1. Extract ONLY data that exists in the text
2. If you cannot find a field, return null
3. Return valid JSON only
4. Convert dates to YYYY/MM/DD format
5. Extract customer company name from "Ship To" or "Invoice To" address

FIELDS TO EXTRACT:

1. FileName: Customer company name from "Ship To" or "Invoice To" address (first line after the label)
2. SourceOrderID: Vendor number (look for "Vendor:", "v endor:", "Vendor #")
3. PONumber: Purchase order number (look for "PO#", "PO:", "Purchase Order")
4. RDD: Delivery/arrival date - FIND the date FIRST in OCR using ANY of these labels:
   - "ETA Date", "ETA:", "ETA"
   - "Delivery Date", "DELIVERY DATE:", "Delivery:"
   - "RDD", "Requested Delivery Date"
   - "Ship Date", "Shipping Date"
   - "Arrival Date", "Due Date"
   - "Expected Date"
   IMPORTANT: Extract the EXACT date as it appears in OCR, then convert to YYYY/MM/DD format
5. ShippingAddress: Complete ship-to address (street, city, state, ZIP)
6. BillingAddress: Complete billing address (street, city, state, ZIP)
7. MaterialIDList: **CRITICAL** - Extract ALL vendor item numbers/SKUs from the line items section
   - Look for columns labeled: "Item", "Item #", "Product Code", "SKU", "Material", "Vendor Item"
   - These are typically 4-6 digit numeric codes
   - Extract EVERY item number from EVERY line in the line items table
   - DO NOT skip any items
   - Example: If you see rows with items 75397, 98462, 11379, etc., extract ALL of them
8. LineItemCount: Count of actual product rows only (not headers/footers)

OUTPUT FORMAT:
{{
  "FileName": {{
    "value": "Company name from Ship To or null",
    "confidence": "high/medium/low",
    "source_text": "snippet from OCR"
  }},
  "SourceOrderID": {{
    "value": "vendor number or null",
    "confidence": "high/medium/low",
    "source_text": "snippet"
  }},
  "PONumber": {{
    "value": "PO number or null",
    "confidence": "high/medium/low",
    "source_text": "snippet"
  }},
  "RDD": {{
    "value": "date in YYYY/MM/DD or null",
    "confidence": "high/medium/low",
    "source_text": "EXACT original date as found in OCR (e.g., 05/08/2025)"
  }},
  "ShippingAddress": {{
    "value": "complete address or null",
    "confidence": "high/medium/low",
    "source_text": "first line"
  }},
  "BillingAddress": {{
    "value": "complete address or null",
    "confidence": "high/medium/low",
    "source_text": "first line"
  }},
  "MaterialIDList": {{
    "value": ["id1", "id2", ...] or [],
    "confidence": "high/medium/low",
    "source_text": "sample IDs"
  }},
  "LineItemCount": {{
    "value": number,
    "confidence": "high/medium/low",
    "source_text": "where counted"
  }}
}}

OCR TEXT:
{ocr_text[:65000]}

Extract now. Return ONLY JSON."""

        return prompt
    
    def validate_extraction(self, extracted: Dict, ocr_text: str) -> Tuple[Dict, List[str]]:
        """
        Validate extraction and return validation report + error list
        Returns: (validation_report, error_list)
        """
        validation_report = {}
        errors = []
        
        # Validate each field
        for field_name in ['FileName', 'SourceOrderID', 'PONumber', 'RDD', 'ShippingAddress', 'BillingAddress']:
            if field_name in extracted and isinstance(extracted[field_name], dict):
                value = extracted[field_name].get('value')
                confidence = extracted[field_name].get('confidence', 'low')
                source_text = extracted[field_name].get('source_text', '')
                
                # Normalize date AFTER extraction
                if field_name == 'RDD' and value:
                    normalized = self.normalize_date_format(value)
                    if normalized:
                        value = normalized
                
                # Simple validation
                is_valid = value is not None and value != ""
                
                # Check if value exists in OCR
                in_ocr = False
                if value:
                    # For RDD, check if the ORIGINAL date (source_text) is in OCR
                    if field_name == 'RDD':
                        # Use source_text which should contain the original date from OCR
                        if source_text and source_text.strip():
                            # Check various formats of the original date
                            date_variations = [source_text.strip()]
                            # Also check without leading zeros
                            date_variations.append(source_text.strip().lstrip('0'))
                            # Check with different separators
                            date_variations.append(source_text.strip().replace('/', '-'))
                            in_ocr = any(str(var) in ocr_text for var in date_variations if var)
                        else:
                            # Fallback: if no source_text, assume it's valid
                            in_ocr = True
                    # For addresses, check if key parts exist
                    elif "Address" in field_name:
                        parts = str(value).split(',')
                        in_ocr = any(part.strip() in ocr_text for part in parts if part.strip())
                    else:
                        in_ocr = str(value) in ocr_text
                
                confidence_score = 1.0 if in_ocr else 0.5
                
                validation_report[field_name] = {
                    'value': value,
                    'is_valid': is_valid,
                    'in_ocr': in_ocr,
                    'confidence_score': confidence_score,
                    'gemini_confidence': confidence
                }
                
                if not is_valid:
                    errors.append(f"{field_name}: Missing/null")
                elif not in_ocr and field_name != 'RDD':  # Don't flag RDD - date format conversion is expected
                    errors.append(f"{field_name}: Not found in OCR (possible hallucination)")
        
        # Validate Material IDs
        if 'MaterialIDList' in extracted and isinstance(extracted['MaterialIDList'], dict):
            material_ids = extracted['MaterialIDList'].get('value', [])
            # Ensure material_ids is a list (handle None case)
            if material_ids is None:
                material_ids = []
            valid_ids = [mid for mid in material_ids if str(mid) in ocr_text]
            invalid_ids = [mid for mid in material_ids if str(mid) not in ocr_text]
            
            validation_report['MaterialIDList'] = {
                'value': valid_ids,
                'is_valid': len(valid_ids) > 0,
                'confidence_score': len(valid_ids) / len(material_ids) if material_ids else 0.0,
                'invalid_ids': invalid_ids
            }
            
            if invalid_ids:
                errors.append(f"MaterialIDList: {len(invalid_ids)} IDs not in OCR")
        
        # Line count
        if 'LineItemCount' in extracted and isinstance(extracted['LineItemCount'], dict):
            line_count = extracted['LineItemCount'].get('value', 0)
            material_count = len(validation_report.get('MaterialIDList', {}).get('value', []))
            
            validation_report['LineItemCount'] = {
                'value': line_count,
                'is_valid': line_count > 0,
                'confidence_score': 1.0 if line_count == material_count else 0.7
            }
        
        # Overall confidence
        scores = [v.get('confidence_score', 0) for v in validation_report.values() if 'confidence_score' in v]
        overall_confidence = sum(scores) / len(scores) if scores else 0.0
        
        # Check if RDD is missing/not found in OCR
        rdd_missing = False
        if 'RDD' in validation_report:
            rdd_value = validation_report['RDD'].get('value')
            if not rdd_value or rdd_value is None:
                rdd_missing = True
        
        # If RDD is missing, lower confidence and flag for review
        if rdd_missing:
            overall_confidence = min(overall_confidence, 0.85)  # Cap at 85% if RDD missing
        
        # Only flag for review if: confidence < 90% OR critical errors (not minor warnings)
        critical_errors = [e for e in errors if 'Missing/null' in e and ('PONumber' in e or 'RDD' in e)]
        needs_review = overall_confidence < 0.90 or len(critical_errors) > 0 or rdd_missing  # RDD missing = needs review
        
        validation_report['_overall'] = {
            'confidence': overall_confidence,
            'needs_review': needs_review,
            'minor_warnings': len(errors) - len(critical_errors),
            'critical_errors': len(critical_errors),
            'rdd_missing': rdd_missing
        }
        
        return validation_report, errors
    
    def extract_with_gemini(self, ocr_text: str) -> Tuple[Optional[Dict], Optional[List[str]]]:
        """
        Extract with Gemini
        Returns: (extracted_data, errors) or (None, error_list)
        """
        try:
            self.rate_limit()
            
            prompt = self.create_extraction_prompt(ocr_text)
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()
            
            extracted = json.loads(response_text)
            return extracted, None
            
        except json.JSONDecodeError as e:
            return None, [f"JSON parse error: {e}"]
        except Exception as e:
            return None, [f"Gemini API error: {e}"]
    
    def build_final_output(self, validation_report: Dict, errors: List[str]) -> Dict:
        """Build final output structure"""
        
        filename = validation_report.get('FileName', {}).get('value')
        source_order_id = validation_report.get('SourceOrderID', {}).get('value')
        po_number = validation_report.get('PONumber', {}).get('value')
        rdd = validation_report.get('RDD', {}).get('value')
        shipping_address = validation_report.get('ShippingAddress', {}).get('value')
        billing_address = validation_report.get('BillingAddress', {}).get('value')
        material_ids = validation_report.get('MaterialIDList', {}).get('value', [])
        line_item_count = validation_report.get('LineItemCount', {}).get('value', 0)
        
        material_count = len(material_ids)
        overall_confidence = validation_report.get('_overall', {}).get('confidence', 0.0)
        needs_review = validation_report.get('_overall', {}).get('needs_review', True)
        
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
                "Count>0": material_count > 0,
                "LineItem=IDs": line_item_count == material_count if material_count > 0 else False,
                "Length>5": len(str(po_number)) > 5 if po_number else False,
                "OnlyNumeric": str(po_number).isdigit() if po_number else False,
                "All Mandatory Fields extracted": all([po_number, rdd, shipping_address])
            },
            "Confidence_and_Validation": {
                "overall_confidence": overall_confidence,
                "needs_human_review": needs_review,
                "validation_errors": errors
            }
        }
        
        return result
    
    def process_single_file(self, ocr_file_path: Path) -> Tuple[Optional[Dict], str, List[str]]:
        """
        Process a single file
        Returns: (result, status, errors)
        status = "success" | "needs_review" | "error"
        """
        errors = []
        
        try:
            # Load OCR
            with open(ocr_file_path, 'r', encoding='utf-8') as f:
                ocr_data = json.load(f)
            
            # Extract text
            ocr_text = self.extract_text_from_ocr(ocr_data)
            if not ocr_text:
                return None, "error", ["No text in OCR"]
            
            # Extract with Gemini
            extracted, extract_errors = self.extract_with_gemini(ocr_text)
            if extract_errors:
                return None, "error", extract_errors
            
            # Validate
            validation_report, validation_errors = self.validate_extraction(extracted, ocr_text)
            errors.extend(validation_errors)
            
            # Build output
            result = self.build_final_output(validation_report, errors)
            
            # Use the needs_human_review flag which respects the 90% threshold
            if result['Confidence_and_Validation']['needs_human_review']:
                status = "needs_review"
            else:
                status = "success"
            
            return result, status, errors
            
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            return None, "error", [error_msg]
    
    def process_all_files(self) -> Dict[str, Any]:
        """Process all OCR files"""
        
        json_files = sorted(
            self.input_dir.glob('*.json'),
            key=lambda x: self._extract_number_from_filename(x.name)
        )
        
        print(f"Found {len(json_files)} JSON files to process")
        print(f"Using: Gemini 1.5 Flash")
        print(f"Output organized by status:")
        print(f"  ✅ Success: {self.success_dir}")
        print(f"  ⚠️  Review: {self.review_dir}")
        print(f"  ❌ Errors: {self.error_dir}")
        print()
        
        stats = {
            'total': 0,
            'successful': 0,
            'needs_review': 0,
            'errors': 0,
            'error_details': []
        }
        
        for idx, json_file in enumerate(json_files, 1):
            print(f"[{idx}/{len(json_files)}] {json_file.name[:50]}", end=' ')
            
            try:
                result, status, errors = self.process_single_file(json_file)
                
                output_filename = f"{json_file.stem}_extracted.json"
                
                if status == "success":
                    output_path = self.success_dir / output_filename
                    stats['successful'] += 1
                    icon = "✅"
                elif status == "needs_review":
                    output_path = self.review_dir / output_filename
                    stats['needs_review'] += 1
                    icon = "⚠️ "
                else:  # error
                    output_path = self.error_dir / output_filename
                    stats['errors'] += 1
                    stats['error_details'].append(f"{json_file.name}: {', '.join(errors)}")
                    icon = "❌"
                    
                    # For errors, save error info
                    if result is None:
                        result = {
                            "error": True,
                            "errors": errors,
                            "filename": json_file.name
                        }
                
                # Save result
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                # Print status
                if result and "Invoice_Header_Fields" in result:
                    po = result['Invoice_Header_Fields'].get('PONumber', 'None')
                    conf = result['Confidence_and_Validation'].get('overall_confidence', 0)
                    print(f"{icon} PO: {po}, Conf: {conf:.2f}")
                else:
                    print(f"{icon} Error: {errors[0] if errors else 'Unknown'}")
                
                stats['total'] += 1
                
            except Exception as e:
                stats['errors'] += 1
                stats['error_details'].append(f"{json_file.name}: {str(e)}")
                print(f"❌ Exception: {str(e)[:50]}")
        
        return stats
    
    def _extract_number_from_filename(self, filename: str) -> int:
        """Extract number from filename for sorting"""
        match = re.search(r'_(\d+)\.pdf', filename)
        return int(match.group(1)) if match else 0
    
    def generate_summary_report(self, stats: Dict[str, Any]):
        """Generate summary report"""
        
        print("\n" + "="*70)
        print("EXTRACTION SUMMARY - Gemini 1.5 Flash")
        print("="*70)
        print(f"Total files processed: {stats['total']}")
        print(f"✅ Successful (high confidence): {stats['successful']}")
        print(f"⚠️  Needs Review (low confidence): {stats['needs_review']}")
        print(f"❌ Errors (failed extraction): {stats['errors']}")
        print(f"\nSuccess rate: {(stats['successful'] + stats['needs_review'])/stats['total']*100:.1f}%")
        print(f"High confidence rate: {stats['successful']/stats['total']*100:.1f}%")
        
        if stats['error_details']:
            print(f"\n❌ Error Details ({len(stats['error_details'])} files):")
            for error in stats['error_details'][:10]:
                print(f"  - {error}")
            if len(stats['error_details']) > 10:
                print(f"  ... and {len(stats['error_details']) - 10} more")
        
        print("="*70)
        print(f"\n📁 Output Directories:")
        print(f"  ✅ Success: {self.success_dir}/")
        print(f"  ⚠️  Review:  {self.review_dir}/")
        print(f"  ❌ Errors:  {self.error_dir}/")
        print("="*70)
        
        # Save summary
        summary_path = self.output_base_dir / "extraction_summary.txt"
        with open(summary_path, 'w') as f:
            f.write(f"Extraction Summary - {datetime.now()}\n")
            f.write(f"Model: Gemini 1.5 Flash\n")
            f.write(f"Total: {stats['total']}\n")
            f.write(f"Successful: {stats['successful']}\n")
            f.write(f"Needs Review: {stats['needs_review']}\n")
            f.write(f"Errors: {stats['errors']}\n\n")
            f.write(f"Error Details:\n")
            for error in stats['error_details']:
                f.write(f"  {error}\n")


def main():
    """Main execution"""
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("="*70)
        print("ERROR: GEMINI_API_KEY not set!")
        print("="*70)
        print("Set your API key:")
        print("  export GEMINI_API_KEY='your-key-here'")
        print("Get key from: https://makersuite.google.com/app/apikey")
        exit(1)
    
    INPUT_DIR = "/Users/vasingh/Desktop/Backend/results_ocr-final"
    OUTPUT_DIR = "/Users/vasingh/Desktop/Backend/extracted_final_v2"
    
    print("="*70)
    print("Gemini 1.5 Flash - Organized Invoice Extraction")
    print("="*70)
    print(f"Input: {INPUT_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print("\nFiles will be organized by status:")
    print("  ✅ Successful extractions → successful/")
    print("  ⚠️  Low confidence → needs_review/")
    print("  ❌ Extraction errors → errors/")
    print()
    
    extractor = OrganizedGeminiExtractor(api_key, INPUT_DIR, OUTPUT_DIR)
    stats = extractor.process_all_files()
    extractor.generate_summary_report(stats)
    
    print(f"\n✓ Complete! Check folders for organized results.")


if __name__ == "__main__":
    main()

