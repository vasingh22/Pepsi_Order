"""
Database models for Pepsi Order Digitization System
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.database import Base


class Document(Base):
    """Document model - stores uploaded file metadata"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_hash = Column(String(64), unique=True, index=True)  # For duplicate detection
    file_size = Column(Integer)  # in bytes
    mime_type = Column(String(100))
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    results = relationship("Result", back_populates="document", uselist=False)
    metrics = relationship("Metric", back_populates="document", uselist=False)
    corrections = relationship("Correction", back_populates="document")


class Result(Base):
    """Result model - stores structured JSON output"""
    __tablename__ = "results"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), unique=True, nullable=False)
    
    # OCR output
    raw_ocr_text = Column(Text, nullable=True)
    normalized_text = Column(Text, nullable=True)
    
    # Structured output
    structured_json = Column(JSON, nullable=True)
    validated_json = Column(JSON, nullable=True)
    
    # Accuracy metrics
    confidence_score = Column(Float, default=0.0)
    field_accuracy = Column(JSON, nullable=True)  # Per-field accuracy scores
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="results")


class Correction(Base):
    """Correction model - stores human feedback for continuous learning"""
    __tablename__ = "corrections"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    
    # Correction data
    original_json = Column(JSON, nullable=False)
    corrected_json = Column(JSON, nullable=False)
    corrections = Column(JSON, nullable=True)  # Specific fields that were corrected
    feedback = Column(Text, nullable=True)
    
    # Learning metadata
    used_for_training = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="corrections")


class Metric(Base):
    """Metric model - tracks cost and performance metrics"""
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), unique=True, nullable=False)
    
    # Cost tracking
    ocr_cost = Column(Float, default=0.0)
    llm_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    cost_per_document = Column(Float, default=0.0)
    
    # Performance metrics
    processing_time_seconds = Column(Float, nullable=True)
    ocr_time_seconds = Column(Float, nullable=True)
    llm_time_seconds = Column(Float, nullable=True)
    normalization_time_seconds = Column(Float, nullable=True)
    
    # Token usage (for LLM)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="metrics")


class Cache(Base):
    """Cache model - for duplicate detection"""
    __tablename__ = "cache"
    
    id = Column(Integer, primary_key=True, index=True)
    file_hash = Column(String(64), unique=True, index=True, nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document")



