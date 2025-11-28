import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_ocr_service
from app.config import Settings, get_settings
from app.schemas import OCRResult, SampleList
from app.services.ocr_service import SuryaOCRService

router = APIRouter(prefix="", tags=["OCR"])


@router.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ocr/samples", response_model=SampleList, summary="List reference sample PDFs")
async def list_samples(settings: Settings = Depends(get_settings)) -> SampleList:
    sample_dir = settings.sample_dir
    if not sample_dir.exists():
        return SampleList(samples=[])
    samples = sorted(
        file_path.name
        for file_path in sample_dir.iterdir()
        if file_path.is_file() and file_path.suffix.lower().lstrip(".") in settings.allowed_extensions
    )
    return SampleList(samples=samples)


@router.get(
    "/ocr/extract/sample",
    response_model=OCRResult,
    summary="Run OCR against a sample file that already exists on the server",
)
async def extract_sample(
    filename: str = Query(..., description="Name of the PDF within the configured sample directory."),
    languages: Optional[str] = Query(
        default=None,
        description="Comma-separated language codes (e.g. 'eng,hin'). Defaults to server setting.",
    ),
    include_raw: bool = Query(
        default=False,
        description="Return the raw response from Surya in addition to the normalised output.",
    ),
    ocr_service: SuryaOCRService = Depends(get_ocr_service),
    settings: Settings = Depends(get_settings),
) -> OCRResult:
    pdf_path = (settings.sample_dir / filename).resolve()
    if not pdf_path.exists() or pdf_path.suffix.lower().lstrip(".") not in settings.allowed_extensions:
        raise HTTPException(status_code=404, detail="Sample PDF not found.")

    languages_list = _parse_languages(languages)
    return await _run_ocr(ocr_service, pdf_path, languages_list, include_raw)


@router.post(
    "/ocr/extract",
    response_model=OCRResult,
    summary="Upload a PDF invoice and extract its content with Surya OCR.",
)
async def extract_upload(
    file: UploadFile = File(..., description="PDF invoice to process"),
    languages: Optional[str] = Query(
        default=None,
        description="Comma-separated language codes (e.g. 'eng,hin'). Defaults to server setting.",
    ),
    include_raw: bool = Query(
        default=False,
        description="Return the raw response from Surya in addition to the normalised output.",
    ),
    ocr_service: SuryaOCRService = Depends(get_ocr_service),
    settings: Settings = Depends(get_settings),
) -> OCRResult:
    _validate_file(file, settings)

    tmp_filename = f"{uuid4().hex}.pdf"
    tmp_path = settings.temp_dir / tmp_filename
    total_bytes = 0
    max_bytes = settings.max_upload_size_mb * 1024 * 1024

    try:
        with tmp_path.open("wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds {settings.max_upload_size_mb} MB limit.",
                    )
                buffer.write(chunk)
    finally:
        await file.close()

    languages_list = _parse_languages(languages)

    try:
        return await _run_ocr(
            ocr_service,
            tmp_path,
            languages_list,
            include_raw,
            upload_name=file.filename,
        )
    finally:
        tmp_path.unlink(missing_ok=True)


async def _run_ocr(
    ocr_service: SuryaOCRService,
    pdf_path: Path,
    languages: Optional[List[str]],
    include_raw: bool,
    upload_name: Optional[str] = None,
) -> OCRResult:
    result = await run_in_threadpool(
        ocr_service.extract_from_pdf,
        pdf_path,
        languages,
        include_raw,
    )

    # Override filename with uploaded name when available.
    if upload_name:
        result.filename = upload_name

    _persist_result(result)
    return result


def _validate_file(file: UploadFile, settings: Settings) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    suffix = Path(file.filename).suffix.lower().lstrip(".")
    if suffix not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '.{suffix}'. Allowed: {', '.join(settings.allowed_extensions)}",
        )

    if file.content_type and "pdf" not in file.content_type:
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF document.")


def _parse_languages(languages: Optional[str]) -> Optional[List[str]]:
    if not languages:
        return None
    parts = [item.strip() for item in languages.split(",")]
    parsed = [part for part in parts if part]
    return parsed or None


def _persist_result(result: OCRResult) -> None:
    """Persist the OCR response to the results directory for auditing."""
    results_dir = Path.cwd() / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", result.filename or "document")
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    output_path = results_dir / f"{timestamp}_{safe_name}.json"
    payload = json.loads(result.model_dump_json(by_alias=True))

    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


