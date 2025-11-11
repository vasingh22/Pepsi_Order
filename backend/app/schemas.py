from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class OCRTokenVariant(BaseModel):
    engine: str = Field(..., description="Identifier of the OCR engine that produced this variant.")
    text: str = Field(..., description="Variant text emitted by the OCR engine.")
    confidence: Optional[float] = Field(
        default=None, description="Confidence score reported by the OCR engine for this variant."
    )


class OCRToken(BaseModel):
    id: str = Field(..., description="Stable identifier for the token within the document.")
    text: str = Field(..., description="Token text as emitted by the OCR engine.")
    confidence: Optional[float] = Field(
        default=None, description="Confidence score reported by the OCR engine."
    )
    bbox: List[float] = Field(
        ...,
        description="Absolute bounding box [x1, y1, x2, y2] in image pixels.",
        min_items=4,
        max_items=4,
    )
    bbox_rel: List[float] = Field(
        ...,
        description="Bounding box normalized to page width/height (values in [0,1]).",
        min_items=4,
        max_items=4,
    )
    page: int = Field(..., ge=1, description="Page number (1-indexed) that contains the token.")
    reading_order: int = Field(
        ..., ge=0, description="Document-level reading order index for deterministic traversal."
    )
    token_type: Literal["line", "word"] = Field(
        default="word", description="Semantic type of the token."
    )
    engine: str = Field(default="surya", description="Primary OCR engine that produced the token.")
    block_id: Optional[str] = Field(
        default=None, description="Identifier of the parent block/line this token belongs to."
    )
    order_in_block: Optional[int] = Field(
        default=None,
        ge=0,
        description="Position of the token within its parent block (if applicable).",
    )
    variants: Optional[List[OCRTokenVariant]] = Field(
        default=None,
        description="Per-engine alternative transcriptions for this token (when multiple OCR engines are used).",
    )
    hints: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Lightweight hints about the token (e.g. likely type, matched pattern).",
    )


class OCRBlock(BaseModel):
    block_id: str = Field(..., description="Stable identifier for the block.")
    block_type: Optional[str] = Field(
        default=None, description="Type/category of the detected block (paragraph, table, etc.)."
    )
    text: str = Field(..., description="Text extracted for the block.")
    confidence: Optional[float] = Field(
        default=None, description="Confidence score reported by the OCR engine, if available."
    )
    bbox: Optional[List[float]] = Field(
        default=None,
        description="Bounding box coordinates reported by OCR engine, if available.",
    )
    bbox_rel: Optional[List[float]] = Field(
        default=None,
        description="Bounding box normalised to page width/height (values in [0,1]).",
    )
    page: Optional[int] = Field(
        default=None,
        ge=1,
        description="Page number (1-indexed) on which this block was detected.",
    )
    reading_order: Optional[int] = Field(
        default=None,
        ge=0,
        description="Reading order index for the block within the document.",
    )
    tokens: Optional[List[OCRToken]] = Field(
        default=None,
        description="Word/line tokens associated with this block.",
    )


class OCRPage(BaseModel):
    page_number: int = Field(..., ge=1, description="Page number starting at 1.")
    text: str = Field(..., description="Full text for the page, concatenated from blocks.")
    width: Optional[int] = Field(
        default=None, description="Page width in pixels, used for normalised calculations."
    )
    height: Optional[int] = Field(
        default=None, description="Page height in pixels, used for normalised calculations."
    )
    blocks: Optional[List[OCRBlock]] = Field(
        default=None,
        description="Structured blocks detected for the page, when available.",
    )
    tokens: Optional[List[OCRToken]] = Field(
        default=None,
        description="Flattened list of tokens present on this page, in reading order.",
    )


class OCRZone(BaseModel):
    zone_id: str = Field(..., description="Stable identifier for the zone.")
    zone_type: Literal["header", "body", "footer"] = Field(
        ..., description="Semantic label for the zone."
    )
    page: int = Field(..., ge=1, description="Page number (1-indexed) containing this zone.")
    bbox: List[float] = Field(
        ...,
        description="Absolute bounding box [x1, y1, x2, y2] in image pixels.",
        min_items=4,
        max_items=4,
    )
    bbox_rel: List[float] = Field(
        ...,
        description="Bounding box normalised to page width/height (values in [0,1]).",
        min_items=4,
        max_items=4,
    )


