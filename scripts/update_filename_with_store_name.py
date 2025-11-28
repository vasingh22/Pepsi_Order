#!/usr/bin/env python3
"""
Update FileName field in extracted JSONs with store_name from normalized_samples_gemini files
"""

import json
import re
from pathlib import Path

def extract_pdf_number(filename: str) -> str:
    """Extract the PDF number from filename like '20251112T022033_1.pdf.json'"""
    match = re.search(r'_(\d+)\.pdf', filename)
    if match:
        return match.group(1)
    return None

def find_gemini_file(pdf_number: str, gemini_dir: Path) -> Path:
    """Find the corresponding gemini file for a given PDF number"""
    # Look for files that contain _{pdf_number}.pdf.gemini.json
    pattern = f"*_{pdf_number}.pdf.gemini.json"
    matches = list(gemini_dir.glob(pattern))
    
    if matches:
        return matches[0]
    return None

def update_filenames_with_store_names():
    """Update all extracted JSON files with store_name from gemini files"""
    
    # Paths
    extracted_dir = Path('/Users/vasingh/Desktop/Backend/extracted_invoice_fields_mapped')
    gemini_dir = Path('/Users/vasingh/Desktop/Backend/normalized_samples_gemini')
    
    updated_count = 0
    null_store_names = 0
    not_found_count = 0
    errors = []
    
    print("Updating FileName fields with store_name from normalized_samples_gemini...")
    print("="*70)
    
    # Process each extracted JSON file
    for json_file in sorted(extracted_dir.glob('*_extracted.json')):
        try:
            # Extract the PDF number
            pdf_number = extract_pdf_number(json_file.name)
            
            if not pdf_number:
                print(f"Could not extract PDF number from: {json_file.name}")
                errors.append(f"No PDF number: {json_file.name}")
                continue
            
            # Find corresponding gemini file
            gemini_file = find_gemini_file(pdf_number, gemini_dir)
            
            if not gemini_file:
                print(f"[{pdf_number}] No gemini file found")
                not_found_count += 1
                continue
            
            # Load gemini data to get store_name
            with open(gemini_file, 'r', encoding='utf-8') as f:
                gemini_data = json.load(f)
            
            store_name = gemini_data.get('store_name')
            
            # Load the extracted JSON
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Get the old filename for comparison
            old_filename = data['Invoice_Header_Fields']['FileName']
            
            # Update the FileName with store_name (or keep old if null)
            if store_name:
                data['Invoice_Header_Fields']['FileName'] = store_name
                
                # Save back
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                updated_count += 1
                print(f"[{updated_count}] PDF #{pdf_number}: Updated")
                print(f"    From: {old_filename[:60]}...")
                print(f"    To:   {store_name}")
            else:
                null_store_names += 1
                print(f"[Skip] PDF #{pdf_number}: store_name is null (kept original)")
            
        except Exception as e:
            error_msg = f"{json_file.name}: {str(e)}"
            errors.append(error_msg)
            print(f"✗ Error processing {json_file.name}: {e}")
    
    # Summary
    print("\n" + "="*70)
    print("UPDATE SUMMARY")
    print("="*70)
    print(f"Total files processed: {updated_count + null_store_names + not_found_count + len(errors)}")
    print(f"Successfully updated: {updated_count}")
    print(f"Null store_names (skipped): {null_store_names}")
    print(f"No gemini file found: {not_found_count}")
    print(f"Errors: {len(errors)}")
    
    if errors:
        print(f"\nErrors encountered:")
        for error in errors[:10]:
            print(f"  - {error}")
    
    if null_store_names > 0:
        print(f"\nNote: {null_store_names} files had null store_name and kept their original filenames")
    
    print("="*70)
    print(f"\n✓ Update complete!")

if __name__ == "__main__":
    update_filenames_with_store_names()

