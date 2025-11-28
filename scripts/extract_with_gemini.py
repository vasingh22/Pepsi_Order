#!/usr/bin/env python3
"""
Gemini-based Invoice Field Extraction - High Accuracy
Uses Google Gemini API to extract structured fields from OCR text
Includes validation to prevent hallucination
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import time

# Import Google Generative AI
try:
    import google.generativeai as genai
except ImportError:
    print("ERROR: google-generativeai not installed!")
    print("Install with: pip install google-generativeai")
    exit(1)


class GeminiInvoiceExtractor:
    """Extract invoice fields using Gemini AI"""
    
    def __init__(self, api_key: str, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Rate limiting
        self.request_count = 0
        self.max_requests_per_minute = 15  # Adjust based on your API quota
        self.last_request_time = time.time()
    
    def rate_limit(self):
        """Simple rate limiting to avoid API quota issues"""
        self.request_count += 1
        
        # Reset counter every minute
        current_time = time.time()
        if current_time - self.last_request_time > 60:
            self.request_count = 0
            self.last_request_time = current_time
        
        # If we've hit the limit, wait
        if self.request_count >= self.max_requests_per_minute:
            wait_time = 60 - (current_time - self.last_request_time)
            if wait_time > 0:
                print(f"  Rate limit reached, waiting {wait_time:.1f}s...")
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
    
    def create_extraction_prompt(self, ocr_text: str) -> str:
        """Create a precise prompt for Gemini to extract fields"""
        
        prompt = f"""You are a precise invoice data extraction system. Extract the following fields from this purchase order/invoice OCR text.

CRITICAL RULES:
1. Only extract data that exists in the text - DO NOT make up or infer data
2. If a field is not found, return null
3. Return ONLY valid JSON, no additional text
4. Material IDs are vendor item numbers (typically 4-5 digit codes in the line items table)
5. Line item count = number of product rows in the table (not headers/footers)

REQUIRED FIELDS TO EXTRACT:

1. FileName: The vendor/company name (e.g., "Colonial Wholesale Dist. LLC")
2. SourceOrderID: The vendor number (look for "vendor:", "v endor:", "vendor #")
3. PONumber: Purchase order number (look for "PO#", "PO:", "Purchase Order")
4. RDD: Requested delivery date (look for "ETA Date", "Delivery Date", "RDD", "Arrival Date")
5. ShippingAddress: Complete ship-to address including street, city, state, ZIP (look for "Ship To")
6. BillingAddress: Complete billing/invoice-to address including street, city, state, ZIP (look for "Invoice To", "Bill To", "Sold To")
7. MaterialIDList: Array of ALL vendor item numbers/material IDs from the line items table (typically 4-5 digit codes)
8. LineItemCount: Accurate count of product line items in the table

OUTPUT FORMAT (strict JSON):
{{
  "FileName": "string or null",
  "SourceOrderID": "string or null",
  "PONumber": "string or null",
  "RDD": "string or null",
  "ShippingAddress": "string or null",
  "BillingAddress": "string or null",
  "MaterialIDList": ["id1", "id2", ...] or [],
  "LineItemCount": number
}}

OCR TEXT:
{ocr_text[:8000]}

