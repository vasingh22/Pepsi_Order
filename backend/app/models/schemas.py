"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class DocumentStatus(str, Enum):
    """Document processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Upload Schemas
class UploadResponse(BaseModel):
    """Response after file upload"""
    job_id: str = Field(..., description="Unique job identifier")
    filename: str
    status: str
    message: str
    uploaded_at: datetime


# Status Schemas
class StatusResponse(BaseModel):
    """Document processing status"""
    job_id: str
    status: DocumentStatus
    progress: Optional[float] = Field(None, ge=0, le=100, description="Processing progress percentage")
    message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# Result Schemas
class OrderItem(BaseModel):
    """Order item structure"""
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None


class StructuredOrder(BaseModel):
    """Structured order data"""
    customer_name: Optional[str] = None
    customer_id: Optional[str] = None
    order_number: Optional[str] = None
    order_date: Optional[str] = None
    delivery_date: Optional[str] = None
    billing_address: Optional[str] = None
    shipping_address: Optional[str] = None
    items: List[OrderItem] = []
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    currency: Optional[str] = None
    notes: Optional[str] = None


class ResultResponse(BaseModel):
    """Result response"""
    job_id: str
    status: DocumentStatus
    raw_ocr_text: Optional[str] = None
    normalized_text: Optional[str] = None
    structured_json: Optional[StructuredOrder] = None
    validated_json: Optional[StructuredOrder] = None
    confidence_score: Optional[float] = None
    field_accuracy: Optional[Dict[str, float]] = None
    created_at: datetime


# Correction Schemas
class CorrectionRequest(BaseModel):
    """Request to submit correction"""
    corrected_json: Dict[str, Any] = Field(..., description="Corrected structured JSON")
    feedback: Optional[str] = Field(None, description="Optional feedback note")


class CorrectionResponse(BaseModel):
    """Correction submission response"""
    correction_id: int
    job_id: str
    message: str
    created_at: datetime


# Metrics Schemas
class MetricsResponse(BaseModel):
    """Metrics response"""
    job_id: str
    ocr_cost: float
    llm_cost: float
    total_cost: float
    cost_per_document: float
    processing_time_seconds: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


# Error Schemas
class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None



