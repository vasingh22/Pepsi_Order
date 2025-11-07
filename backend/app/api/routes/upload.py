"""
File upload endpoint
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import os
import hashlib
import uuid
from pathlib import Path

from app.database.database import get_db
from app.database.models import Document
from app.models.schemas import UploadResponse
from app.core.config import settings

router = APIRouter()


def calculate_file_hash(file_content: bytes) -> str:
    """Calculate SHA256 hash of file content"""
    return hashlib.sha256(file_content).hexdigest()


def validate_file(file: UploadFile) -> None:
    """Validate uploaded file"""
    # Check file extension
    file_ext = Path(file.filename).suffix[1:].lower() if file.filename else ""
    if file_ext not in [ext.lower() for ext in settings.ALLOWED_EXTENSIONS]:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # Note: File size validation will be done after reading content


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a document (image or PDF) for processing
    
    - **file**: Document file (PDF, PNG, JPG, JPEG)
    - Returns: Job ID and upload confirmation
    """
    try:
        # Validate file
        validate_file(file)
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Check file size
        max_size_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB"
            )
        
        # Calculate file hash for duplicate detection
        file_hash = calculate_file_hash(file_content)
        
        # Check if file already exists (duplicate)
        existing_doc = db.query(Document).filter(Document.file_hash == file_hash).first()
        if existing_doc:
            return UploadResponse(
                job_id=str(existing_doc.id),
                filename=file.filename,
                status="duplicate",
                message="File already processed",
                uploaded_at=existing_doc.uploaded_at
            )
        
        # Generate unique filename
        file_ext = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
        
        # Save file
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Create document record
        document = Document(
            filename=file.filename,
            file_path=file_path,
            file_hash=file_hash,
            file_size=file_size,
            mime_type=file.content_type,
            status="pending"
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        return UploadResponse(
            job_id=str(document.id),
            filename=file.filename,
            status="pending",
            message="File uploaded successfully",
            uploaded_at=document.uploaded_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading file: {str(e)}"
        )



