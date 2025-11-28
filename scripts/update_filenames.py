#!/usr/bin/env python3
"""
Update FileName field in extracted JSONs with full names from complete_pdf_mapping.json
"""

import json
import re
from pathlib import Path

def extract_pdf_number(filename: str) -> str:
    """Extract the PDF number from OCR filename like '20251112T022033_1.pdf.json'"""
    match = re.search(r'_(\d+)\.pdf', filename)
    if match:
        return match.group(1)
    return None

def update_filenames():
    """Update all extracted JSON files with full PDF names"""
    
    # Load the PDF mapping
    mapping_file = Path('/Users/vasingh/Desktop/Backend/complete_pdf_mapping.json')
    with open(mapping_file, 'r') as f:
        pdf_mapping = json.load(f)
    
    # Path to extracted files
    extracted_dir = Path('/Users/vasingh/Desktop/Backend/extracted_invoice_fields_mapped')
    
    updated_count = 0
    not_found_count = 0
    errors = []
    
    print("Updating FileName fields with full PDF names...")
    print("="*70)
    
    # Process each extracted JSON file
    for json_file in sorted(extracted_dir.glob('*_extracted.json')):
        try:
            # Extract the PDF number from filename
            pdf_number = extract_pdf_number(json_file.name)
            
            if not pdf_number:
                print(f"Could not extract PDF number from: {json_file.name}")
                errors.append(f"No PDF number: {json_file.name}")
                continue
            
            # Look up the full PDF name from mapping
            if pdf_number not in pdf_mapping:
                print(f"PDF #{pdf_number} not found in mapping")
                not_found_count += 1
                continue
            
            full_pdf_name = pdf_mapping[pdf_number]
            
            # Load the extracted JSON
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Update the FileName
            old_filename = data['Invoice_Header_Fields']['FileName']
            data['Invoice_Header_Fields']['FileName'] = full_pdf_name
            
            # Save back
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            updated_count += 1
            print(f"[{updated_count}] PDF #{pdf_number}: Updated")
            print(f"    From: {old_filename}")
            print(f"    To:   {full_pdf_name[:80]}{'...' if len(full_pdf_name) > 80 else ''}")
            
        except Exception as e:
            error_msg = f"{json_file.name}: {str(e)}"
            errors.append(error_msg)
            print(f"✗ Error processing {json_file.name}: {e}")
    
    # Summary
    print("\n" + "="*70)
    print("UPDATE SUMMARY")
    print("="*70)
    print(f"Total files processed: {updated_count + not_found_count + len(errors)}")
    print(f"Successfully updated: {updated_count}")
    print(f"Not found in mapping: {not_found_count}")
    print(f"Errors: {len(errors)}")
    
    if errors:
        print(f"\nErrors encountered:")
        for error in errors[:10]:
            print(f"  - {error}")
    
    print("="*70)
    print(f"\n✓ Update complete!")

if __name__ == "__main__":
    update_filenames()

