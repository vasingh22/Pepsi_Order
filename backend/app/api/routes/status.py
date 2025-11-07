"""
Status check endpoint
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Document
from app.models.schemas import StatusResponse, DocumentStatus

router = APIRouter()


@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Get processing status of a document
    
    - **job_id**: Document ID (from upload response)
    - Returns: Current status and progress
    """
    try:
        document_id = int(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format")
    
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Calculate progress (placeholder - will be enhanced with actual workflow progress)
    progress = None
    if document.status == "completed":
        progress = 100.0
    elif document.status == "processing":
        progress = 50.0  # Will be updated by workflow
    elif document.status == "pending":
        progress = 0.0
    
    return StatusResponse(
        job_id=job_id,
        status=DocumentStatus(document.status),
        progress=progress,
        message=f"Document is {document.status}",
        created_at=document.uploaded_at,
        updated_at=document.processed_at
    )



