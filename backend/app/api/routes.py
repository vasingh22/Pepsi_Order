import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional
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

