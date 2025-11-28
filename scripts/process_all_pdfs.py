"""
Script to process all PDF files in PickSample200 directory using Surya OCR.
Saves results to results_ocr folder.
"""
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
import re

# Add backend to path so we can import the service
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.ocr_service import SuryaOCRService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_all_pdfs():
    """Process all PDF files in PickSample200 directory."""
    
    # Setup paths
    base_dir = Path(__file__).parent
    pdf_dir = base_dir / "backend" / "PickSample200"
    output_dir = base_dir / "results_ocr"
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if PDF directory exists
    if not pdf_dir.exists():
        logger.error(f"PDF directory not found: {pdf_dir}")
        return
    
    # Find all PDF files (case-insensitive)
    pdf_files = sorted(
        list(pdf_dir.glob("*.pdf")) + list(pdf_dir.glob("*.PDF"))
    )
    
    total_files = len(pdf_files)
    
    if total_files == 0:
        logger.warning(f"No PDF files found in {pdf_dir}")
        return
    
    logger.info(f"Found {total_files} PDF files to process")
    logger.info(f"Output directory: {output_dir}")
    
    # Initialize OCR service
    logger.info("Initializing Surya OCR service...")
    try:
        ocr_service = SuryaOCRService(default_languages=["en"])
    except Exception as e:
        logger.error(f"Failed to initialize OCR service: {e}")
        return
    
    # Process each PDF
    successful = 0
    failed = 0
    skipped = 0
    
    for i, pdf_path in enumerate(pdf_files, 1):
        try:
            # Create safe filename for output
            safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", pdf_path.name)
            timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            output_filename = f"{timestamp}_{safe_name}.json"
            output_path = output_dir / output_filename
            
            # Check if already processed
            if output_path.exists():
                logger.info(f"[{i}/{total_files}] SKIPPED (already exists): {pdf_path.name}")
                skipped += 1
                continue
            
            logger.info(f"[{i}/{total_files}] Processing: {pdf_path.name}")
            
            # Run OCR extraction
            result = ocr_service.extract_from_pdf(
                pdf_path=pdf_path,
                languages=["en"],
                include_raw=False  # Set to True if you want raw Surya output
            )
            
            # Save result as JSON
            payload = json.loads(result.model_dump_json(by_alias=True))
            
            with output_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[{i}/{total_files}] ✓ SUCCESS: Saved to {output_filename}")
            successful += 1
            
        except Exception as e:
            logger.error(f"[{i}/{total_files}] ✗ FAILED: {pdf_path.name} - Error: {e}")
            failed += 1
            continue
    
    # Print summary
    logger.info("=" * 70)
    logger.info("PROCESSING COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Total files found:        {total_files}")
    logger.info(f"Successfully processed:   {successful}")
    logger.info(f"Skipped (already exist):  {skipped}")
    logger.info(f"Failed:                   {failed}")
    logger.info(f"Output directory:         {output_dir}")
    logger.info("=" * 70)


if __name__ == "__main__":
    logger.info("Starting OCR extraction for all PDFs in PickSample200...")
    logger.info("")
    
    try:
        process_all_pdfs()
    except KeyboardInterrupt:
        logger.warning("\nProcess interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
    
    logger.info("\n✅ Script execution completed.")

