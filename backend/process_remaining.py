#!/usr/bin/env python3
"""
Script to process remaining unprocessed PDF files through the OCR service.
"""
import logging
from pathlib import Path
import json
from app.services.ocr_service import SuryaOCRService
from app.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_all_pdfs():
    """
    Processes all PDF files in the input directory, generates normalized JSON,
    and saves them to the output directory.
    """
    settings = get_settings()
    input_dir = Path("PickSample200")
    output_dir = Path("results")

    # Ensure the output directory exists
    output_dir.mkdir(exist_ok=True)

    # Initialize the OCR service
    # You can specify languages if needed, e.g., ["en", "hi"]
    ocr_service = SuryaOCRService()

    # Find all PDF files in the input directory
    pdf_files = list(input_dir.glob("*.pdf")) + list(input_dir.glob("*.PDF"))
    total_files = len(pdf_files)
    logging.info(f"Found {total_files} PDF files to process.")

    for i, pdf_path in enumerate(pdf_files):
        logging.info(f"Processing file {i+1}/{total_files}: {pdf_path.name}")
        output_path = output_dir / f"{pdf_path.stem}.json"

        if output_path.exists():
            logging.info(f"Result for {pdf_path.name} already exists. Skipping.")
            continue

        try:
            # This single call runs the entire pipeline: OCR and normalization
            ocr_result = ocr_service.extract_from_pdf(pdf_path, include_raw=False)

            # Convert the result to a dictionary for JSON serialization
            result_dict = ocr_result.model_dump(exclude_none=True)

            # Save the JSON output
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result_dict, f, indent=2, ensure_ascii=False)

            logging.info(f"Successfully processed and saved {output_path.name}")

        except Exception as e:
            logging.error(f"Failed to process {pdf_path.name}: {e}", exc_info=True)
            # Optionally, you could save a log of failed files
            with open("processing_log.txt", "a", encoding="utf-8") as log_file:
                log_file.write(f"Error processing {pdf_path.name}: {e}\n")

    logging.info("All PDF files have been processed.")

if __name__ == "__main__":
    process_all_pdfs()

