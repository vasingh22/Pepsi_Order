"""
Metrics endpoint - for cost and performance tracking
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Document, Metric
from app.models.schemas import MetricsResponse

router = APIRouter()


@router.get("/metrics/{job_id}", response_model=MetricsResponse)
async def get_metrics(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Get cost and performance metrics for a document
    
    - **job_id**: Document ID
    - Returns: Cost breakdown and processing metrics
    """
    try:
        document_id = int(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format")
    
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    metric = db.query(Metric).filter(Metric.document_id == document_id).first()
    
    if not metric:
        raise HTTPException(
            status_code=404,
            detail="Metrics not available. Document may not be processed yet."
        )
    
    return MetricsResponse(
        job_id=job_id,
        ocr_cost=metric.ocr_cost,
        llm_cost=metric.llm_cost,
        total_cost=metric.total_cost,
        cost_per_document=metric.cost_per_document,
        processing_time_seconds=metric.processing_time_seconds,
        input_tokens=metric.input_tokens,
        output_tokens=metric.output_tokens,
        total_tokens=metric.total_tokens
    )



