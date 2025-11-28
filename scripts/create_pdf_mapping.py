#!/usr/bin/env python3
"""
Create a numbered mapping (1-200) of all PDFs in PickSample200.
This recreates the mapping used by the Gemini processing.
"""
import json
from pathlib import Path

def create_pdf_mapping():
    """
    Create a numbered mapping of all PDFs in PickSample200 folder.
    Returns a dictionary: {number: pdf_filename}
    """
    
    pdf_dir = Path("backend/PickSample200")
    if not pdf_dir.exists():
        print(f"❌ Error: {pdf_dir} not found!")
        return {}
    
    # Get all PDF files (case-insensitive)
    pdf_files = sorted(list(pdf_dir.glob("*.pdf")) + list(pdf_dir.glob("*.PDF")))
    
    print(f"📁 Found {len(pdf_files)} PDF files in PickSample200")
    print()
    
    # Create mapping: number -> filename
    mapping = {}
    for i, pdf_path in enumerate(pdf_files, start=1):
        mapping[i] = pdf_path.name
    
    return mapping, pdf_files

def find_missing_pdf_files():
    """
    Identify which actual PDF files correspond to the missing numbers.
    """
    
    # Load missing numbers
    missing_file = Path("missing_pdf_numbers.txt")
    if not missing_file.exists():
        print(f"❌ Error: {missing_file} not found!")
        print("   Run 'python3 find_missing_numbered_pdfs.py' first.")
        return
    
    with open(missing_file, 'r') as f:
        missing_numbers = [int(line.strip()) for line in f if line.strip()]
    
    print(f"📊 Missing PDF numbers: {len(missing_numbers)}")
    
    # Create mapping
    mapping, all_pdfs = create_pdf_mapping()
    
    if not mapping:
        return
    
    # Find missing files
    print("="*70)
    print(f"MISSING PDF FILES ({len(missing_numbers)} total)")
    print("="*70)
    print()
    
    missing_files_info = []
    
    for num in sorted(missing_numbers):
        if num in mapping:
            filename = mapping[num]
            print(f"  {num:3d}. {filename}")
            missing_files_info.append({
                "number": num,
                "filename": filename,
                "path": f"backend/PickSample200/{filename}"
            })
        else:
            print(f"  {num:3d}. [NUMBER OUT OF RANGE]")
    
    # Save results
    output_json = "missing_pdfs_mapping.json"
    with open(output_json, 'w') as f:
        json.dump(missing_files_info, f, indent=2)
    
    print()
    print(f"💾 Missing PDF files info saved to: {output_json}")
    
    # Save simple list of paths
    output_txt = "missing_pdfs_paths.txt"
    with open(output_txt, 'w') as f:
        for info in missing_files_info:
            f.write(f"{info['path']}\n")
    
    print(f"💾 Missing PDF paths saved to: {output_txt}")
    
    # Save complete mapping for reference
    complete_mapping_file = "complete_pdf_mapping.json"
    with open(complete_mapping_file, 'w') as f:
        json.dump(mapping, f, indent=2)
    
    print(f"📚 Complete PDF mapping (1-{len(mapping)}) saved to: {complete_mapping_file}")
    print()
    
    # Statistics
    print("="*70)
    print("STATISTICS")
    print("="*70)
    print(f"  Total PDFs in PickSample200:     {len(all_pdfs)}")
    print(f"  PDFs processed by Gemini:        {len(all_pdfs) - len(missing_numbers)}")
    print(f"  PDFs missing from Gemini:        {len(missing_numbers)}")
    print(f"  Percentage processed:            {((len(all_pdfs) - len(missing_numbers)) / len(all_pdfs) * 100):.1f}%")
    print("="*70)
    
    return missing_files_info

if __name__ == "__main__":
    print("🔍 Creating PDF mapping and identifying missing files...\n")
    missing_files_info = find_missing_pdf_files()
    
    if missing_files_info:
        print()
        print("="*70)
        print("📝 NEXT STEPS:")
        print("="*70)
        print("1. Review the missing files in 'missing_pdfs_mapping.json'")
        print("2. Choose a processing method:")
        print("   a) Process through Gemini API (requires API key + network)")
        print("   b) Use existing OCR results from results_ocr/")
        print("   c) Extract fields manually")
        print("="*70)

