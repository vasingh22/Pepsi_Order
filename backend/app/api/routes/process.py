"""
Processing endpoint: run OCR extraction and pre-LLM normalization.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.database.database import get_db
from app.database.models import Document, Result
from app.services.ocr_service import extract_text
from app.services.text_normalizer import normalize_text

router = APIRouter()


@router.post("/process/{job_id}")
async def process_document(job_id: str, db: Session = Depends(get_db)):
	"""
	Run OCR and text normalization for a given uploaded document.
	Stores raw_ocr_text and normalized_text in Result table.
	"""
	try:
		document_id = int(job_id)
	except ValueError:
		raise HTTPException(status_code=400, detail="Invalid job_id format")

	document = db.query(Document).filter(Document.id == document_id).first()
	if not document:
		raise HTTPException(status_code=404, detail="Document not found")

	# Update status to processing
	document.status = "processing"
	db.commit()

	try:
		# OCR extraction
		ocr_result = extract_text(document.file_path)
		# Normalize text
		norm = normalize_text(ocr_result.text)

		# Upsert Result
		result = db.query(Result).filter(Result.document_id == document_id).first()
		if result is None:
			result = Result(
				document_id=document_id,
				raw_ocr_text=ocr_result.text,
				normalized_text=norm,
			)
			db.add(result)
		else:
			result.raw_ocr_text = ocr_result.text
			result.normalized_text = norm

		# Mark document as completed for extraction phase
		document.status = "completed"
		document.processed_at = datetime.utcnow()
		db.commit()

		return {
			"job_id": job_id,
			"status": document.status,
			"pages": ocr_result.pages,
			"message": "OCR extraction and normalization completed"
		}
	except Exception as e:
		document.status = "failed"
		db.commit()
		raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
