"""
Corrections endpoint - for human feedback and continuous learning
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Document, Result, Correction
from app.models.schemas import CorrectionRequest, CorrectionResponse

router = APIRouter()


@router.post("/correct/{job_id}", response_model=CorrectionResponse)
async def submit_correction(
    job_id: str,
    correction: CorrectionRequest,
    db: Session = Depends(get_db)
):
    """
    Submit human correction for a processed document
    
    - **job_id**: Document ID
    - **correction**: Corrected JSON and optional feedback
    - Returns: Confirmation of correction submission
    """
    try:
        document_id = int(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format")
    
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    result = db.query(Result).filter(Result.document_id == document_id).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Results not found")
    
    # Get original JSON
    original_json = result.validated_json or result.structured_json or {}
    
    # Identify which fields were corrected
    corrections = {}
    if isinstance(original_json, dict) and isinstance(correction.corrected_json, dict):
        for key, value in correction.corrected_json.items():
            if key not in original_json or original_json[key] != value:
                corrections[key] = {
                    "original": original_json.get(key),
                    "corrected": value
                }
    
    # Create correction record
    correction_record = Correction(
        document_id=document_id,
        original_json=original_json,
        corrected_json=correction.corrected_json,
        corrections=corrections if corrections else None,
        feedback=correction.feedback,
        used_for_training=False
    )
    
    db.add(correction_record)
    db.commit()
    db.refresh(correction_record)
    
    return CorrectionResponse(
        correction_id=correction_record.id,
        job_id=job_id,
        message="Correction submitted successfully. Will be used for continuous learning.",
        created_at=correction_record.created_at
    )



