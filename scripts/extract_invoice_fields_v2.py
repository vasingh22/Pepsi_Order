#!/usr/bin/env python3
"""
IMPROVED Invoice Field Extraction Script - Version 2.0
Processes all 200 OCR JSON files with enhanced pattern matching
Fixes issues with false PO matches and improves accuracy
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

class ImprovedInvoiceFieldExtractor:
    """Enhanced extractor with better pattern recognition"""
    
    # Blacklist of common words that shouldn't be PO numbers
    PO_BLACKLIST = {
        'nsible', 'responsible', 'INTMENT', 'appointment', 'Number', 'number',
        'BOX', 'box', 'PCORN', 'pcorners', 'pcorner', 'CASES', 'cases',
        'lis', 'list', 'ODER', 'order', 'Issued', 'issued', 'Bill', 'bill',
        'Date', 'date', 'Total', 'total', 'Page', 'page', 'Item', 'item'
    }
    
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
    
    def clean_po_number(self, po: str) -> Optional[str]:
        """Clean and validate PO number"""
        if not po:
            return None
        
        po = po.strip()
        
        # Check blacklist
        if po in self.PO_BLACKLIST or po.lower() in {x.lower() for x in self.PO_BLACKLIST}:
            return None
        
        # Must be at least 3 characters
        if len(po) < 3:
            return None
        
        # If it's purely alphabetic and short, likely not a PO
        if po.isalpha() and len(po) < 5:
            return None
        
        return po
    
    def extract_po_number(self, text: str) -> Optional[str]:
        """Extract Purchase Order number with improved patterns"""
        
        # Priority 1: Explicit "PURCHASE ORDER NO" or "PURCHASE ORDER #" followed by number
        priority_patterns = [
            r'PURCHASE\s+ORDER\s+(?:NO|NUMBER|#)[:\s]*\n?\s*([A-Z0-9\-]{5,})',
            r'PURCHASE\s+ORDER[:\s]*\n?\s*([A-Z0-9\-]{5,})',
            r'P\.?O\.?\s+(?:NO|NUMBER|#)[:\s]*([A-Z0-9\-]{5,})',
        ]
        
        for pattern in priority_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                po = self.clean_po_number(match.group(1))
                if po:
                    return po
        
        # Priority 2: "PO:" or "PO #" patterns (more specific)
        po_patterns = [
            r'PO\s*#[:\s]*([A-Z0-9\-]{5,})',
            r'PO:[:\s]*([A-Z0-9\-]{5,})',
            r'P\.O\.:[:\s]*([A-Z0-9\-]{5,})',
            r'CUSTOMER\s+PO[:\s]*([A-Z0-9\-]{5,})',
        ]
        
        for pattern in po_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                po = self.clean_po_number(match.group(1))
                if po:
                    return po
        
        # Priority 3: Standalone alphanumeric codes (like B34200)
        # Look for pattern at start of line: Letter followed by 5+ digits
        standalone_pattern = r'(?:^|\n)([A-Z]\d{5,})(?:\s|$|\n)'
        match = re.search(standalone_pattern, text, re.MULTILINE)
        if match:
            po = self.clean_po_number(match.group(1))
            if po:
                return po
        
        # Priority 4: ORDER NUMBER (as fallback)
        order_pattern = r'ORDER\s+NUMBER[:\s]*([A-Z0-9]{6,})'
        match = re.search(order_pattern, text, re.IGNORECASE)
        if match:
            po = self.clean_po_number(match.group(1))
            if po:
                return po
        
        return None
    
    def extract_order_id(self, text: str) -> Optional[str]:
        """Extract Source Order ID"""
        patterns = [
            r'ORDER\s+NUMBER[:\s]*([0-9]{8,})',
            r'ORDER[:\s#]*([0-9]{10})',
            r'CUST#[:\s]*([0-9]{7,})',
            r'CUSTOMER\s+NUMBER[:\s]*([0-9]{7,})',
            r'VENDOR\s*#[:\s]*([0-9]{7,})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                order_id = match.group(1).strip()
                if len(order_id) >= 7:
                    return order_id
        return None
    
    def extract_rdd(self, text: str) -> Optional[str]:
        """Extract Requested Delivery Date with improved patterns"""
        patterns = [
            # Specific labels
            r'DELIVERY\s+DATE[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})',
            r'ARRIVAL\s+DATE[:\s]*\|?\s*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})',
            r'RDD[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})',
            r'REQUESTED\s+DELIVERY[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})',
            r'DEL\s+DATE[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})',
            r'SHIP\s+DATE[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})',
            # Look for dates after "DEL" or "DELIVERY"
            r'(?:DEL|DELIVERY).*?([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                date_str = match.group(1).strip()
                # Validate it's a reasonable date format
                if re.match(r'\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}', date_str):
                    return date_str
        return None
    
    def clean_address(self, address: str) -> str:
        """Clean extracted address by removing metadata"""
        if not address:
            return address
        
        # Remove common metadata strings
        metadata_terms = [
            'ORDER NUMBER:', 'DELIVERY DATE:', 'CONTACT:', 'BUYER:',
            'SHIP TO:', 'SOLD TO:', 'BILL TO:', 'PHONE:', 'FAX:',
            'ORDER DATE:', 'CUST#:', 'PO:', 'VENDOR #:'
        ]
        
        lines = address.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip lines that are just metadata labels
            if any(term in line.upper() for term in metadata_terms):
                # But keep the line if it also has substantive address info
                if re.search(r'\d{5}', line):  # Has a zip code
                    line = re.sub(r'(?:' + '|'.join(metadata_terms) + r')', '', line, flags=re.IGNORECASE)
                    line = line.strip(', ')
                else:
                    continue
            if line and len(line) > 2:
                cleaned_lines.append(line)
        
        return ', '.join(cleaned_lines[:4])  # Max 4 lines
    
    def extract_shipping_address(self, text: str) -> Optional[str]:
        """Extract Shipping Address with better cleaning"""
        patterns = [
            # Look for SHIP TO with address components
            r'SHIP\s+TO[:\s]*\n([^\n]+\n[^\n]+\n[^\n]*(?:[A-Z]{2})\s+\d{5}[^\n]*)',
            r'SHIP\s+TO[:\s]*([^0-9\n]*\d+[^\n]+\n[^\n]+[A-Z]{2}\s+\d{5})',
            r'DELIVER\s+TO[:\s]*\n([^\n]+\n[^\n]+[A-Z]{2}\s+\d{5})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                address = self.clean_address(match.group(1))
                if len(address) > 15:
                    return address
        
        # Fallback: Look for any address-like pattern with zip code
        address_pattern = r'(\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s*(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Blvd|Boulevard|Way|Lane|Ln)?[,\s]+[A-Z][a-z]+[,\s]+[A-Z]{2}\s+\d{5}(?:-\d{4})?)'
        match = re.search(address_pattern, text)
        if match:
            return match.group(1).strip()
        
        return None
    
    def extract_billing_address(self, text: str) -> Optional[str]:
        """Extract Billing Address"""
        patterns = [
            r'SOLD\s+TO[:\s]*\n([^\n]+\n[^\n]+\n[^\n]*[A-Z]{2}\s+\d{5}[^\n]*)',
            r'BILL\s+TO[:\s]*\n([^\n]+\n[^\n]+[A-Z]{2}\s+\d{5})',
            r'BILLING\s+ADDRESS[:\s]*\n([^\n]+\n[^\n]+[A-Z]{2}\s+\d{5})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                address = self.clean_address(match.group(1))
                if len(address) > 15:
                    return address
        return None
    
    def extract_material_ids(self, text: str) -> List[str]:
        """Extract Material IDs/SKUs - improved to filter out non-product codes"""
        material_ids = []
        
        # Pattern 1: GTIN codes (must start with specific prefixes for Frito-Lay)
        gtin_pattern = r'(?:^|\s)(00028[0-9]{9})(?:\s|$|\n)'
        gtin_matches = re.findall(gtin_pattern, text, re.MULTILINE)
        
        # Pattern 2: Item codes in specific contexts (after CODE, ITEM #, etc.)
        item_code_pattern = r'(?:SUPPLIER CODE|AVI CODE|ITEM #|VENDOR STYLE #|D\'s ITEM #)[:\s]*([A-Z0-9]{4,8})'
        item_matches = re.findall(item_code_pattern, text, re.IGNORECASE)
        
        # Pattern 3: 5-digit item codes at start of line (but not PO or Order numbers)
        line_start_pattern = r'(?:^|\n)([0-9]{5})(?:\s+[A-Z])'
        line_matches = re.findall(line_start_pattern, text, re.MULTILINE)
        
        # Combine and filter
        all_ids = gtin_matches + item_matches + line_matches
        
        # Exclusion list: common non-product numbers
        exclude_patterns = [
            r'^10\d{8}$',  # Order numbers starting with 10
            r'^20\d{8}$',  # Customer numbers starting with 20
            r'^975$',  # Short numbers
            r'^GTIN$', r'^DESCRIPTION$', r'^PRODUCT$', r'^ITEM$',  # Labels
            r'^ORDER$', r'^UNIT$', r'^COMMENTS$', r'^CODE$',
            r'^[0-9]{4}$',  # Too short (4 digits)
        ]
        
        seen = set()
        for id_val in all_ids:
            # Skip if matches exclusion patterns
            if any(re.match(pat, id_val, re.IGNORECASE) for pat in exclude_patterns):
                continue
            
            # Skip if it's a known non-product term
            if id_val.upper() in ['DESCRIPTION', 'PRODUCT', 'ITEM', 'CODE', 'GTIN', 'UNIT', 'ORDER']:
                continue
            
            # Must be at least 5 characters for GTIN or SKU
            if len(id_val) >= 5 and id_val not in seen:
                material_ids.append(id_val)
                seen.add(id_val)
        
        return material_ids
    
    def count_line_items(self, text: str) -> int:
        """Count line items with improved accuracy"""
        line_count = 0
        
        # Method 1: Count lines with quantity + unit + price patterns
        # Look for patterns like: "20  CS  41.22"
        pattern1 = r'\b(\d{1,4})\s+(CS|EA|CASE|EACH|BX|BOX|PC|PIECES)\s+[\d,]+\.?\d*'
        matches1 = re.findall(pattern1, text, re.IGNORECASE)
        line_count = max(line_count, len(matches1))
        
        # Method 2: Count GTIN codes (each product has one)
        gtin_pattern = r'00028[0-9]{9}'
        matches2 = re.findall(gtin_pattern, text)
        line_count = max(line_count, len(matches2))
        
        # Method 3: Count item rows with VENDOR STYLE or similar
        pattern3 = r'(?:VENDOR STYLE #|ITEM #|SKU)[:\s]*[A-Z0-9]+'
        matches3 = re.findall(pattern3, text, re.IGNORECASE)
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
        
        try:
            with open(ocr_file_path, 'r', encoding='utf-8') as f:
                ocr_data = json.load(f)
        except Exception as e:
            print(f"Error reading {ocr_file_path}: {e}")
            return None
        
        filename = ocr_data.get('filename', ocr_file_path.stem)
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
        line_item_match = (line_item_count == material_count) if material_count > 0 and line_item_count > 0 else False
        
        # Check mandatory fields
        mandatory_fields = [po_number, rdd, shipping_address]
        all_mandatory = all(field is not None for field in mandatory_fields)
        
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
            }
        }
        
        return result
    
    def process_all_files(self) -> Dict[str, Any]:
        """Process all OCR files"""
        
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
            print(f"Processing [{idx}/{len(json_files)}]: {json_file.name}", end=' ')
            
            try:
                result = self.extract_all_fields(json_file)
                
                if result:
                    output_filename = f"{json_file.stem}_extracted.json"
                    output_path = self.output_dir / output_filename
                    
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    
                    stats['successful'] += 1
                    
                    # Quick summary
                    po = result['Invoice_Header_Fields']['PONumber']
                    mat_count = result['Line_Item_Fields']['MaterialIDCount']
                    complete = result['Validation_and_Quality_Checks']['All Mandatory Fields extracted']
                    print(f"✓ PO: {po or 'None'}, Materials: {mat_count}, Complete: {complete}")
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
        print("IMPROVED EXTRACTION SUMMARY - V2.0")
        print("="*70)
        print(f"Total files processed: {stats['total']}")
        print(f"Successful extractions: {stats['successful']}")
        print(f"Failed extractions: {stats['failed']}")
        print(f"Success rate: {stats['successful']/stats['total']*100:.1f}%")
        
        if stats['errors']:
            print(f"\nErrors: {len(stats['errors'])}")
            for error in stats['errors'][:10]:
                print(f"  - {error}")
        
        print("="*70)
        
        # Save summary
        summary_path = self.output_dir / "extraction_summary_v2.txt"
        with open(summary_path, 'w') as f:
            f.write(f"Extraction Summary V2.0 - {datetime.now()}\n")
            f.write(f"Total: {stats['total']}\n")
            f.write(f"Successful: {stats['successful']}\n")
            f.write(f"Failed: {stats['failed']}\n")
            f.write(f"\nImprovements:\n")
            f.write("- Fixed PO number false matches (nsible, INTMENT, etc.)\n")
            f.write("- Improved material ID filtering\n")
            f.write("- Better address cleaning\n")
            f.write("- Enhanced date extraction\n")
            f.write(f"\nErrors:\n")
            for error in stats['errors']:
                f.write(f"  {error}\n")


def main():
    """Main execution"""
    
    INPUT_DIR = "/Users/vasingh/Desktop/Backend/results_ocr-final"
    OUTPUT_DIR = "/Users/vasingh/Desktop/Backend/extracted_invoice_fields_mapped"
    
    print("="*70)
    print("IMPROVED Invoice Field Extraction System - V2.0")
    print("="*70)
    print(f"Input: {INPUT_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print("\nImprovements:")
    print("  ✓ Fixed false PO matches (nsible, INTMENT, etc.)")
    print("  ✓ Better material ID filtering")
    print("  ✓ Improved address cleaning")
    print("  ✓ Enhanced RDD extraction")
    print()
    
    extractor = ImprovedInvoiceFieldExtractor(INPUT_DIR, OUTPUT_DIR)
    stats = extractor.process_all_files()
    extractor.generate_summary_report(stats)
    
    print(f"\n✓ Extraction complete! Output saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

