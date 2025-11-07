"""
Application configuration settings
"""
from pydantic_settings import BaseSettings
from typing import List, Union
import os
from functools import lru_cache
from pydantic import field_validator


class Settings(BaseSettings):
	"""Application settings"""
	
	# App
	APP_NAME: str = "Pepsi Order Digitization API"
	DEBUG: bool = True
	API_VERSION: str = "v1"
	
	# Database
	DATABASE_URL: str = os.getenv(
		"DATABASE_URL",
		"sqlite:///./pepsi_order.db"
	)
	
	# File Upload
	MAX_FILE_SIZE_MB: int = 10
	UPLOAD_DIR: str = "./uploads"
	ALLOWED_EXTENSIONS: List[str] = ["pdf", "PDF", "png", "PNG", "jpg", "JPG", "jpeg", "JPEG"]
	
	# OCR
	SURYA_OCR_ENABLED: bool = False
	SURYA_OCR_API_URL: str = ""
	SURYA_OCR_API_KEY: str = ""
	
	# LLM
	LLM_PROVIDER: str = "openai"
	OPENAI_API_KEY: str = ""
	OPENAI_MODEL: str = "gpt-4-turbo-preview"
	ANTHROPIC_API_KEY: str = ""
	ANTHROPIC_MODEL: str = "claude-3-opus-20240229"
	
	# Temporal
	TEMPORAL_CLOUD_ENABLED: bool = False
	TEMPORAL_CLOUD_ADDRESS: str = ""
	TEMPORAL_NAMESPACE: str = ""
	TEMPORAL_TASK_QUEUE: str = "document-processing"
	
	# Cost
	COST_LIMIT_PER_DOCUMENT: float = 0.04
	
	# CORS
	CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
	
	class Config:
		env_file = ".env"
		case_sensitive = True
	
	@field_validator("ALLOWED_EXTENSIONS", mode="before")
	@classmethod
	def parse_allowed_extensions(cls, value: Union[str, List[str]]):
		"""Allow comma-separated string or JSON list for extensions."""
		if isinstance(value, str):
			parts = [p.strip() for p in value.split(",") if p.strip()]
			return parts if parts else cls.__fields__["ALLOWED_EXTENSIONS"].default
		return value
	
	@field_validator("CORS_ORIGINS", mode="before")
	@classmethod
	def parse_cors_origins(cls, value: Union[str, List[str]]):
		"""Allow comma-separated string or JSON list for CORS origins."""
		if isinstance(value, str):
			parts = [p.strip() for p in value.split(",") if p.strip()]
			return parts if parts else cls.__fields__["CORS_ORIGINS"].default
		return value


@lru_cache()
def get_settings() -> Settings:
	"""Get cached settings instance"""
	return Settings()


settings = get_settings()



