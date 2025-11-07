"""
Results endpoint
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Document, Result
from app.models.schemas import ResultResponse, DocumentStatus, StructuredOrder

router = APIRouter()


@router.get("/results/{job_id}", response_model=ResultResponse)
async def get_results(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Get processing results for a document
    
    - **job_id**: Document ID (from upload response)
    - Returns: Structured JSON and processing metadata
    """
    try:
        document_id = int(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format")
    
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Document processing not completed. Current status: {document.status}"
        )
    
    result = db.query(Result).filter(Result.document_id == document_id).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Results not found")
    
    # Parse structured JSON if available
    structured_json = None
    validated_json = None
    
    if result.structured_json:
        try:
            structured_json = StructuredOrder(**result.structured_json)
        except Exception:
            structured_json = result.structured_json
    
    if result.validated_json:
        try:
            validated_json = StructuredOrder(**result.validated_json)
        except Exception:
            validated_json = result.validated_json
    
    return ResultResponse(
        job_id=job_id,
        status=DocumentStatus(document.status),
        raw_ocr_text=result.raw_ocr_text,
        normalized_text=result.normalized_text,
        structured_json=structured_json,
        validated_json=validated_json,
        confidence_score=result.confidence_score,
        field_accuracy=result.field_accuracy,
        created_at=result.created_at
    )