class OCRAnchor(BaseModel):
    anchor_id: str = Field(..., description="Stable identifier for the anchor.")
    label: str = Field(..., description="Canonical label for the anchor (e.g. 'po_number').")
    text: str = Field(..., description="Text snippet that triggered the anchor.")
    page: int = Field(..., ge=1, description="Page number containing the anchor.")
    bbox: List[float] = Field(
        ...,
        description="Absolute bounding box [x1, y1, x2, y2] in image pixels.",
        min_items=4,
        max_items=4,
    )
    bbox_rel: List[float] = Field(
        ...,
        description="Bounding box normalised to page width/height (values in [0,1]).",
        min_items=4,
        max_items=4,
    )
    zone_type: Optional[Literal["header", "body", "footer"]] = Field(
        default=None,
        description="Zone classification that contains this anchor (if determinable).",
    )
    token_ids: List[str] = Field(
        default_factory=list,
        description="Token identifiers that belong to the anchor span.",
    )
    context_token_ids: List[str] = Field(
        default_factory=list,
        description="Tokens within the configured context window (e.g. 300px right/down).",
    )
    context_window_px: int = Field(
        default=300, description="Size of the context window used to gather context tokens."
    )


class OCRTableCell(BaseModel):
    cell_id: str = Field(..., description="Stable identifier for the table cell.")
    row: int = Field(..., ge=0, description="Zero-based row index within the table.")
    column: int = Field(..., ge=0, description="Zero-based column index within the table.")
    text: str = Field(..., description="Raw text content of the cell.")
    bbox: List[float] = Field(
        ...,
        description="Absolute bounding box [x1, y1, x2, y2] in image pixels.",
        min_items=4,
        max_items=4,
    )
    bbox_rel: List[float] = Field(
        ...,
        description="Bounding box normalised to page width/height (values in [0,1]).",
        min_items=4,
        max_items=4,
    )
    row_span: int = Field(default=1, ge=1, description="Row span for merged cells.")
    column_span: int = Field(default=1, ge=1, description="Column span for merged cells.")
    is_header: bool = Field(default=False, description="Whether the cell belongs to a header row.")
    token_ids: List[str] = Field(
        default_factory=list,
        description="Token identifiers associated with this cell (duplicates allowed).",
    )
    hints: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional hints (e.g., {'empty': true, 'wrap_candidate': true}).",
    )


class OCRTable(BaseModel):
    table_id: str = Field(..., description="Stable identifier for the table.")
    page: int = Field(..., ge=1, description="Page number containing the table.")
    bbox: List[float] = Field(
        ...,
        description="Absolute bounding box [x1, y1, x2, y2] encompassing the table.",
        min_items=4,
        max_items=4,
    )
    bbox_rel: List[float] = Field(
        ...,
        description="Bounding box normalised to page width/height (values in [0,1]).",
        min_items=4,
        max_items=4,
    )
    header_rows: List[int] = Field(
        default_factory=list,
        description="Zero-based indices of rows considered header rows.",
    )
    column_headers: List[str] = Field(
        default_factory=list,
        description="Column header texts inferred from the table.",
    )
    n_rows: int = Field(default=0, ge=0, description="Total number of rows detected.")
    n_cols: int = Field(default=0, ge=0, description="Total number of columns inferred.")
    cells: List[OCRTableCell] = Field(
        default_factory=list,
        description="All cells belonging to the table.",
    )

class DocumentAnomaly(BaseModel):
    code: str = Field(..., description="Machine-readable anomaly code (e.g., 'duplicate_header').")
    message: str = Field(..., description="Human-readable description of the anomaly.")
    page: Optional[int] = Field(
        default=None,
        ge=1,
        description="Page number associated with the anomaly, if applicable.",
    )

class DocumentFingerprint(BaseModel):
    vendor_guess: Optional[str] = Field(
        default=None, description="Heuristic guess of the vendor name."
    )
    layout_signature: Optional[str] = Field(
        default=None,
        description="Hash/signature representing the layout (useful for template matching).",
    )
    languages: List[str] = Field(
        default_factory=list, description="Languages detected/assumed for the document."
    )
    currency_glyphs: List[str] = Field(
        default_factory=list, description="Currency glyphs observed in the document."
    )
    numbering_style: Optional[str] = Field(
        default=None, description="Detected numbering style (e.g. 'indian', 'international')."
    )

class MasterDataSummary(BaseModel):
    vendor_aliases: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Vendor canonical names mapped to alias lists.",
    )
    sku_aliases: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="SKU canonical names mapped to alias lists.",
    )
    uom_aliases: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="UOM canonical names mapped to alias lists.",
    )

class CandidateEvidence(BaseModel):
    page: int = Field(..., ge=1, description="Page number containing the evidence.")
    bbox: List[float] = Field(
        ...,
        description="Absolute bounding box for the evidence span.",
        min_items=4,
        max_items=4,
    )
    bbox_rel: List[float] = Field(
        ...,
        description="Normalised bounding box for the evidence span.",
        min_items=4,
        max_items=4,
    )
    anchor_id: Optional[str] = Field(
        default=None, description="Anchor identifier that led to this candidate."
    )
    anchor_label: Optional[str] = Field(
        default=None, description="Anchor label that led to this candidate."
    )
    token_ids: List[str] = Field(
        default_factory=list,
        description="Tokens that back this candidate value.",
    )


