#!/usr/bin/env python3
"""
CRITICAL: Cross-verify PO numbers from extracted files against original OCR data
This script checks EVERY file to ensure PO numbers are authentic and correctly extracted
"""

import json
import re
from pathlib import Path
from typing import Dict, Optional, List

class PONumberVerifier:
    """Verify PO numbers against original OCR text"""
    
    def __init__(self):
        self.extracted_dir = Path('/Users/vasingh/Desktop/Backend/extracted_invoice_fields_mapped')
        self.ocr_dir = Path('/Users/vasingh/Desktop/Backend/results_ocr-final')
        self.issues = []
        self.verified = []
        
    def get_ocr_file(self, extracted_filename: str) -> Optional[Path]:
        """Find corresponding OCR file"""
        # Extract the timestamp and number from extracted filename
        # e.g., "20251112T022033_1.pdf_extracted.json" -> "20251112T022033_1.pdf.json"
        match = re.search(r'(20\d{6}T\d{6}_\d+)\.pdf', extracted_filename)
        if match:
            base = match.group(1)
            ocr_file = self.ocr_dir / f"{base}.pdf.json"
            if ocr_file.exists():
                return ocr_file
        return None
    
    def extract_text_from_ocr(self, ocr_file: Path) -> str:
        """Extract all text from OCR JSON"""
        try:
            with open(ocr_file, 'r', encoding='utf-8') as f:
                ocr_data = json.load(f)
            
            text_parts = []
            if 'pages' in ocr_data:
                for page in ocr_data['pages']:
                    if 'text' in page:
                        text_parts.append(page['text'])
            
            return '\n'.join(text_parts)
        except Exception as e:
            return ""
    
    def find_po_patterns_in_text(self, text: str) -> List[str]:
        """Find all possible PO number patterns in text"""
        patterns = [
            r'PURCHASE\s+ORDER\s+(?:NO|NUMBER|#)[:\s]*\n?\s*([A-Z0-9\-]{5,})',
            r'PO\s*#[:\s]*([A-Z0-9\-]{5,})',
            r'PO:[:\s]*([A-Z0-9\-]{5,})',
            r'P\.?O\.?[:\s#]*([A-Z0-9\-]{5,})',
            r'CUSTOMER\s+PO[:\s]*([A-Z0-9\-]{5,})',
            r'ORDER\s+NUMBER[:\s]*([0-9]{6,})',
            r'(?:^|\n)([A-Z]\d{5,})(?:\s|$|\n)',  # Standalone like B34200
        ]
        
        found = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            found.extend([m.strip() for m in matches if len(m.strip()) >= 5])
        
        return list(set(found))  # Remove duplicates
    
    def verify_po_number(self, extracted_po: Optional[str], ocr_text: str, filename: str) -> Dict:
        """Verify if extracted PO exists in OCR text"""
        result = {
            'filename': filename,
            'extracted_po': extracted_po,
            'status': 'UNKNOWN',
            'found_in_ocr': False,
            'possible_pos': [],
            'notes': ''
        }
        
        if not extracted_po:
            result['status'] = 'NO_PO_EXTRACTED'
            result['notes'] = 'No PO number was extracted'
            # Still find what POs exist in text
            result['possible_pos'] = self.find_po_patterns_in_text(ocr_text)
            return result
        
        # Find all possible PO patterns in OCR text
        possible_pos = self.find_po_patterns_in_text(ocr_text)
        result['possible_pos'] = possible_pos
        
        # Check if extracted PO exists in the text
        if extracted_po in ocr_text:
            result['found_in_ocr'] = True
            result['status'] = 'VERIFIED'
            result['notes'] = '✓ PO number found in original OCR text'
        elif extracted_po in possible_pos:
            result['found_in_ocr'] = True
            result['status'] = 'VERIFIED'
            result['notes'] = '✓ PO number matches pattern found in OCR'
        else:
            result['status'] = 'MISMATCH'
            result['notes'] = f'⚠ PO "{extracted_po}" NOT found in OCR text'
            if possible_pos:
                result['notes'] += f'. Found these POs instead: {", ".join(possible_pos[:5])}'
        
        return result
    
    def verify_all_files(self):
        """Verify PO numbers in all extracted files"""
        
        extracted_files = sorted(self.extracted_dir.glob('*_extracted.json'))
        
        print("="*80)
        print("CRITICAL PO NUMBER VERIFICATION")
        print("="*80)
        print(f"Total files to verify: {len(extracted_files)}")
        print()
        
        for idx, extracted_file in enumerate(extracted_files, 1):
            # Load extracted data
            try:
                with open(extracted_file, 'r', encoding='utf-8') as f:
                    extracted_data = json.load(f)
            except Exception as e:
                self.issues.append({
                    'filename': extracted_file.name,
                    'error': f"Could not read file: {e}"
                })
                continue
            
            extracted_po = extracted_data['Invoice_Header_Fields'].get('PONumber')
            
            # Find corresponding OCR file
            ocr_file = self.get_ocr_file(extracted_file.name)
            
            if not ocr_file:
                self.issues.append({
                    'filename': extracted_file.name,
                    'extracted_po': extracted_po,
                    'error': 'OCR file not found'
                })
                print(f"[{idx}] ✗ {extracted_file.name}: OCR file not found")
                continue
            
            # Get OCR text
            ocr_text = self.extract_text_from_ocr(ocr_file)
            
            if not ocr_text:
                self.issues.append({
                    'filename': extracted_file.name,
                    'extracted_po': extracted_po,
                    'error': 'Could not extract text from OCR'
                })
                print(f"[{idx}] ✗ {extracted_file.name}: No OCR text")
                continue
            
            # Verify PO number
            result = self.verify_po_number(extracted_po, ocr_text, extracted_file.name)
            
            if result['status'] == 'VERIFIED':
                self.verified.append(result)
                print(f"[{idx}] ✓ {extracted_file.name[:50]:50s} PO: {extracted_po}")
            elif result['status'] == 'NO_PO_EXTRACTED':
                self.issues.append(result)
                pos = result['possible_pos'][:3]
                pos_str = ', '.join(pos) if pos else 'None'
                print(f"[{idx}] ⚠ {extracted_file.name[:50]:50s} NO PO (Found: {pos_str})")
            else:  # MISMATCH
                self.issues.append(result)
                print(f"[{idx}] ✗ {extracted_file.name[:50]:50s} MISMATCH: {extracted_po}")
                print(f"      → {result['notes']}")
    
    def generate_report(self):
        """Generate detailed verification report"""
        
        print("\n" + "="*80)
        print("VERIFICATION SUMMARY")
        print("="*80)
        
        total = len(self.verified) + len(self.issues)
        verified_count = len(self.verified)
        issues_count = len(self.issues)
        
        print(f"Total Files: {total}")
        print(f"✓ Verified: {verified_count} ({verified_count/total*100:.1f}%)")
        print(f"✗ Issues: {issues_count} ({issues_count/total*100:.1f}%)")
        
        if issues_count > 0:
            print("\n" + "="*80)
            print("DETAILED ISSUES")
            print("="*80)
            
            # Group by status
            no_po = [i for i in self.issues if i.get('status') == 'NO_PO_EXTRACTED']
            mismatches = [i for i in self.issues if i.get('status') == 'MISMATCH']
            errors = [i for i in self.issues if 'error' in i]
            
            if no_po:
                print(f"\n1. NO PO EXTRACTED ({len(no_po)} files):")
                for issue in no_po[:20]:
                    pos = ', '.join(issue.get('possible_pos', [])[:3])
                    print(f"   - {issue['filename']}")
                    if pos:
                        print(f"     Found in OCR: {pos}")
                if len(no_po) > 20:
                    print(f"   ... and {len(no_po) - 20} more")
            
            if mismatches:
                print(f"\n2. PO MISMATCHES ({len(mismatches)} files):")
                for issue in mismatches[:20]:
                    print(f"   - {issue['filename']}")
                    print(f"     Extracted: {issue['extracted_po']}")
                    if issue.get('possible_pos'):
                        print(f"     Found in OCR: {', '.join(issue['possible_pos'][:5])}")
                if len(mismatches) > 20:
                    print(f"   ... and {len(mismatches) - 20} more")
            
            if errors:
                print(f"\n3. ERRORS ({len(errors)} files):")
                for issue in errors[:10]:
                    print(f"   - {issue['filename']}: {issue.get('error')}")
        else:
            print("\n✓ All PO numbers verified successfully!")
        
        print("\n" + "="*80)
        
        # Save detailed report
        report_path = self.extracted_dir / "po_verification_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'total': total,
                    'verified': verified_count,
                    'issues': issues_count
                },
                'verified': self.verified,
                'issues': self.issues
            }, f, indent=2, ensure_ascii=False)
        
        print(f"Detailed report saved to: {report_path}")
        print("="*80)

def main():
    verifier = PONumberVerifier()
    verifier.verify_all_files()
    verifier.generate_report()

if __name__ == "__main__":
    main()

