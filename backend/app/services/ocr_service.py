"""
OCR service: extract text from images and PDFs.

Primary implementation uses Surya OCR when SURYA_OCR_ENABLED=True.
Falls back to local Tesseract only if explicitly disabled (not used in Docker).
"""
from typing import List, Tuple
from dataclasses import dataclass
import os

from app.core.config import settings
from app.services.surya_ocr_service import extract_text_via_surya

# Local fallback imports are optional and only used if enabled
try:
	from PIL import Image  # type: ignore
	from pdf2image import convert_from_path  # type: ignore
	import pytesseract  # type: ignore
	_LOCAL_OCR_AVAILABLE = True
except Exception:
	_LOCAL_OCR_AVAILABLE = False


@dataclass
class OCRResult:
	text: str
	pages: int


def _extract_text_from_image_local(image: "Image.Image") -> str:
	"""Run OCR on a single PIL image."""
	return pytesseract.image_to_string(image)


def _extract_text_from_pdf_local(pdf_path: str, dpi: int = 300) -> Tuple[str, int]:
	"""Convert PDF to images and run OCR page by page."""
	pages: List[Image.Image] = convert_from_path(pdf_path, dpi=dpi)
	all_text_parts: List[str] = []
	for page in pages:
		page_text = _extract_text_from_image_local(page)
		all_text_parts.append(page_text)
	return "\n\n".join(all_text_parts), len(pages)


def extract_text(file_path: str) -> OCRResult:
	"""Extract text using Surya OCR (preferred) or local fallback if enabled."""
	if settings.SURYA_OCR_ENABLED:
		result = extract_text_via_surya(file_path)
		return OCRResult(text=result.text, pages=result.pages)
	
	# Fallback (not used in Docker image as we don't ship tesseract/poppler)
	if _LOCAL_OCR_AVAILABLE:
		_, ext = os.path.splitext(file_path)
		ext = ext.lower()
		if ext in [".pdf"]:
			text, pages = _extract_text_from_pdf_local(file_path)
		elif ext in [".png", ".jpg", ".jpeg"]:
			image = Image.open(file_path)
			text = _extract_text_from_image_local(image)
			pages = 1
		else:
			raise ValueError(f"Unsupported file extension: {ext}")
		return OCRResult(text=text, pages=pages)
	
	raise RuntimeError("No OCR backend available. Enable SURYA_OCR_ENABLED and set SURYA_OCR_API_URL.")