class FieldCandidate(BaseModel):
    value_raw: str = Field(..., description="Raw value extracted for the field.")
    evidence: CandidateEvidence = Field(
        ..., description="Pointer to the evidence backing this candidate."
    )


class NormalizedFieldValue(BaseModel):
    raw: Optional[str] = Field(
        default=None, description="Raw value that was selected for normalisation."
    )
    normalized: Optional[str] = Field(
        default=None, description="Normalised / parsed representation of the value."
    )
    value_type: Optional[str] = Field(
        default=None, description="Detected value type (e.g. 'string', 'date', 'number', 'currency')."
    )
    parser: Optional[str] = Field(
        default=None, description="Deterministic parser identifier that produced the normalised value."
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Relative confidence in the deterministic parse (1.0 = high confidence).",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parser-specific metadata (e.g. detected format, glyph, table id).",
    )


class TotalsBreakdown(BaseModel):
    subtotal: Optional[NormalizedFieldValue] = Field(
        default=None, description="Parsed subtotal candidate (if available)."
    )
    tax_total: Optional[NormalizedFieldValue] = Field(
        default=None, description="Parsed tax total candidate (if available)."
    )
    grand_total: Optional[NormalizedFieldValue] = Field(
        default=None, description="Parsed grand total candidate (if available)."
    )
    recomputed_total: Optional[NormalizedFieldValue] = Field(
        default=None,
        description="Total recomputed from table rows or candidate arithmetic (if feasible).",
    )
    difference: Optional[float] = Field(
        default=None, description="Absolute difference between grand total and recomputed total."
    )
    status: Literal["ok", "mismatch", "insufficient", "missing"] = Field(
        default="missing",
        description="Status of totals reconciliation (ok/mismatch/insufficient/missing).",
    )
    notes: Optional[str] = Field(
        default=None, description="Additional notes about how totals were derived."
    )


class NormalizationSummary(BaseModel):
    fields: Dict[str, NormalizedFieldValue] = Field(
        default_factory=dict,
        description="Deterministically parsed fields keyed by canonical field name.",
    )
    currency: Optional[NormalizedFieldValue] = Field(
        default=None, description="Detected currency code from glyphs/candidates."
    )
    totals: Optional[TotalsBreakdown] = Field(
        default=None, description="Totals reconciliation summary."
    )


class OCRDocumentHints(BaseModel):
    day_first_prob: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Probability that dates in the document are day-first.",
    )
    numbering_style: Optional[str] = Field(
        default=None,
        description="Detected numbering style (e.g. 'indian', 'international').",
    )
    currency_glyphs: List[str] = Field(
        default_factory=list,
        description="Currency glyphs observed in the document.",
    )


class OCRResult(BaseModel):
    filename: str = Field(..., description="Name of the processed file.")
    pages: List[OCRPage] = Field(..., description="Per-page OCR results.")
    full_text: str = Field(..., description="Full text extracted from the document.")
    tokens: Optional[List[OCRToken]] = Field(
        default=None,
        description="Flattened list of tokens for the entire document in reading order.",
    )
    zones: Optional[List[OCRZone]] = Field(
        default=None, description="Header/body/footer zones detected across pages."
    )
    anchors: Optional[List[OCRAnchor]] = Field(
        default=None, description="Anchor spans detected (e.g. PO No, Order Date)."
    )
    tables: Optional[List[OCRTable]] = Field(
        default=None, description="Table skeletons detected across the document."
    )
    candidates: Optional[Dict[str, List[FieldCandidate]]] = Field(
        default=None,
        description="Candidate sets per target field with evidence pointers.",
    )
    hints: Optional[OCRDocumentHints] = Field(
        default=None,
        description="Document-level hints (date ordering, numbering style, currency glyphs, etc.).",
    )
    fingerprint: Optional[DocumentFingerprint] = Field(
        default=None,
        description="Document fingerprint used as priors for downstream tools.",
    )
    normalized: Optional[NormalizationSummary] = Field(
        default=None,
        description="Deterministic parsing output (parsed fields, detected currency, totals reconciliation).",
    )
    master_data: Optional[MasterDataSummary] = Field(
        default=None,
        description="Loaded master-data alias sets (vendor/SKU/UOM).",
    )
    anomalies: Optional[List[DocumentAnomaly]] = Field(
        default=None,
        description="Structured anomalies detected during normalization.",
    )
    raw_response: Optional[Any] = Field(
        default=None,
        description="Raw response returned by Surya OCR (included only when requested).",
    )


class SampleList(BaseModel):
    samples: List[str] = Field(
        default_factory=list,
        description="Available sample PDF filenames discovered on the server.",
    )

