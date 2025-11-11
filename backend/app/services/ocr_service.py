from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Iterable, List, Optional, Tuple, Literal, Set

from surya.input.langs import get_unique_langs, replace_lang_with_code
from surya.input.load import load_pdf
from surya.model.detection.model import (
    load_model as load_detection_model,
    load_processor as load_detection_processor,
)
from surya.model.recognition.model import load_model as load_recognition_model
from surya.model.recognition.processor import load_processor as load_recognition_processor
from surya.model.recognition.tokenizer import _tokenize
from surya.ocr import run_ocr as surya_run_ocr
from surya.schema import OCRResult as SuryaOCRResult, TextLine

from app.config import get_settings
from app.schemas import (
    OCRAnchor,
    OCRBlock,
    OCRPage,
    OCRResult,
    OCRDocumentHints,
    OCRTable,
    OCRTableCell,
    OCRToken,
    CandidateEvidence,
    FieldCandidate,
    OCRZone,
    DocumentAnomaly,
    DocumentFingerprint,
    MasterDataSummary,
    NormalizationSummary,
)
from app.utils.normalization import normalize_document

logger = logging.getLogger(__name__)


class SuryaOCRService:
    """Service wrapper around the Surya OCR pipeline that normalises output."""

    def __init__(self, default_languages: Optional[List[str]] = None):
        self._settings = get_settings()
        self._default_languages = default_languages or self._settings.default_languages

        self._det_model = None
        self._det_processor = None
        self._det_lock = Lock()

        self._rec_processor = None
        self._rec_model_cache: Dict[Tuple[str, ...], object] = {}
        self._rec_lock = Lock()
        self._master_data = self._load_master_data()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def extract_from_pdf(
        self, pdf_path: Path, languages: Optional[List[str]] = None, include_raw: bool = False
    ) -> OCRResult:
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        images, _page_names = load_pdf(str(pdf_path))
        if not images:
            raise ValueError(f"No pages found in PDF: {pdf_path}")

        language_codes = self._prepare_languages(languages)
        image_langs = [language_codes.copy() for _ in range(len(images))]

        det_model, det_processor = self._get_detection_components()
        rec_model, rec_processor = self._get_recognition_components(language_codes)

        logger.info(
            "Running Surya OCR on %s (%d pages) with languages=%s",
            pdf_path,
            len(images),
            ",".join(language_codes),
        )

        surya_results = surya_run_ocr(
            images,
            image_langs,
            det_model,
            det_processor,
            rec_model,
            rec_processor,
        )

        page_sizes = [image.size for image in images]

        pages, document_tokens, block_map = self._normalise_pages(surya_results, page_sizes)
        doc_stats = self._apply_token_hints(document_tokens)
        full_text = "\n\n".join(page.text for page in pages if page.text)

        raw_payload: Any | None = None
        if include_raw:
            raw_payload = self._ensure_json_serialisable(
                [result.model_dump() for result in surya_results]
            )

        zones, zones_by_page = self._build_zones(page_sizes)
        anchors = self._detect_anchors(
            pages=pages,
            document_tokens=document_tokens,
            zones_by_page=zones_by_page,
            page_sizes=page_sizes,
        )
        tables = self._detect_tables(
            pages=pages,
            block_map=block_map,
            page_sizes=page_sizes,
        )
        candidates = self._extract_field_candidates(
            anchors=anchors,
            pages=pages,
            document_tokens=document_tokens,
        )
        document_hints = self._compute_document_hints(doc_stats)
        normalized: NormalizationSummary | None = normalize_document(
            candidates=candidates or {},
            hints=document_hints,
            tables=tables or None,
        )
        fingerprint = self._build_fingerprint(
            hints=document_hints,
            candidates=candidates,
            pages=pages,
        )
        anomalies = self._detect_anomalies(
            anchors=anchors,
            tables=tables,
            candidates=candidates,
        )

        return OCRResult(
            filename=pdf_path.name,
            pages=pages,
            full_text=full_text,
            tokens=document_tokens or None,
            zones=zones or None,
            anchors=anchors or None,
            tables=tables or None,
            candidates=candidates or None,
            hints=document_hints,
            normalized=normalized,
            fingerprint=fingerprint,
            master_data=self._master_data if self._master_data else None,
            anomalies=anomalies or None,
            raw_response=raw_payload,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _prepare_languages(self, languages: Optional[List[str]]) -> List[str]:
        cleaned = [lang.strip() for lang in (languages or self._default_languages) if lang.strip()]
        if not cleaned:
            cleaned = self._default_languages.copy()
        replace_lang_with_code(cleaned)
        return cleaned

    def _get_detection_components(self):
        if self._det_model and self._det_processor:
            return self._det_model, self._det_processor

        with self._det_lock:
            if self._det_model and self._det_processor:
                return self._det_model, self._det_processor

            logger.info("Loading Surya detection model and processor...")
            self._det_processor = load_detection_processor()
            self._det_model = load_detection_model()
            return self._det_model, self._det_processor

    def _get_recognition_components(self, language_codes: List[str]):
        key = tuple(language_codes)
        if key in self._rec_model_cache and self._rec_processor:
            return self._rec_model_cache[key], self._rec_processor

        with self._rec_lock:
            if self._rec_processor is None:
                logger.info("Loading Surya recognition processor...")
                self._rec_processor = load_recognition_processor()

            if key not in self._rec_model_cache:
                logger.info("Loading Surya recognition model for languages=%s", ",".join(language_codes))
                _, lang_tokens = _tokenize("", get_unique_langs([language_codes]))
                self._rec_model_cache[key] = load_recognition_model(langs=lang_tokens)

        return self._rec_model_cache[key], self._rec_processor

    def _normalise_pages(
        self, surya_results: Iterable[SuryaOCRResult], page_sizes: List[Tuple[int, int]]
    ) -> Tuple[List[OCRPage], List[OCRToken], Dict[str, OCRBlock]]:
        pages: List[OCRPage] = []
        all_tokens: List[OCRToken] = []
        reading_order = 0
        block_map: Dict[str, OCRBlock] = {}

        for page_index, (result, size) in enumerate(zip(surya_results, page_sizes), start=1):
            width, height = size
            page_tokens: List[OCRToken] = []
            blocks: List[OCRBlock] = []
            page_text_lines: List[str] = []

            for line_index, line in enumerate(result.text_lines):
                line_text = (line.text or "").strip()
                page_text_lines.append(line_text)

                bbox_abs = self._extract_bbox(line)
                bbox_rel = self._to_relative_bbox(bbox_abs, width, height)
                block_id = f"p{page_index}-l{line_index}"

                reading_order += 1
                line_token = OCRToken(
                    id=f"{block_id}-line",
                    text=line_text,
                    confidence=line.confidence,
                    bbox=bbox_abs,
                    bbox_rel=bbox_rel,
                    page=page_index,
                    reading_order=reading_order,
                    token_type="line",
                    engine="surya",
                    block_id=block_id,
                )

                block_tokens: List[OCRToken] = [line_token]

                words = self._split_words(line_text)
                for word_index, word in enumerate(words):
                    reading_order += 1
                    word_token = OCRToken(
                        id=f"{block_id}-w{word_index}",
                        text=word,
                        confidence=line.confidence,
                        bbox=bbox_abs,
                        bbox_rel=bbox_rel,
                        page=page_index,
                        reading_order=reading_order,
                        token_type="word",
                        engine="surya",
                        block_id=block_id,
                        order_in_block=word_index,
                    )
                    block_tokens.append(word_token)

                block = OCRBlock(
                    block_id=block_id,
                    block_type="line",
                    text=line_text,
                    confidence=line.confidence,
                    bbox=bbox_abs,
                    bbox_rel=bbox_rel,
                    page=page_index,
                    reading_order=line_token.reading_order,
                    tokens=block_tokens,
                )

                blocks.append(block)
                block_map[block_id] = block

                page_tokens.extend(block_tokens)
                all_tokens.extend(block_tokens)

            page_text = "\n".join(filter(None, page_text_lines))
            pages.append(
                OCRPage(
                    page_number=page_index,
                    text=page_text,
                    width=width,
                    height=height,
                    blocks=blocks or None,
                    tokens=page_tokens or None,
                )
            )

        if not pages:
            pages.append(OCRPage(page_number=1, text="", blocks=None, tokens=None))

        return pages, all_tokens, block_map

    @staticmethod
    def _extract_bbox(line: TextLine) -> List[float]:
        bbox = getattr(line, "bbox", None)
        if not bbox:
            return [0.0, 0.0, 0.0, 0.0]
        return [float(value) for value in bbox]

    @staticmethod
    def _to_relative_bbox(bbox: List[float], width: int, height: int) -> List[float]:
        if not width or not height:
            return [0.0, 0.0, 0.0, 0.0]
        x1, y1, x2, y2 = bbox
        return [
            max(0.0, min(1.0, x1 / width)),
            max(0.0, min(1.0, y1 / height)),
            max(0.0, min(1.0, x2 / width)),
            max(0.0, min(1.0, y2 / height)),
        ]

    @staticmethod
    def _split_words(text: str) -> List[str]:
        if not text:
            return []
        return re.findall(r"\S+", text)

    def _apply_token_hints(self, tokens: List[OCRToken]) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
            "currency_glyphs": set(),
            "date_counts": {"day_first": 0, "month_first": 0, "ambiguous": 0},
            "numbering": {"indian": 0, "international": 0},
        }

        money_symbol_pattern = re.compile(r"^(?P<symbol>[₹$€£])\s*\d")
        money_word_pattern = re.compile(r"^(rs\.?|inr|usd|eur|gbp|aud|cad)$", re.IGNORECASE)
        money_numeric_pattern = re.compile(r"^[\d,]+(?:\.\d+)?$")
        date_separators_pattern = re.compile(r"(?P<d>\d{1,2})[\/\-](?P<m>\d{1,2})[\/\-](?P<y>\d{2,4})$")
        iso_date_pattern = re.compile(r"^\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2}$")
        indian_number_pattern = re.compile(r"^\d{1,2}(,\d{2})+(?:\.\d+)?$")
        international_number_pattern = re.compile(r"^\d{1,3}(,\d{3})+(?:\.\d+)?$")

        for token in tokens:
            text = (token.text or "").strip()
            if not text:
                continue
            hints: Dict[str, Any] = {}

            money_symbol_match = money_symbol_pattern.match(text)
            if money_symbol_match or money_word_pattern.match(text):
                symbol = money_symbol_match.group("symbol") if money_symbol_match else ""
                if symbol:
                    stats["currency_glyphs"].add(symbol)
                hints["maybe"] = "money"
                hints["pattern"] = text
                if symbol:
                    hints["glyph"] = symbol
                token.hints = hints
                continue

            if "₹" in text or "$" in text or "€" in text or "£" in text:
                hints["maybe"] = "money"
                hints["pattern"] = text
                glyphs = [glyph for glyph in ["₹", "$", "€", "£"] if glyph in text]
                if glyphs:
                    stats["currency_glyphs"].update(glyphs)
                    hints["glyph"] = glyphs[0]
                token.hints = hints
                continue

            date_match = date_separators_pattern.match(text)
            if date_match:
                day = int(date_match.group("d"))
                month = int(date_match.group("m"))
                year = date_match.group("y")
                hints["maybe"] = "date"
                hints["pattern"] = text
                if day > 12 and month <= 12:
                    stats["date_counts"]["day_first"] += 1
                    hints["day_first_conf"] = 1.0
                elif month > 12 and day <= 12:
                    stats["date_counts"]["month_first"] += 1
                    hints["day_first_conf"] = 0.0
                else:
                    stats["date_counts"]["ambiguous"] += 1
                token.hints = hints
                continue

            if iso_date_pattern.match(text):
                hints["maybe"] = "date"
                hints["pattern"] = text
                hints["format"] = "iso"
                token.hints = hints
                continue

            if indian_number_pattern.match(text):
                stats["numbering"]["indian"] += 1
                hints["maybe"] = "number"
                hints["numbering_style"] = "indian"
                hints["pattern"] = text
                token.hints = hints
                continue

            if international_number_pattern.match(text):
                stats["numbering"]["international"] += 1
                hints["maybe"] = "number"
                hints["numbering_style"] = "international"
                hints["pattern"] = text
                token.hints = hints
                continue

            if money_numeric_pattern.match(text) and "," in text:
                hints["maybe"] = "number"
                hints["pattern"] = text
                token.hints = hints

        return stats
    def _build_zones(
        self, page_sizes: List[Tuple[int, int]], header_ratio: float = 0.2, footer_ratio: float = 0.15
    ) -> Tuple[List[OCRZone], Dict[int, List[OCRZone]]]:
        zones: List[OCRZone] = []
        zones_by_page: Dict[int, List[OCRZone]] = {}

        for page_index, (width, height) in enumerate(page_sizes, start=1):
            if width <= 0 or height <= 0:
                continue

            header_height = int(height * header_ratio)
            footer_height = int(height * footer_ratio)
            header_height = min(header_height, height)
            footer_height = min(footer_height, height - header_height)
            body_top = header_height
            body_bottom = max(body_top, height - footer_height)

            page_zones: List[OCRZone] = []

            zone_defs = [
                ("header", [0.0, 0.0, float(width), float(header_height)]),
                (
                    "body",
                    [0.0, float(body_top), float(width), float(body_bottom)],
                ),
                (
                    "footer",
                    [0.0, float(body_bottom), float(width), float(height)],
                ),
            ]

            for zone_type, bbox_abs in zone_defs:
                if bbox_abs[3] - bbox_abs[1] <= 0:
                    continue
                bbox_rel = self._to_relative_bbox(bbox_abs, width, height)
                zone = OCRZone(
                    zone_id=f"p{page_index}-{zone_type}",
                    zone_type=zone_type,  # type: ignore[arg-type]
                    page=page_index,
                    bbox=bbox_abs,
                    bbox_rel=bbox_rel,
                )
                zones.append(zone)
                page_zones.append(zone)

            zones_by_page[page_index] = page_zones

        return zones, zones_by_page

    def _detect_anchors(
        self,
        pages: List[OCRPage],
        document_tokens: List[OCRToken],
        zones_by_page: Dict[int, List[OCRZone]],
        page_sizes: List[Tuple[int, int]],
        context_window_px: int = 300,
    ) -> List[OCRAnchor]:
        anchors: List[OCRAnchor] = []
        anchor_patterns = self._anchor_patterns()

        for page in pages:
            if not page.blocks:
                continue
            width = page.width or page_sizes[page.page_number - 1][0]
            height = page.height or page_sizes[page.page_number - 1][1]

            page_tokens = page.tokens or []
            for block in page.blocks:
                label = self._match_anchor_label(block.text, anchor_patterns)
                if not label:
                    continue

                bbox_abs = block.bbox or [0.0, 0.0, 0.0, 0.0]
                bbox_rel = block.bbox_rel or self._to_relative_bbox(bbox_abs, width, height)
                token_ids = [token.id for token in (block.tokens or [])]

                context_token_ids = self._gather_context_tokens(
                    page_tokens=page_tokens,
                    anchor_bbox=bbox_abs,
                    context_window_px=context_window_px,
                    anchor_token_ids=set(token_ids),
                )

                zone_type = self._zone_type_for_bbox(
                    zones_by_page.get(page.page_number, []),
                    bbox_abs,
                )

                anchor_id = f"p{page.page_number}-a{len(anchors)+1}"
                anchor_text = block.text or ""
                anchors.append(
                    OCRAnchor(
                        anchor_id=anchor_id,
                        label=label,
                        text=anchor_text,
                        page=page.page_number,
                        bbox=bbox_abs,
                        bbox_rel=bbox_rel,
                        zone_type=zone_type,
                        token_ids=token_ids,
                        context_token_ids=context_token_ids,
                        context_window_px=context_window_px,
                    )
                )

        return anchors

    def _detect_tables(
        self,
        pages: List[OCRPage],
        block_map: Dict[str, OCRBlock],
        page_sizes: List[Tuple[int, int]],
    ) -> List[OCRTable]:
        tables: List[OCRTable] = []

        for page in pages:
            blocks = page.blocks or []
            if not blocks:
                continue
            candidate_runs: List[List[OCRBlock]] = []
            current_run: List[OCRBlock] = []

            for block in blocks:
                text = block.text.strip() if block.text else ""
                if self._is_table_line(text):
                    current_run.append(block)
                else:
                    if current_run:
                        candidate_runs.append(current_run)
                        current_run = []
            if current_run:
                candidate_runs.append(current_run)

            page_tables: List[OCRTable] = []
            for run_index, run_blocks in enumerate(candidate_runs):
                if len(run_blocks) < 2:
                    continue
                table = self._build_table_from_blocks(
                    page=page,
                    run_blocks=run_blocks,
                    table_index=len(page_tables) + 1,
                    page_sizes=page_sizes,
                )
                if table:
                    page_tables.append(table)
                    tables.append(table)

            if page_tables:
                page.tables = (page.tables or []) + page_tables

        return tables

    @staticmethod
    def _anchor_patterns() -> Dict[str, List[re.Pattern[str]]]:
        anchor_map = {
            "po_number": [
                r"\bpo[\s\-]*no\b",
                r"\bpurchase\s+order\b",
            ],
            "po_date": [
                r"\bpo[\s\-]*date\b",
                r"\border\s+date\b",
            ],
            "order_reference": [
                r"\border\s+ref(erence)?\b",
                r"\border\s+id\b",
            ],
            "bill_to": [
                r"\bbill\s*to\b",
                r"\binvoicee\b",
            ],
            "ship_to": [
                r"\bship\s*to\b",
                r"\bdelivery\s+address\b",
            ],
            "vendor": [
                r"\bvendor\b",
                r"\bsupplier\b",
            ],
            "invoice_number": [
                r"\binvoice\s*no\b",
                r"\binvoice\s+number\b",
            ],
            "invoice_date": [
                r"\binvoice\s*date\b",
            ],
            "total": [
                r"\b(total|grand\s+total)\b",
            ],
            "subtotal": [
                r"\bsub\s*total\b",
            ],
            "tax": [
                r"\btax\b",
                r"\bgst\b",
            ],
        }
        compiled: Dict[str, List[re.Pattern[str]]] = {}
        for label, patterns in anchor_map.items():
            compiled[label] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        return compiled

    @staticmethod
    def _match_anchor_label(
        text: Optional[str], anchor_patterns: Dict[str, List[re.Pattern[str]]]
    ) -> Optional[str]:
        if not text:
            return None
        for label, patterns in anchor_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    return label
        return None

    @staticmethod
    def _gather_context_tokens(
        page_tokens: List[OCRToken],
        anchor_bbox: List[float],
        context_window_px: int,
        anchor_token_ids: set[str],
    ) -> List[str]:
        x1, y1, x2, y2 = anchor_bbox
        context_x2 = x2 + context_window_px
        context_y2 = y2 + context_window_px

        context_ids: List[str] = []
        for token in page_tokens:
            if token.id in anchor_token_ids:
                continue
            tx1, ty1, _, _ = token.bbox
            if tx1 >= x1 and tx1 <= context_x2 and ty1 >= y1 and ty1 <= context_y2:
                context_ids.append(token.id)
        return context_ids
    @staticmethod
    def _zone_type_for_bbox(zones: List[OCRZone], bbox: List[float]) -> Optional[Literal["header", "body", "footer"]]:
        x1, y1, x2, y2 = bbox
        anchor_cx = (x1 + x2) / 2.0
        anchor_cy = (y1 + y2) / 2.0
        for zone in zones:
            zx1, zy1, zx2, zy2 = zone.bbox
            if zx1 <= anchor_cx <= zx2 and zy1 <= anchor_cy <= zy2:
                return zone.zone_type
        return None

    @staticmethod
    def _is_table_line(text: Optional[str]) -> bool:
        if not text:
            return False
        stripped = text.strip()
        if not stripped:
            return False
        return bool(re.search(r"\s{2,}", stripped))

    def _build_table_from_blocks(
        self,
        page: OCRPage,
        run_blocks: List[OCRBlock],
        table_index: int,
        page_sizes: List[Tuple[int, int]],
    ) -> Optional[OCRTable]:
        header_block = run_blocks[0]
        header_segments = self._split_table_cells(header_block.text)
        column_count = len(header_segments)
        if column_count == 0:
            return None

        page_width = page.width or page_sizes[page.page_number - 1][0]
        page_height = page.height or page_sizes[page.page_number - 1][1]
        if page_width <= 0 or page_height <= 0:
            return None

        cells: List[OCRTableCell] = []
        header_rows = [0]
        column_headers = header_segments

        table_x1 = min(block.bbox[0] if block.bbox else page_width for block in run_blocks)
        table_y1 = min(block.bbox[1] if block.bbox else page_height for block in run_blocks)
        table_x2 = max(block.bbox[2] if block.bbox else 0 for block in run_blocks)
        table_y2 = max(block.bbox[3] if block.bbox else 0 for block in run_blocks)
        table_bbox = [float(table_x1), float(table_y1), float(table_x2), float(table_y2)]
        table_bbox_rel = self._to_relative_bbox(table_bbox, page_width, page_height)

        total_rows = len(run_blocks)
        for row_index, block in enumerate(run_blocks):
            segments = self._split_table_cells(block.text)
            segments = self._normalise_segments(segments, column_count)
            row_bbox = block.bbox or table_bbox
            row_tokens = [token.id for token in (block.tokens or [])]
            row_cells = self._build_row_cells(
                table_id=f"p{page.page_number}-t{table_index}",
                row_index=row_index,
                row_bbox=row_bbox,
                segments=segments,
                column_count=column_count,
                page_width=page_width,
                page_height=page_height,
                token_ids=row_tokens,
                is_header=row_index == 0,
            )
            cells.extend(row_cells)

        return OCRTable(
            table_id=f"p{page.page_number}-t{table_index}",
            page=page.page_number,
            bbox=table_bbox,
            bbox_rel=table_bbox_rel,
            header_rows=header_rows,
            column_headers=column_headers,
            n_rows=total_rows,
            n_cols=column_count,
            cells=cells,
        )

    @staticmethod
    def _split_table_cells(text: Optional[str]) -> List[str]:
        if not text:
            return []
        stripped = text.strip()
        if not stripped:
            return []
        return [segment.strip() for segment in re.split(r"\s{2,}", stripped) if segment.strip()]

    @staticmethod
    def _normalise_segments(segments: List[str], expected_columns: int) -> List[str]:
        if expected_columns <= 0:
            return segments
        if len(segments) == expected_columns:
            return segments
        if len(segments) < expected_columns:
            return segments + [""] * (expected_columns - len(segments))
        # Merge excess segments into the last column
        head = segments[: expected_columns - 1]
        tail = " ".join(segments[expected_columns - 1 :])
        return head + [tail]

    def _build_row_cells(
        self,
        table_id: str,
        row_index: int,
        row_bbox: List[float],
        segments: List[str],
        column_count: int,
        page_width: int,
        page_height: int,
        token_ids: List[str],
        is_header: bool,
    ) -> List[OCRTableCell]:
        cells: List[OCRTableCell] = []
        x1, y1, x2, y2 = row_bbox
        row_width = max(x2 - x1, 1.0)
        total_chars = sum(max(len(segment), 1) for segment in segments) or column_count

        cumulative = 0
        for col_index, segment in enumerate(segments):
            segment_char_count = max(len(segment), 1)
            start_ratio = cumulative / total_chars
            cumulative += segment_char_count
            end_ratio = cumulative / total_chars

            cell_x1 = x1 + row_width * start_ratio
            cell_x2 = x1 + row_width * end_ratio
            cell_bbox = [float(cell_x1), float(y1), float(cell_x2), float(y2)]
            cell_bbox_rel = self._to_relative_bbox(cell_bbox, page_width, page_height)
            hints: Dict[str, Any] = {}
            if not segment.strip():
                hints["empty"] = True

            cell = OCRTableCell(
                cell_id=f"{table_id}-r{row_index}c{col_index}",
                row=row_index,
                column=col_index,
                text=segment,
                bbox=cell_bbox,
                bbox_rel=cell_bbox_rel,
                row_span=1,
                column_span=1,
                is_header=is_header,
                token_ids=token_ids,
                hints=hints,
            )
            cells.append(cell)
        return cells

    @staticmethod
    def _ensure_json_serialisable(payload: Any) -> Any:
        try:
            json.dumps(payload)
            return payload
        except TypeError:
            return json.loads(json.dumps(payload, default=str))

    def _compute_document_hints(self, stats: Dict[str, Any]) -> OCRDocumentHints:
        day_first_count = stats["date_counts"]["day_first"]
        month_first_count = stats["date_counts"]["month_first"]
        ambiguous_count = stats["date_counts"]["ambiguous"]
        denominator = day_first_count + month_first_count + ambiguous_count
        day_first_prob: Optional[float] = None
        if denominator:
            day_first_prob = (day_first_count + 0.5 * ambiguous_count) / float(denominator)

        numbering = stats["numbering"]
        numbering_style: Optional[str] = None
        if numbering["indian"] or numbering["international"]:
            numbering_style = (
                "indian"
                if numbering["indian"] >= numbering["international"]
                else "international"
            )

        currency_glyphs = sorted(stats["currency_glyphs"])

        return OCRDocumentHints(
            day_first_prob=day_first_prob,
            numbering_style=numbering_style,
            currency_glyphs=currency_glyphs,
        )

    def _extract_field_candidates(
        self,
        anchors: List[OCRAnchor],
        pages: List[OCRPage],
        document_tokens: List[OCRToken],
    ) -> Dict[str, List[FieldCandidate]]:
        if not anchors and not document_tokens:
            return {}

        token_lookup: Dict[str, OCRToken] = {token.id: token for token in document_tokens}
        field_candidates: Dict[str, List[FieldCandidate]] = {}

        for anchor in anchors:
            field = self._anchor_label_to_field(anchor.label)
            if not field:
                continue
            candidate = self._build_candidate_from_anchor(
                field=field,
                anchor=anchor,
                token_lookup=token_lookup,
            )
            if candidate:
                field_candidates.setdefault(field, []).append(candidate)

        if "currency" not in field_candidates:
            currency_candidates = self._derive_currency_candidates(token_lookup)
            if currency_candidates:
                field_candidates["currency"] = currency_candidates

        return field_candidates

    @staticmethod
    def _anchor_label_to_field(label: str) -> Optional[str]:
        mapping = {
            "po_number": "po_number",
            "po_date": "po_date",
            "order_reference": "order_reference",
            "vendor": "vendor_name",
            "invoice_number": "invoice_number",
            "invoice_date": "invoice_date",
            "total": "grand_total",
            "subtotal": "subtotal",
            "tax": "tax_total",
            "currency": "currency",
        }
        return mapping.get(label)

    def _build_candidate_from_anchor(
        self,
        field: str,
        anchor: OCRAnchor,
        token_lookup: Dict[str, OCRToken],
    ) -> Optional[FieldCandidate]:
        candidate_text, evidence_token = self._extract_candidate_value(field, anchor, token_lookup)
        if not candidate_text:
            return None

        if evidence_token:
            bbox = evidence_token.bbox
            bbox_rel = evidence_token.bbox_rel
            token_ids = [evidence_token.id]
        else:
            bbox = anchor.bbox
            bbox_rel = anchor.bbox_rel
            token_ids = anchor.token_ids or []

        evidence = CandidateEvidence(
            page=anchor.page,
            bbox=bbox,
            bbox_rel=bbox_rel,
            anchor_id=anchor.anchor_id,
            anchor_label=anchor.label,
            token_ids=token_ids,
        )
        return FieldCandidate(value_raw=candidate_text, evidence=evidence)

    def _extract_candidate_value(
        self,
        field: str,
        anchor: OCRAnchor,
        token_lookup: Dict[str, OCRToken],
    ) -> Tuple[Optional[str], Optional[OCRToken]]:
        context_ids = list(anchor.token_ids or []) + list(anchor.context_token_ids or [])
        context_tokens = [
            token_lookup[token_id]
            for token_id in context_ids
            if token_id in token_lookup
        ]

        if field in ("po_number", "order_reference", "invoice_number"):
            value = self._find_alphanumeric(context_tokens, exclude=anchor.text)
            return value

        if field in ("po_date", "invoice_date"):
            value = self._find_date_value(context_tokens)
            return value

        if field in ("grand_total", "subtotal", "tax_total"):
            value = self._find_money_value(context_tokens)
            return value

        if field == "vendor_name":
            value = self._find_textual_value(context_tokens, min_length=3)
            return value

        if field == "currency":
            value = self._find_currency_value(context_tokens)
            return value

        return None, None

    @staticmethod
    def _find_alphanumeric(
        tokens: List[OCRToken],
        exclude: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[OCRToken]]:
        pattern = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-_/]*")
        for token in tokens:
            text = (token.text or "").strip()
            if not text or (exclude and text.lower() == exclude.lower()):
                continue
            match = pattern.search(text)
            if match:
                return match.group(0), token
        return None, None

    @staticmethod
    def _find_date_value(tokens: List[OCRToken]) -> Tuple[Optional[str], Optional[OCRToken]]:
        date_pattern = re.compile(r"\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2}")
        for token in tokens:
            text = (token.text or "").strip()
            if not text:
                continue
            if token.hints and token.hints.get("maybe") == "date":
                return text, token
            if date_pattern.match(text):
                return text, token
        return None, None

    @staticmethod
    def _find_money_value(tokens: List[OCRToken]) -> Tuple[Optional[str], Optional[OCRToken]]:
        money_pattern = re.compile(r"[₹$€£]?\s?[\d,]+(?:\.\d+)?")
        for token in tokens:
            text = (token.text or "").strip()
            if not text:
                continue
            if token.hints and token.hints.get("maybe") == "money":
                return text, token
            match = money_pattern.match(text)
            if match and re.search(r"\d", match.group(0)):
                return match.group(0), token
        return None, None

    @staticmethod
    def _find_textual_value(tokens: List[OCRToken], min_length: int = 3) -> Tuple[Optional[str], Optional[OCRToken]]:
        for token in tokens:
            text = (token.text or "").strip()
            if len(text) >= min_length and re.search(r"[A-Za-z]", text):
                return text, token
        return None, None

    @staticmethod
    def _find_currency_value(tokens: List[OCRToken]) -> Tuple[Optional[str], Optional[OCRToken]]:
        currency_words = {"inr", "rs", "usd", "eur", "gbp", "cad", "aud"}
        for token in tokens:
            text = (token.text or "").strip()
            if not text:
                continue
            if token.hints and token.hints.get("maybe") == "money" and "glyph" in token.hints:
                return token.hints["glyph"], token
            if text.lower() in currency_words:
                return text.upper(), token
        return None, None

    def _derive_currency_candidates(
        self,
        token_lookup: Dict[str, OCRToken],
    ) -> List[FieldCandidate]:
        candidates: List[FieldCandidate] = []
        seen_values: Set[str] = set()
        for token in token_lookup.values():
            if not token.hints:
                continue
            if token.hints.get("maybe") != "money":
                continue
            value = token.hints.get("glyph") or token.text.strip()
            if not value or value in seen_values:
                continue
            seen_values.add(value)
            evidence = CandidateEvidence(
                page=token.page,
                bbox=token.bbox,
                bbox_rel=token.bbox_rel,
                anchor_id=None,
                anchor_label=None,
                token_ids=[token.id],
            )
            candidates.append(FieldCandidate(value_raw=value, evidence=evidence))
        return candidates

    def _load_master_data(self) -> Optional[MasterDataSummary]:
        vendor_aliases = self._load_alias_file(self._settings.vendor_master_path)
        sku_aliases = self._load_alias_file(self._settings.sku_master_path)
        uom_aliases = self._load_alias_file(self._settings.uom_master_path)

        if not any([vendor_aliases, sku_aliases, uom_aliases]):
            return None

        return MasterDataSummary(
            vendor_aliases=vendor_aliases or {},
            sku_aliases=sku_aliases or {},
            uom_aliases=uom_aliases or {},
        )

    @staticmethod
    def _load_alias_file(path: Optional[Path]) -> Optional[Dict[str, List[str]]]:
        if not path:
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                normalised: Dict[str, List[str]] = {}
                for key, value in data.items():
                    if isinstance(value, list):
                        normalised[str(key)] = [str(item) for item in value]
                    else:
                        normalised[str(key)] = [str(value)]
                return normalised
        except FileNotFoundError:
            logging.warning("Master data file not found: %s", path)
        except json.JSONDecodeError:
            logging.warning("Failed to decode master data file: %s", path)
        return None

    def _build_fingerprint(
        self,
        hints: OCRDocumentHints,
        candidates: Dict[str, List[FieldCandidate]],
        pages: List[OCRPage],
    ) -> DocumentFingerprint:
        vendor_guess = None
        if candidates.get("vendor_name"):
            vendor_guess = candidates["vendor_name"][0].value_raw

        first_page_text = "\n".join(page.text for page in pages[:1])
        layout_signature = hashlib.sha256(first_page_text.encode("utf-8")).hexdigest()[:16]

        languages = self._default_languages
        return DocumentFingerprint(
            vendor_guess=vendor_guess,
            layout_signature=layout_signature,
            languages=languages,
            currency_glyphs=hints.currency_glyphs if hints and hints.currency_glyphs else [],
            numbering_style=hints.numbering_style if hints else None,
        )

    def _detect_anomalies(
        self,
        anchors: List[OCRAnchor],
        tables: List[OCRTable],
        candidates: Dict[str, List[FieldCandidate]],
    ) -> List[DocumentAnomaly]:
        anomalies: List[DocumentAnomaly] = []

        anchor_labels = [anchor.label for anchor in anchors]
        for label in set(anchor_labels):
            occurrences = anchor_labels.count(label)
            if occurrences > 3:
                anomalies.append(
                    DocumentAnomaly(
                        code="anchor_excess",
                        message=f"Anchor '{label}' detected {occurrences} times.",
                        page=None,
                    )
                )

        for table in tables:
            if table.n_cols <= 1:
                anomalies.append(
                    DocumentAnomaly(
                        code="table_low_confidence",
                        message=f"Table {table.table_id} has {table.n_cols} columns; verify layout.",
                        page=table.page,
                    )
                )

        totals_present = any(field in candidates for field in ("grand_total", "subtotal"))
        if not totals_present:
            anomalies.append(
                DocumentAnomaly(
                    code="totals_missing",
                    message="No subtotal or grand total candidates identified.",
                    page=None,
                )
            )

        return anomalies

