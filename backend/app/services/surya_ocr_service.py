"""
Surya OCR client integration.
Requires:
- SURYA_OCR_API_URL (base endpoint for OCR)
- SURYA_OCR_API_KEY (optional, for Authorization header)

This client POSTs the document and expects JSON response containing text.
"""
import os
from dataclasses import dataclass
from typing import Optional
import httpx

from app.core.config import settings


@dataclass
class SuryaOCRResult:
	text: str
	pages: int


def extract_text_via_surya(file_path: str, timeout_seconds: int = 120) -> SuryaOCRResult:
	"""Call Surya OCR API to extract text from the given file path."""
	api_url = settings.SURYA_OCR_API_URL.strip()
	if not api_url:
		raise RuntimeError("SURYA_OCR_API_URL is not configured")
	
	headers = {}
	if settings.__dict__.get("SURYA_OCR_API_KEY"):
		headers["Authorization"] = f"Bearer {settings.__dict__.get('SURYA_OCR_API_KEY')}"
	
	# Some Surya deployments expect multipart form with field name 'file'
	with open(file_path, "rb") as f:
		files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
		with httpx.Client(timeout=timeout_seconds) as client:
			resp = client.post(api_url, headers=headers, files=files)
			resp.raise_for_status()
			data = resp.json()
			# Flexible extraction of text/pages
			text = data.get("text") or data.get("ocr_text") or ""
			pages = int(data.get("pages") or data.get("page_count") or 1)
			return SuryaOCRResult(text=text, pages=pages)
