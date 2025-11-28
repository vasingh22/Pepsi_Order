from pathlib import Path
from typing import List, Optional, Dict, Any

from surya.ocr import run_ocr
from surya.input.load import load_pdf
from surya.model.detection.model import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor
from PIL import Image

from app.schemas import OCRResult as AppOCRResult, Page, Block


class SuryaOCRService:
    """Service for performing OCR on PDF documents using Surya OCR."""

    def __init__(self, default_languages: List[str] = None):
        """
        Initialize the OCR service.

        Args:
            default_languages: List of language codes (e.g., ["en", "hi"])
        """
        self.default_languages = default_languages or ["en"]
        self._det_model = None
        self._det_processor = None
        self._rec_model = None
        self._rec_processor = None

    @property
    def det_model(self):
        """Lazy load detection model."""
        if self._det_model is None:
            self._det_model = load_det_model()
        return self._det_model

    @property
    def det_processor(self):
        """Lazy load detection processor."""
        if self._det_processor is None:
            self._det_processor = load_det_processor()
        return self._det_processor

    @property
    def rec_model(self):
        """Lazy load recognition model."""
        if self._rec_model is None:
            self._rec_model = load_rec_model()
        return self._rec_model

    @property
    def rec_processor(self):
        """Lazy load recognition processor."""
        if self._rec_processor is None:
            self._rec_processor = load_rec_processor()
        return self._rec_processor

    def extract_from_pdf(
        self,
        pdf_path: Path,
        languages: Optional[List[str]] = None,
        include_raw: bool = False,
    ) -> AppOCRResult:
        """
        Extract text from a PDF file using Surya OCR.

        Args:
            pdf_path: Path to the PDF file
            languages: List of language codes. If None, uses default_languages.
            include_raw: Whether to include raw Surya response in the result

        Returns:
            OCRResult containing extracted text and metadata
        """
        if languages is None:
            languages = self.default_languages

        # Load PDF images
        images, image_names = load_pdf(str(pdf_path))

        # Prepare languages - one list per image
        langs_per_image = [languages] * len(images)

        # Run OCR
        predictions = run_ocr(
            images,
            langs=langs_per_image,
            det_model=self.det_model,
            det_processor=self.det_processor,
            rec_model=self.rec_model,
            rec_processor=self.rec_processor,
        )

        # Build pages
        pages = []
        raw_response = {"predictions": []} if include_raw else None

        for idx, (image, prediction) in enumerate(zip(images, predictions), start=1):
            # Extract text from all text lines
            text_lines = []
            for text_line in prediction.text_lines:
                text_lines.append(text_line.text)

            full_text = "\n".join(text_lines)

            # Get image dimensions
            if isinstance(image, Image.Image):
                width, height = image.size
            else:
                width = getattr(image, 'width', 0)
                height = getattr(image, 'height', 0)

            # Build blocks from text lines
            blocks = []
            for line_idx, text_line in enumerate(prediction.text_lines):
                # Extract polygon (bbox) and confidence
                polygon = list(text_line.polygon) if hasattr(text_line, 'polygon') and text_line.polygon is not None else [0, 0, 0, 0, 0, 0, 0, 0]
                # Convert polygon to bbox (min/max x/y)
                if len(polygon) >= 8:
                    x_coords = [polygon[i] for i in range(0, 8, 2)]
                    y_coords = [polygon[i] for i in range(1, 8, 2)]
                    bbox = [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
                    # Calculate relative bbox
                    bbox_rel = [bbox[0] / width if width > 0 else 0, 
                               bbox[1] / height if height > 0 else 0,
                               bbox[2] / width if width > 0 else 0,
                               bbox[3] / height if height > 0 else 0]
                else:
                    bbox = [0, 0, 0, 0]
                    bbox_rel = [0, 0, 0, 0]
                
                confidence = float(text_line.confidence) if hasattr(text_line, 'confidence') and text_line.confidence is not None else 1.0

                block = Block(
                    block_id=f"p{idx}-l{line_idx}",
                    block_type="line",
                    text=text_line.text,
                    confidence=confidence,
                    bbox=bbox,
                    bbox_rel=bbox_rel,
                    page=idx,
                    reading_order=line_idx + 1,
                )
                blocks.append(block)

            page = Page(
                page_number=idx,
                text=full_text,
                width=width,
                height=height,
                blocks=blocks,
            )
            pages.append(page)

            if include_raw:
                raw_response["predictions"].append({
                    "page": idx,
                    "text_lines": [
                        {
                            "text": tl.text,
                            "polygon": list(tl.polygon) if hasattr(tl, 'polygon') and tl.polygon is not None else None,
                            "confidence": float(tl.confidence) if hasattr(tl, 'confidence') and tl.confidence is not None else None,
                        }
                        for tl in prediction.text_lines
                    ],
                    "languages": list(prediction.languages) if hasattr(prediction, 'languages') else languages,
                    "image_bbox": list(prediction.image_bbox) if hasattr(prediction, 'image_bbox') else [0, 0, width, height],
                })

        return AppOCRResult(
            filename=pdf_path.name,
            pages=pages,
            raw_response=raw_response if include_raw else None,
        )

