from threading import Lock
from typing import Optional

from fastapi import Depends

from app.config import Settings, get_settings
from app.services.ocr_service import SuryaOCRService

_service_instance: Optional[SuryaOCRService] = None
_service_lock = Lock()


def get_ocr_service(settings: Settings = Depends(get_settings)) -> SuryaOCRService:
    global _service_instance
    if _service_instance is not None:
        return _service_instance

    with _service_lock:
        if _service_instance is None:
            _service_instance = SuryaOCRService(default_languages=settings.default_languages)
    return _service_instance