Extract the fields now. Return ONLY the JSON object, nothing else."""

        return prompt
    
    def validate_extraction(self, extracted: Dict, ocr_text: str) -> Dict:
        """Validate extracted fields against OCR text to prevent hallucination"""
        
        validation_results = {}
        
        # Validate PO Number exists in text
        if extracted.get('PONumber'):
            po = extracted['PONumber']
            if po in ocr_text or po.replace('-', '') in ocr_text:
                validation_results['PONumber'] = True
            else:
                validation_results['PONumber'] = False
                print(f"  ⚠️ Warning: PO Number '{po}' not found in OCR text")
        
        # Validate Material IDs exist in text
        if extracted.get('MaterialIDList'):
            valid_ids = []
            for mat_id in extracted['MaterialIDList']:
                if str(mat_id) in ocr_text:
                    valid_ids.append(mat_id)
                else:
                    print(f"  ⚠️ Warning: Material ID '{mat_id}' not found in OCR text")
            extracted['MaterialIDList'] = valid_ids
            validation_results['MaterialIDs'] = len(valid_ids) > 0
        
        # Validate RDD exists
        if extracted.get('RDD'):
            rdd = extracted['RDD']
            if rdd in ocr_text or rdd.replace('/', '-') in ocr_text:
                validation_results['RDD'] = True
            else:
                validation_results['RDD'] = False
                print(f"  ⚠️ Warning: RDD '{rdd}' not found in OCR text")
        
        return validation_results
    
    def extract_with_gemini(self, ocr_text: str, filename: str) -> Optional[Dict]:
        """Use Gemini to extract fields from OCR text"""
        
        try:
            # Rate limiting
            self.rate_limit()
            
            # Create prompt
            prompt = self.create_extraction_prompt(ocr_text)
            
            # Call Gemini API
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response (sometimes Gemini adds markdown)
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()
            
            # Parse JSON
            extracted = json.loads(response_text)
            
            # Validate against OCR text
            validation = self.validate_extraction(extracted, ocr_text)
            
            return extracted
            
        except json.JSONDecodeError as e:
            print(f"  ✗ JSON parsing error: {e}")
            print(f"  Response was: {response_text[:200]}...")
            return None
        except Exception as e:
            print(f"  ✗ Gemini API error: {e}")
            return None
    
    def build_final_output(self, extracted: Dict, ocr_text: str) -> Dict:
        """Build final output with validation checks"""
        
        # Extract fields
        po_number = extracted.get('PONumber')
        rdd = extracted.get('RDD')
        shipping_address = extracted.get('ShippingAddress')
        billing_address = extracted.get('BillingAddress')
        material_ids = extracted.get('MaterialIDList', [])
        line_item_count = extracted.get('LineItemCount', 0)
        
        # Validation checks
        material_count = len(material_ids)
        count_check = material_count > 0
        line_item_match = (line_item_count == material_count) if material_count > 0 and line_item_count > 0 else False
        
        po_validation = {
            'Length>5': len(po_number) > 5 if po_number else False,
            'OnlyNumeric': po_number.isdigit() if po_number else False
        }
        
        # Check mandatory fields
        mandatory_fields = [po_number, rdd, shipping_address]
        all_mandatory = all(field is not None and field != "" for field in mandatory_fields)
        
        # Build output structure
        result = {
            "Invoice_Header_Fields": {
                "FileName": extracted.get('FileName'),
                "SourceOrderID": extracted.get('SourceOrderID'),
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
            }
        }
        
        return result
    
    def process_single_file(self, ocr_file_path: Path) -> Optional[Dict]:
        """Process a single OCR file"""
        
        try:
            # Load OCR data
            with open(ocr_file_path, 'r', encoding='utf-8') as f:
                ocr_data = json.load(f)
            
            # Extract text
            ocr_text = self.extract_text_from_ocr(ocr_data)
            if not ocr_text:
                print(f"  ✗ No text extracted from OCR")
                return None
            
            # Extract with Gemini
            extracted = self.extract_with_gemini(ocr_text, ocr_file_path.name)
            if not extracted:
                return None
            
            # Build final output
            result = self.build_final_output(extracted, ocr_text)
            
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
        print()
        
        stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'complete_extractions': 0,
            'errors': []
        }
        
        for idx, json_file in enumerate(json_files, 1):
            print(f"Processing [{idx}/{len(json_files)}]: {json_file.name}", end=' ')
            
            try:
                result = self.process_single_file(json_file)
                
                if result:
                    output_filename = f"{json_file.stem}_extracted.json"
                    output_path = self.output_dir / output_filename
                    
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    
                    stats['successful'] += 1
                    
                    # Track complete extractions
                    if result['Validation_and_Quality_Checks']['All Mandatory Fields extracted']:
                        stats['complete_extractions'] += 1
                    
                    # Quick summary
                    po = result['Invoice_Header_Fields']['PONumber']
                    mat_count = result['Line_Item_Fields']['MaterialIDCount']
                    line_count = result['Line_Item_Fields']['LineItemCount']
                    complete = result['Validation_and_Quality_Checks']['All Mandatory Fields extracted']
                    print(f"✓ PO: {po or 'None'}, Materials: {mat_count}, Lines: {line_count}, Complete: {complete}")
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
        print("GEMINI EXTRACTION SUMMARY")
        print("="*70)
        print(f"Total files processed: {stats['total']}")
        print(f"Successful extractions: {stats['successful']}")
        print(f"Complete extractions (all mandatory fields): {stats['complete_extractions']}")
        print(f"Failed extractions: {stats['failed']}")
        print(f"Success rate: {stats['successful']/stats['total']*100:.1f}%")
        print(f"Completeness rate: {stats['complete_extractions']/stats['total']*100:.1f}%")
        
        if stats['errors']:
            print(f"\nErrors: {len(stats['errors'])}")
            for error in stats['errors'][:10]:
                print(f"  - {error}")
        
        print("="*70)
        
        # Save summary
        summary_path = self.output_dir / "gemini_extraction_summary.txt"
        with open(summary_path, 'w') as f:
            f.write(f"Gemini Extraction Summary - {datetime.now()}\n")
            f.write(f"Total: {stats['total']}\n")
            f.write(f"Successful: {stats['successful']}\n")
            f.write(f"Complete: {stats['complete_extractions']}\n")
            f.write(f"Failed: {stats['failed']}\n")
            f.write(f"\nErrors:\n")
            for error in stats['errors']:
                f.write(f"  {error}\n")


def main():
    """Main execution"""
    
    # Get API key from environment variable
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("="*70)
        print("ERROR: GEMINI_API_KEY environment variable not set!")
        print("="*70)
        print("\nPlease set your Gemini API key:")
        print("  export GEMINI_API_KEY='your-api-key-here'")
        print("\nOr get an API key from:")
        print("  https://makersuite.google.com/app/apikey")
        print("="*70)
        exit(1)
    
    INPUT_DIR = "/Users/vasingh/Desktop/Backend/results_ocr-final"
    OUTPUT_DIR = "/Users/vasingh/Desktop/Backend/extracted_invoice_fields_gemini"
    
    print("="*70)
    print("GEMINI-BASED Invoice Field Extraction System")
    print("="*70)
    print(f"Input: {INPUT_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print("\nUsing Google Gemini AI for intelligent extraction")
    print("Features:")
    print("  ✓ LLM-based extraction (handles complex layouts)")
    print("  ✓ Validation against OCR to prevent hallucination")
    print("  ✓ Complete address extraction")
    print("  ✓ Accurate material ID and line item counting")
    print("  ✓ Vendor number extraction")
    print()
    
    extractor = GeminiInvoiceExtractor(api_key, INPUT_DIR, OUTPUT_DIR)
    stats = extractor.process_all_files()
    extractor.generate_summary_report(stats)
    
    print(f"\n✓ Extraction complete! Output saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

