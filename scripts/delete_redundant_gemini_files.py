#!/usr/bin/env python3
"""
Delete redundant files from normalized_samples_gemini folder.
Keeps the newer versions (20251112T...) and deletes older versions (20251111T...).
"""
import os
from pathlib import Path

# List of 75 files to delete (older versions from November 11, 2025)
FILES_TO_DELETE = [
    "20251111T183307_1.pdf.gemini.json",
    "20251111T184511_11.pdf.gemini.json",
    "20251111T185203_12.pdf.gemini.json",
    "20251111T185735_13.pdf.gemini.json",
    "20251111T204004_54.pdf.gemini.json",
    "20251111T204057_55.pdf.gemini.json",
    "20251111T204147_56.pdf.gemini.json",
    "20251111T205418_65.pdf.gemini.json",
    "20251111T212832_85.pdf.gemini.json",
    "20251111T213517_91.pdf.gemini.json",
    "20251111T185105_115.pdf.gemini.json",
    "20251111T185259_123.pdf.gemini.json",
    "20251111T185304_124.pdf.gemini.json",
    "20251111T185330_126.pdf.gemini.json",
    "20251111T185709_128.pdf.gemini.json",
    "20251111T185721_129.pdf.gemini.json",
    "20251111T185748_130.pdf.gemini.json",
    "20251111T185802_131.pdf.gemini.json",
    "20251111T185815_132.pdf.gemini.json",
    "20251111T185822_133.pdf.gemini.json",
    "20251111T185833_134.pdf.gemini.json",
    "20251111T185840_135.pdf.gemini.json",
    "20251111T185905_137.pdf.gemini.json",
    "20251111T185917_138.pdf.gemini.json",
    "20251111T185924_139.pdf.gemini.json",
    "20251111T185947_140.pdf.gemini.json",
    "20251111T185957_141.pdf.gemini.json",
    "20251111T190029_143.pdf.gemini.json",
    "20251111T190045_144.pdf.gemini.json",
    "20251111T190101_145.pdf.gemini.json",
    "20251111T190120_146.pdf.gemini.json",
    "20251111T190133_147.pdf.gemini.json",
    "20251111T190142_148.pdf.gemini.json",
    "20251111T190152_149.pdf.gemini.json",
    "20251111T190219_150.pdf.gemini.json",
    "20251111T190225_151.pdf.gemini.json",
    "20251111T190237_152.pdf.gemini.json",
    "20251111T190246_153.pdf.gemini.json",
    "20251111T190253_154.pdf.gemini.json",
    "20251111T190302_155.pdf.gemini.json",
    "20251111T190311_156.pdf.gemini.json",
    "20251111T190320_157.pdf.gemini.json",
    "20251111T190327_158.pdf.gemini.json",
    "20251111T190338_159.pdf.gemini.json",
    "20251111T190402_160.pdf.gemini.json",
    "20251111T190410_161.pdf.gemini.json",
    "20251111T190417_162.pdf.gemini.json",
    "20251111T190424_163.pdf.gemini.json",
    "20251111T190437_164.pdf.gemini.json",
    "20251111T190446_165.pdf.gemini.json",
    "20251111T190503_166.pdf.gemini.json",
    "20251111T190518_168.pdf.gemini.json",
    "20251111T190532_169.pdf.gemini.json",
    "20251111T190556_170.pdf.gemini.json",
    "20251111T190605_171.pdf.gemini.json",
    "20251111T190613_172.pdf.gemini.json",
    "20251111T190629_173.pdf.gemini.json",
    "20251111T190636_174.pdf.gemini.json",
    "20251111T190656_175.pdf.gemini.json",
    "20251111T190713_176.pdf.gemini.json",
    "20251111T190721_177.pdf.gemini.json",
    "20251111T190732_178.pdf.gemini.json",
    "20251111T190740_179.pdf.gemini.json",
    "20251111T191519_182.pdf.gemini.json",
    "20251111T191546_185.pdf.gemini.json",
    "20251111T191554_186.pdf.gemini.json",
    "20251111T191603_187.pdf.gemini.json",
    "20251111T191609_188.pdf.gemini.json",
    "20251111T191647_190.pdf.gemini.json",
    "20251111T191701_191.pdf.gemini.json",
    "20251111T191709_192.pdf.gemini.json",
    "20251111T191732_194.pdf.gemini.json",
    "20251111T191740_195.pdf.gemini.json",
    "20251111T191751_196.pdf.gemini.json",
    "20251111T191805_197.pdf.gemini.json",
]

def delete_redundant_files():
    """
    Delete the redundant/duplicate files from normalized_samples_gemini folder.
    """
    
    # Try multiple possible locations
    possible_dirs = [
        "normalized_samples_gemini",
        "backend/normalized_samples_gemini",
        "../normalized_samples_gemini"
    ]
    
    gemini_dir = None
    for dir_path in possible_dirs:
        if Path(dir_path).exists():
            gemini_dir = Path(dir_path)
            break
    
    if not gemini_dir:
        print("❌ Error: normalized_samples_gemini folder not found!")
        print("Searched in:")
        for dir_path in possible_dirs:
            print(f"  - {dir_path}")
        return
    
    print(f"📁 Found directory: {gemini_dir}")
    print(f"🗑️  Preparing to delete {len(FILES_TO_DELETE)} redundant files...")
    print("="*70)
    
    deleted_count = 0
    not_found_count = 0
    error_count = 0
    
    for filename in FILES_TO_DELETE:
        file_path = gemini_dir / filename
        
        if file_path.exists():
            try:
                file_path.unlink()
                deleted_count += 1
                if deleted_count % 10 == 0:
                    print(f"  Progress: {deleted_count}/{len(FILES_TO_DELETE)} files deleted...")
            except Exception as e:
                print(f"❌ Error deleting {filename}: {e}")
                error_count += 1
        else:
            not_found_count += 1
            if not_found_count <= 5:  # Only show first 5 missing files
                print(f"⚠️  File not found (already deleted?): {filename}")
    
    print("="*70)
    print("✅ CLEANUP COMPLETE")
    print("="*70)
    print(f"Files deleted:     {deleted_count}")
    print(f"Files not found:   {not_found_count}")
    print(f"Errors:            {error_count}")
    print(f"Total processed:   {len(FILES_TO_DELETE)}")
    print("="*70)
    
    # Verify final count
    remaining_files = list(gemini_dir.glob("*.json"))
    print(f"\n📊 Final Status:")
    print(f"Files remaining in folder: {len(remaining_files)}")
    print(f"Expected after cleanup:    163")
    print("="*70)

if __name__ == "__main__":
    print("🧹 REDUNDANT FILE CLEANUP UTILITY")
    print("="*70)
    print("This script will delete 75 older duplicate files")
    print("Keeping only the newer versions from November 12, 2025")
    print("="*70)
    print()
    
    delete_redundant_files()

