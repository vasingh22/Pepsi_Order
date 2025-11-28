import os
from pathlib import Path

def find_missing_pdfs():
    """
    Compare PDFs in PickSample200 with OCR results in backend/results
    to find which PDFs haven't been processed yet.
    """
    
    # Get all PDFs from PickSample200
    pdf_dir = "backend/PickSample200"
    pdf_files = []
    for ext in ['*.pdf', '*.PDF']:
        pdf_files.extend(Path(pdf_dir).glob(ext))
    
    pdf_basenames = set()
    pdf_full_paths = {}
    for pdf_path in pdf_files:
        basename = pdf_path.stem  # filename without extension
        pdf_basenames.add(basename)
        pdf_full_paths[basename] = str(pdf_path)
    
    print(f"📁 Total PDFs in PickSample200: {len(pdf_basenames)}")
    
    # Get all OCR results from backend/results
    results_dir = "backend/results"
    ocr_files = list(Path(results_dir).glob("*.json"))
    
    # Extract the original PDF names from OCR filenames
    # OCR files are named like: 20251109T101227_ORIGINAL_NAME.pdf.json
    processed_basenames = set()
    for ocr_path in ocr_files:
        ocr_name = ocr_path.stem  # Remove .json
        # Remove the timestamp prefix (format: 20251109T101227_)
        if '_' in ocr_name:
            parts = ocr_name.split('_', 1)
            if len(parts) > 1 and parts[0][:8].isdigit():
                original_name = parts[1]
                # Remove .pdf extension if present
                if original_name.endswith('.pdf'):
                    original_name = original_name[:-4]
                processed_basenames.add(original_name)
    
    print(f"✅ OCR results found: {len(processed_basenames)}")
    
    # Find missing PDFs
    missing_pdfs = []
    for pdf_basename in sorted(pdf_basenames):
        # Check if this PDF has been processed
        found = False
        for processed in processed_basenames:
            if pdf_basename in processed or processed in pdf_basename:
                found = True
                break
        
        if not found:
            missing_pdfs.append(pdf_full_paths[pdf_basename])
    
    print(f"❌ PDFs missing OCR: {len(missing_pdfs)}")
    print("="*70)
    
    # Save missing PDFs to a file
    output_file = "missing_pdfs.txt"
    with open(output_file, 'w') as f:
        for pdf_path in missing_pdfs:
            f.write(f"{pdf_path}\n")
    
    print(f"\n📄 Missing PDFs saved to: {output_file}")
    
    # Show first 10 missing PDFs
    if missing_pdfs:
        print(f"\n📋 First 10 missing PDFs:")
        for i, pdf_path in enumerate(missing_pdfs[:10], 1):
            print(f"  {i}. {Path(pdf_path).name}")
        if len(missing_pdfs) > 10:
            print(f"  ... and {len(missing_pdfs) - 10} more")
    
    return missing_pdfs

if __name__ == "__main__":
    print("🔍 Searching for PDFs that need OCR processing...\n")
    missing = find_missing_pdfs()
    print("\n✅ Analysis complete!")