@router.get("/invoices", summary="List all extracted invoices")
async def list_invoices() -> Dict[str, Any]:
    """List all invoices from successful and needs_review folders."""
    base_dir = Path.cwd().parent if Path.cwd().name == "backend" else Path.cwd()
    successful_dir = base_dir / "extracted_final_v2" / "successful"
    needs_review_dir = base_dir / "extracted_final_v2" / "needs_review"
    
    invoices = []
    
    # Load successful invoices
    if successful_dir.exists():
        for file_path in successful_dir.glob("*.json"):
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                invoices.append({
                    "filename": file_path.name,
                    "data": data,
                    "status": "successful",
                    "modified_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                })
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
    
    # Load needs_review invoices
    if needs_review_dir.exists():
        for file_path in needs_review_dir.glob("*.json"):
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                invoices.append({
                    "filename": file_path.name,
                    "data": data,
                    "status": "needs_review",
                    "modified_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                })
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
    
    # Sort by filename
    invoices.sort(key=lambda x: x["filename"])
    
    return {"invoices": invoices}


@router.get("/invoices/{filename:path}", summary="Get a specific invoice by filename")
async def get_invoice(filename: str) -> Dict[str, Any]:
    """Get a specific invoice by filename from successful or needs_review folders."""
    base_dir = Path.cwd().parent if Path.cwd().name == "backend" else Path.cwd()
    successful_dir = base_dir / "extracted_final_v2" / "successful"
    needs_review_dir = base_dir / "extracted_final_v2" / "needs_review"
    
    # Try successful first
    file_path = successful_dir / filename
    if not file_path.exists():
        # Try needs_review
        file_path = needs_review_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Invoice {filename} not found")
    
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        
        status = "successful" if successful_dir in file_path.parents else "needs_review"
        
        return {
            "filename": filename,
            "data": data,
            "status": status,
            "modified_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading invoice: {str(e)}")


def _parse_line_items_from_ocr_text(text: str) -> List[Dict[str, Any]]:
    """Parse line items from OCR text.
    
    Expected format in text:
    ITEM GTIN DESCRIPTION QUANTITY UNIT RATE VALUE
    Example: 00010 00028400363136 2CT XVL TO SAL VER 30 CS 3.78 CS 1,013.4
    """
    line_items = []
    
    # Find the line items section (after headers like ITEM, GTIN, DESCRIPTION, etc.)
    # The text might have the header and items in a continuous string
    
    # Look for pattern: 5-digit item number followed by 12-14 digit GTIN
    # Pattern: 00010 00028400363136 ... description ... quantity ... unit ... rate ... value
    pattern = r'(\d{5})\s+(\d{12,14})\s+(.+?)\s+(\d+(?:,\d{3})*(?:\.\d+)?)\s+([A-Z]{1,4})\s+(\d+(?:,\d{3})*(?:\.\d+)?)\s+[A-Z]{1,4}\s+(\d+(?:,\d{3})*(?:\.\d+)?)'
    
    matches = re.finditer(pattern, text)
    
    for match in matches:
        try:
            item_id = match.group(1)
            gtin = match.group(2)
            description = match.group(3).strip()
            quantity = match.group(4).replace(',', '')
            unit = match.group(5)
            rate = match.group(6).replace(',', '')
            value = match.group(7).replace(',', '')
            
            # Clean up description (remove extra spaces, numbers at start if any)
            description = re.sub(r'^\d+\s+', '', description)  # Remove leading numbers
            description = ' '.join(description.split())  # Normalize whitespace
            
            line_items.append({
                "item_id": item_id,
                "gtin": gtin,
                "description": description,
                "quantity": quantity,
                "unit": unit,
                "unit_price": float(rate) if rate else None,
                "total": float(value) if value else None,
            })
        except Exception as e:
            # Skip matches that can't be parsed
            continue
    
    # If regex didn't work, try a simpler approach - look for lines starting with 5-digit numbers
    if not line_items:
        lines = text.split('\n')
        
        # Find header row
        header_found = False
        for i, line in enumerate(lines):
            if 'ITEM' in line.upper() and 'GTIN' in line.upper():
                header_found = True
                # Start parsing from next line
                for j in range(i + 1, min(i + 100, len(lines))):  # Limit to next 100 lines
                    line_text = lines[j].strip()
                    if not line_text or len(line_text) < 10:
                        continue
                    
                    # Check if line starts with 5-digit number (item ID)
                    parts = line_text.split()
                    if len(parts) >= 6 and (parts[0].isdigit() and len(parts[0]) == 5):
                        try:
                            item_id = parts[0]
                            # Find GTIN (long number)
                            gtin = None
                            gtin_idx = -1
                            for idx, part in enumerate(parts[1:6], 1):
                                if len(part) >= 12 and part.isdigit():
                                    gtin = part
                                    gtin_idx = idx
                                    break
                            
                            if not gtin:
                                continue
                            
                            # Description is between GTIN and quantity
                            desc_start = gtin_idx + 1
                            desc_end = -1
                            qty = None
                            unit = None
                            rate = None
                            value = None
                            
                            # Find quantity (number followed by unit like "CS")
                            for idx in range(desc_start, len(parts)):
                                if parts[idx].replace(',', '').replace('.', '').isdigit():
                                    try:
                                        test_qty = float(parts[idx].replace(',', ''))
                                        if 0 < test_qty < 10000:
                                            qty = parts[idx]
                                            unit = parts[idx + 1] if idx + 1 < len(parts) else "CS"
                                            desc_end = idx
                                            # Rate should be after unit
                                            if idx + 2 < len(parts):
                                                try:
                                                    rate = float(parts[idx + 2].replace(',', ''))
                                                except:
                                                    pass
                                            # Value is usually the last large number
                                            for k in range(len(parts) - 1, max(idx + 2, len(parts) - 3), -1):
                                                try:
                                                    test_val = float(parts[k].replace(',', ''))
                                                    if test_val > 10:  # Values are usually > 10
                                                        value = test_val
                                                        break
                                                except:
                                                    pass
                                            break
                                    except:
                                        pass
                            
                            if desc_end > desc_start and qty:
                                description = ' '.join(parts[desc_start:desc_end])
                                line_items.append({
                                    "item_id": item_id,
                                    "gtin": gtin,
                                    "description": description,
                                    "quantity": qty.replace(',', ''),
                                    "unit": unit or "CS",
                                    "unit_price": rate,
                                    "total": value,
                                })
                        except Exception:
                            continue
                break
    
    return line_items


@router.get("/invoices/{filename:path}/ocr", summary="Get OCR data for a specific invoice")
async def get_invoice_ocr(filename: str) -> Dict[str, Any]:
    """Get OCR data for a specific invoice from results_ocr-final folder."""
    base_dir = Path.cwd().parent if Path.cwd().name == "backend" else Path.cwd()
    ocr_dir = base_dir / "results_ocr-final"
    
    # Try to find the OCR file - it might have a different name pattern
    # Look for files that match the invoice filename pattern
    ocr_file = None
    
    # First, try exact match with .json extension
    potential_names = [
        filename.replace("_extracted.json", ".pdf.json"),
        filename.replace("_extracted", ".pdf.json"),
        filename + ".json",
    ]
    
    # Also try to extract the base name from the extracted filename
    if "_extracted" in filename:
        base_name = filename.split("_extracted")[0]
        potential_names.append(f"{base_name}.pdf.json")
    
    for name in potential_names:
        file_path = ocr_dir / name
        if file_path.exists():
            ocr_file = file_path
            break
    
    # If not found, try to find by matching the beginning of the filename
    if not ocr_file:
        for file_path in ocr_dir.glob("*.json"):
            # Check if the OCR filename starts with the same timestamp pattern
            if filename.startswith("20251112T") and file_path.name.startswith("20251112T"):
                # Extract the number part and compare
                try:
                    inv_num = filename.split("_")[0].split("T")[1] if "_" in filename else ""
                    ocr_num = file_path.name.split("_")[0].split("T")[1] if "_" in file_path.name else ""
                    if inv_num and ocr_num and inv_num == ocr_num:
                        ocr_file = file_path
                        break
                except:
                    pass
    
    if not ocr_file:
        raise HTTPException(status_code=404, detail=f"OCR file for {filename} not found")
    
    try:
        with ocr_file.open("r", encoding="utf-8") as f:
            ocr_data = json.load(f)
        
        # Extract line items from OCR text
        line_items = []
        if "pages" in ocr_data:
            # Combine all page text
            full_text = "\n".join([page.get("text", "") for page in ocr_data.get("pages", [])])
            line_items = _parse_line_items_from_ocr_text(full_text)
        
        return {
            "filename": ocr_file.name,
            "ocr_data": ocr_data,
            "line_items": line_items,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading OCR file: {str(e)}")

