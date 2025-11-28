#!/usr/bin/env python3
"""
Comprehensive Invoice Field Extraction Script
Processes all 200 OCR JSON files and extracts structured fields
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

class InvoiceFieldExtractor:
    """Extract and validate invoice fields from OCR JSON files"""
    
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
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
    
    def extract_po_number(self, text: str) -> Optional[str]:
        """Extract Purchase Order number"""
        patterns = [
            r'PO[:\s#]*([A-Z0-9\-]+)',
            r'P\.?O\.?[:\s#]*([A-Z0-9\-]+)',
            r'PURCHASE\s+ORDER[:\s#]*([A-Z0-9\-]+)',
            r'CUSTOMER\s+PO[:\s#]*([A-Z0-9\-]+)',
            r'ORDER\s+NUMBER[:\s#]*([0-9]+)',
            r'PO:\s*([A-Z0-9\-]+)',
            r'(?:^|\n)([A-Z]\d{5})(?:\s|$)',  # Pattern like B34200
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                po = match.group(1).strip()
                if len(po) >= 3:  # Minimum PO length
                    return po
        return None
    
    def extract_order_id(self, text: str) -> Optional[str]:
        """Extract Source Order ID"""
        patterns = [
            r'ORDER\s+NUMBER[:\s]*([0-9]+)',
            r'ORDER[:\s#]*([0-9]{8,})',
            r'CUST#[:\s]*([0-9]+)',
            r'CUSTOMER\s+NUMBER[:\s]*([0-9]+)',
            r'ORDER\s+ID[:\s]*([A-Z0-9]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                order_id = match.group(1).strip()
                if len(order_id) >= 5:
                    return order_id
        return None
    
    def extract_rdd(self, text: str) -> Optional[str]:
        """Extract Requested Delivery Date"""
        patterns = [
            r'DELIVERY\s+DATE[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})',
            r'ARRIVAL\s+DATE[:\s]*\|?([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})',
            r'RDD[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})',
            r'REQUESTED\s+DELIVERY[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})',
            r'DEL(?:IVERY)?\s+(?:DATE)?[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                return date_str
        return None
    
    def extract_shipping_address(self, text: str) -> Optional[str]:
        """Extract Shipping Address"""
        patterns = [
            r'SHIP\s+TO[:\s]*\n?([^\n]+(?:\n[^\n]+){0,3})',
            r'SHIP\s+TO[:\s]*([A-Z0-9\s,\.\-]+(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\s+\d{5})',
            r'DELIVER\s+TO[:\s]*\n?([^\n]+(?:\n[^\n]+){0,3})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                address = match.group(1).strip()
                # Clean up and limit to reasonable length
                address_lines = [line.strip() for line in address.split('\n') if line.strip()]
                address = ', '.join(address_lines[:4])  # Max 4 lines
                if len(address) > 15:  # Must be substantial
                    return address
        return None
    
    def extract_billing_address(self, text: str) -> Optional[str]:
        """Extract Billing Address"""
        patterns = [
            r'SOLD\s+TO[:\s]*\n?([^\n]+(?:\n[^\n]+){0,3})',
            r'BILL\s+TO[:\s]*\n?([^\n]+(?:\n[^\n]+){0,3})',
            r'BILLING\s+ADDRESS[:\s]*\n?([^\n]+(?:\n[^\n]+){0,3})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                address = match.group(1).strip()
                address_lines = [line.strip() for line in address.split('\n') if line.strip()]
                address = ', '.join(address_lines[:4])
                if len(address) > 15:
                    return address
        return None
    
    def extract_material_ids(self, text: str) -> List[str]:
        """Extract Material IDs/SKUs from invoice"""
        material_ids = []
        
        # Pattern for GTIN codes (common in the invoices)
        gtin_pattern = r'(?:^|\s)([0-9]{12,14})(?:\s|$)'
        gtin_matches = re.findall(gtin_pattern, text, re.MULTILINE)
        
        # Pattern for item codes like V17741, 70766, etc.
        item_code_pattern = r'(?:SUPPLIER CODE|AVI CODE|ITEM|CODE)[:\s]*([A-Z0-9]+)'
        item_matches = re.findall(item_code_pattern, text, re.IGNORECASE)
        
        # Pattern for product codes in tables
        table_pattern = r'(?:^|\n)([A-Z]?\d{5,})(?:\s+[A-Z])'
        table_matches = re.findall(table_pattern, text, re.MULTILINE)
        
        # Combine all matches and deduplicate
        all_ids = gtin_matches + item_matches + table_matches
        seen = set()
        for id_val in all_ids:
            if id_val and len(id_val) >= 4 and id_val not in seen:
                material_ids.append(id_val)
                seen.add(id_val)
        
        return material_ids
    
    def count_line_items(self, text: str) -> int:
        """Count the number of line items in the invoice"""
        # Look for table-like structures with items
        line_count = 0
        
        # Pattern 1: Lines starting with item numbers
        pattern1 = r'(?:^|\n)(?:[0-9]{5,})\s+[0-9]{12,14}'
        matches1 = re.findall(pattern1, text, re.MULTILINE)
        line_count = max(line_count, len(matches1))
        
        # Pattern 2: Lines with QTY and CS/EA patterns
        pattern2 = r'\d+\s+(?:CS|EA|CASE|EACH)\s+[\d\.]+'
        matches2 = re.findall(pattern2, text, re.IGNORECASE)
        line_count = max(line_count, len(matches2))
        
        # Pattern 3: Count L/N entries
        pattern3 = r'(?:^|\n)L/N\s+\d+'
        matches3 = re.findall(pattern3, text, re.MULTILINE)
        line_count = max(line_count, len(matches3))
        
        return line_count
    
    def validate_po_number(self, po: Optional[str]) -> Dict[str, bool]:
        """Validate PO number"""
        validation = {
            'Length>5': False,
            'OnlyNumeric': False
        }
        
        if po:
            validation['Length>5'] = len(po) > 5
            validation['OnlyNumeric'] = po.isdigit()
        
        return validation
    
    def extract_all_fields(self, ocr_file_path: Path) -> Dict[str, Any]:
        """Extract all fields from a single OCR file"""
        
        # Load OCR data
        try:
            with open(ocr_file_path, 'r', encoding='utf-8') as f:
                ocr_data = json.load(f)
        except Exception as e:
            print(f"Error reading {ocr_file_path}: {e}")
            return None
        
        # Extract filename
        filename = ocr_data.get('filename', ocr_file_path.stem)
        
        # Extract text
        text = self.extract_text_from_ocr(ocr_data)
        
        if not text:
            print(f"No text extracted from {filename}")
            return None
        
        # Extract all fields
        po_number = self.extract_po_number(text)
        source_order_id = self.extract_order_id(text)
        rdd = self.extract_rdd(text)
        shipping_address = self.extract_shipping_address(text)
        billing_address = self.extract_billing_address(text)
        material_ids = self.extract_material_ids(text)
        line_item_count = self.count_line_items(text)
        
        # Validations
        po_validation = self.validate_po_number(po_number)
        material_count = len(material_ids)
        count_check = material_count > 0
        line_item_match = line_item_count == material_count if material_count > 0 else False
        
        # Check if all mandatory fields are extracted
        mandatory_fields = [po_number, rdd, shipping_address]
        all_mandatory = all(field is not None for field in mandatory_fields)
        
        # Build output structure
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
            }
        }
        
        return result
    
    def process_all_files(self) -> Dict[str, Any]:
        """Process all OCR files in the input directory"""
        
        # Get all JSON files sorted by number
        json_files = sorted(
            self.input_dir.glob('*.json'),
            key=lambda x: self._extract_number_from_filename(x.name)
        )
        
        print(f"Found {len(json_files)} JSON files to process")
        
        stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        for idx, json_file in enumerate(json_files, 1):
            print(f"Processing [{idx}/{len(json_files)}]: {json_file.name}")
            
            try:
                result = self.extract_all_fields(json_file)
                
                if result:
                    # Create output filename
                    output_filename = f"{json_file.stem}_extracted.json"
                    output_path = self.output_dir / output_filename
                    
                    # Write result
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    
                    stats['successful'] += 1
                    
                    # Print summary
                    po = result['Invoice_Header_Fields']['PONumber']
                    mat_count = result['Line_Item_Fields']['MaterialIDCount']
                    all_fields = result['Validation_and_Quality_Checks']['All Mandatory Fields extracted']
                    print(f"  ✓ PO: {po}, Materials: {mat_count}, Complete: {all_fields}")
                else:
                    stats['failed'] += 1
                    stats['errors'].append(f"{json_file.name}: No data extracted")
                    print(f"  ✗ Failed to extract data")
                
                stats['total'] += 1
                
            except Exception as e:
                stats['failed'] += 1
                stats['errors'].append(f"{json_file.name}: {str(e)}")
                print(f"  ✗ Error: {e}")
        
        return stats
    
    def _extract_number_from_filename(self, filename: str) -> int:
        """Extract number from filename for sorting"""
        match = re.search(r'_(\d+)\.pdf', filename)
        if match:
            return int(match.group(1))
        return 0
    
    def generate_summary_report(self, stats: Dict[str, Any]):
        """Generate a summary report of the extraction"""
        
        print("\n" + "="*70)
        print("EXTRACTION SUMMARY")
        print("="*70)
        print(f"Total files processed: {stats['total']}")
        print(f"Successful extractions: {stats['successful']}")
        print(f"Failed extractions: {stats['failed']}")
        print(f"Success rate: {stats['successful']/stats['total']*100:.1f}%")
        
        if stats['errors']:
            print(f"\nErrors encountered: {len(stats['errors'])}")
            for error in stats['errors'][:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(stats['errors']) > 10:
                print(f"  ... and {len(stats['errors']) - 10} more")
        
        print("="*70)
        
        # Write summary to file
        summary_path = self.output_dir / "extraction_summary.txt"
        with open(summary_path, 'w') as f:
            f.write(f"Extraction Summary - {datetime.now()}\n")
            f.write(f"Total: {stats['total']}\n")
            f.write(f"Successful: {stats['successful']}\n")
            f.write(f"Failed: {stats['failed']}\n")
            f.write(f"\nErrors:\n")
            for error in stats['errors']:
                f.write(f"  {error}\n")


def main():
    """Main execution function"""
    
    # Configuration
    INPUT_DIR = "/Users/vasingh/Desktop/Backend/results_ocr-final"
    OUTPUT_DIR = "/Users/vasingh/Desktop/Backend/extracted_invoice_fields_mapped"
    
    print("="*70)
    print("Invoice Field Extraction System")
    print("="*70)
    print(f"Input directory: {INPUT_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    
    # Create extractor
    extractor = InvoiceFieldExtractor(INPUT_DIR, OUTPUT_DIR)
    
    # Process all files
    stats = extractor.process_all_files()
    
    # Generate summary
    extractor.generate_summary_report(stats)
    
    print(f"\n✓ Extraction complete! Output saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

