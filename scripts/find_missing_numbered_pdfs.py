#!/usr/bin/env python3
"""
Find which numbered PDFs (1-200) are missing from normalized_samples_gemini folder.
"""
import re
from pathlib import Path

def find_missing_numbers():
    """
    Find which numbers from 1-200 are missing in the normalized_samples_gemini folder.
    """
    
    gemini_dir = Path("normalized_samples_gemini")
    if not gemini_dir.exists():
        print(f"❌ Error: {gemini_dir} not found!")
        return []
    
    gemini_files = list(gemini_dir.glob("*.json"))
    
    # Extract numbers from filenames like: 20251111T185114_116.pdf.gemini.json
    processed_numbers = set()
    for gemini_path in gemini_files:
        # Extract the number before .pdf
        match = re.search(r'_(\d+)\.pdf\.gemini\.json$', gemini_path.name)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 200:
                processed_numbers.add(num)
    
    print(f"📊 Total files in normalized_samples_gemini: {len(gemini_files)}")
    print(f"✅ Unique numbered PDFs processed (1-200): {len(processed_numbers)}")
    print()
    
    # Find missing numbers from 1-200
    all_numbers = set(range(1, 201))
    missing_numbers = sorted(all_numbers - processed_numbers)
    
    print("="*70)
    print(f"❌ MISSING PDF NUMBERS: {len(missing_numbers)} total")
    print("="*70)
    
    if missing_numbers:
        # Group consecutive numbers for cleaner display
        groups = []
        current_group = [missing_numbers[0]]
        
        for num in missing_numbers[1:]:
            if num == current_group[-1] + 1:
                current_group.append(num)
            else:
                groups.append(current_group)
                current_group = [num]
        groups.append(current_group)
        
        # Display groups
        print()
        for group in groups:
            if len(group) > 2:
                print(f"  {group[0]:3d} - {group[-1]:3d}  ({len(group)} PDFs)")
            else:
                for num in group:
                    print(f"  {num:3d}")
        
        # Save to file
        output_file = "missing_pdf_numbers.txt"
        with open(output_file, 'w') as f:
            for num in missing_numbers:
                f.write(f"{num}\n")
        
        print()
        print(f"💾 Missing PDF numbers saved to: {output_file}")
        print("="*70)
        
        return missing_numbers
    else:
        print("✅ All PDFs numbered 1-200 have been processed!")
        print("="*70)
        return []

if __name__ == "__main__":
    print("🔍 Finding missing PDF numbers from 1-200...\n")
    missing = find_missing_numbers()
    
    if missing:
        print()
        print("📝 SUMMARY:")
        print("="*70)
        print(f"  Total in range 1-200: 200")
        print(f"  Processed: {200 - len(missing)}")
        print(f"  Missing: {len(missing)}")
        print("="*70)

