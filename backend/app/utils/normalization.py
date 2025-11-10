from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, Iterable, List, Optional, Tuple

from app.schemas import (
    FieldCandidate,
    NormalizationSummary,
    NormalizedFieldValue,
    OCRDocumentHints,
    OCRTable,
    TotalsBreakdown,
)

DATE_FORMATS_DAY_FIRST = [
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%d/%m/%y",
    "%d-%m-%y",
]

DATE_FORMATS_MONTH_FIRST = [
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%m/%d/%y",
    "%m-%d-%y",
]

DATE_FORMATS_NEUTRAL = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
]

CURRENCY_GLYPH_MAP = {
    "₹": "INR",
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
}

CURRENCY_WORD_MAP = {
    "inr": "INR",
    "rs": "INR",
    "rs.": "INR",
    "usd": "USD",
    "eur": "EUR",
    "gbp": "GBP",
    "aud": "AUD",
    "cad": "CAD",
}


def normalize_document(
    candidates: Optional[Dict[str, List[FieldCandidate]]],
    hints: Optional[OCRDocumentHints],
    tables: Optional[List[OCRTable]],
) -> Optional[NormalizationSummary]:
    """Normalise key fields deterministically using helper parsers."""
    if not candidates and not tables:
        return None

    fields: Dict[str, NormalizedFieldValue] = {}

    fields.update(_normalise_identity_fields(candidates))
    fields.update(_normalise_date_fields(candidates, hints))
    numeric_fields, subtotal_value, tax_value, grand_value = _normalise_numeric_fields(
        candidates, hints
    )
    fields.update(numeric_fields)

    currency_value = _normalise_currency(candidates, hints)

    totals = _build_totals_breakdown(
        candidates=candidates,
        hints=hints,
        tables=tables,
        subtotal=subtotal_value,
        tax=tax_value,
        grand=grand_value,
    )

    if not fields and not currency_value and not totals:
        return None

    summary = NormalizationSummary(
        fields=fields,
        currency=currency_value,
        totals=totals,
    )
    return summary


def _normalise_identity_fields(
    candidates: Optional[Dict[str, List[FieldCandidate]]]
) -> Dict[str, NormalizedFieldValue]:
    identity_fields = ["po_number", "order_reference", "invoice_number", "vendor_name"]
    results: Dict[str, NormalizedFieldValue] = {}
    if not candidates:
        return results

    for field in identity_fields:
        candidate = _select_candidate(candidates.get(field))
        if not candidate:
            continue
        metadata = _candidate_metadata(candidate)
        results[field] = NormalizedFieldValue(
            raw=candidate.value_raw,
            normalized=candidate.value_raw.strip() if candidate.value_raw else None,
            value_type="string",
            parser="identity",
            confidence=1.0,
            metadata=metadata,
        )
    return results


def _normalise_date_fields(
    candidates: Optional[Dict[str, List[FieldCandidate]]],
    hints: Optional[OCRDocumentHints],
) -> Dict[str, NormalizedFieldValue]:
    date_fields = ["po_date", "invoice_date"]
    results: Dict[str, NormalizedFieldValue] = {}
    if not candidates:
        return results
    for field in date_fields:
        candidate = _select_candidate(candidates.get(field))
        if not candidate:
            continue
        parsed, confidence, metadata = _parse_date(candidate.value_raw, hints)
        metadata.update(_candidate_metadata(candidate))
        results[field] = NormalizedFieldValue(
            raw=candidate.value_raw,
            normalized=parsed,
            value_type="date" if parsed else "string",
            parser="deterministic.date",
            confidence=confidence,
            metadata=metadata,
        )
    return results


def _normalise_numeric_fields(
    candidates: Optional[Dict[str, List[FieldCandidate]]],
    hints: Optional[OCRDocumentHints],
) -> Tuple[
    Dict[str, NormalizedFieldValue], Optional[Decimal], Optional[Decimal], Optional[Decimal]
]:
    numeric_fields = ["subtotal", "tax_total", "grand_total"]
    results: Dict[str, NormalizedFieldValue] = {}
    subtotal_value: Optional[Decimal] = None
    tax_value: Optional[Decimal] = None
    grand_value: Optional[Decimal] = None

    if not candidates:
        return results, subtotal_value, tax_value, grand_value

    for field in numeric_fields:
        candidate = _select_candidate(candidates.get(field))
        if not candidate:
            continue
        metadata = _candidate_metadata(candidate)
        value, number_metadata = _parse_number(candidate.value_raw, hints)
        metadata.update(number_metadata)
        normalized_text = _decimal_to_str(value) if value is not None else None
        confidence = 1.0 if value is not None else 0.6
        results[field] = NormalizedFieldValue(
            raw=candidate.value_raw,
            normalized=normalized_text,
            value_type="number" if value is not None else "string",
            parser="deterministic.number",
            confidence=confidence,
            metadata=metadata,
        )
        if field == "subtotal":
            subtotal_value = value
        elif field == "tax_total":
            tax_value = value
        elif field == "grand_total":
            grand_value = value

    return results, subtotal_value, tax_value, grand_value


def _normalise_currency(
    candidates: Optional[Dict[str, List[FieldCandidate]]],
    hints: Optional[OCRDocumentHints],
) -> Optional[NormalizedFieldValue]:
    raw_value = None
    candidate = _select_candidate(candidates.get("currency") if candidates else None)
    if candidate:
        raw_value = candidate.value_raw
    detected_currency, metadata = _detect_currency(raw_value, hints, candidate)
    if not detected_currency and not raw_value:
        return None

    confidence = 0.9 if detected_currency else 0.5
    metadata = {**metadata}
    if candidate:
        metadata.update(_candidate_metadata(candidate))
    return NormalizedFieldValue(
        raw=raw_value,
        normalized=detected_currency,
        value_type="currency" if detected_currency else "string",
        parser="deterministic.currency",
        confidence=confidence,
        metadata=metadata,
    )


def _build_totals_breakdown(
    candidates: Optional[Dict[str, List[FieldCandidate]]],
    hints: Optional[OCRDocumentHints],
    tables: Optional[List[OCRTable]],
    subtotal: Optional[Decimal],
    tax: Optional[Decimal],
    grand: Optional[Decimal],
) -> Optional[TotalsBreakdown]:
    if not candidates and not tables:
        return None

    subtotal_field = None
    tax_field = None
    grand_field = None
    recomputed_field = None
    difference_value: Optional[float] = None
    status = "missing"
    notes = None

    if candidates:
        subtotal_field = _field_from_results("subtotal", candidates)
        tax_field = _field_from_results("tax_total", candidates)
        grand_field = _field_from_results("grand_total", candidates)

    recomputed_value, recomputed_metadata = _recompute_totals_from_tables(
        tables, hints, candidates
    )

    recompute_source = None
    if recomputed_value is not None:
        recompute_source = "table_sum"
    elif subtotal is not None and tax is not None:
        recomputed_value = subtotal + tax
        recompute_source = "subtotal_plus_tax"
        recomputed_metadata = {"source": recompute_source}

    if recomputed_value is not None:
        recomputed_field = NormalizedFieldValue(
            raw=None,
            normalized=_decimal_to_str(recomputed_value),
            value_type="number",
            parser="deterministic.total",
            confidence=0.9,
            metadata=recomputed_metadata or {"source": recompute_source},
        )

    if grand is not None:
        status = "insufficient"
        if recomputed_value is not None:
            difference = abs(grand - recomputed_value)
            difference_value = float(difference)
            threshold = Decimal("0.01")
            status = "ok" if difference <= threshold else "mismatch"
            notes = (
                f"Grand total {'matches' if status == 'ok' else 'differs from'} recomputed total."
            )

    elif any(value is not None for value in (subtotal, tax, recomputed_value)):
        status = "insufficient"

    totals = TotalsBreakdown(
        subtotal=subtotal_field,
        tax_total=tax_field,
        grand_total=grand_field,
        recomputed_total=recomputed_field,
        difference=difference_value,
        status=status,
        notes=notes,
    )

    if (
        totals.subtotal is None
        and totals.tax_total is None
        and totals.grand_total is None
        and totals.recomputed_total is None
    ):
        return None
    return totals


def _recompute_totals_from_tables(
    tables: Optional[List[OCRTable]],
    hints: Optional[OCRDocumentHints],
    candidates: Optional[Dict[str, List[FieldCandidate]]],
) -> Tuple[Optional[Decimal], Dict[str, Any]]:
    if not tables:
        return None, {}

    preferred_table_ids = _preferred_table_ids_from_candidates(candidates)

    for table in tables:
        if preferred_table_ids and table.table_id not in preferred_table_ids:
            continue
        amount_values: List[Decimal] = []
        for cell in table.cells:
            if cell.is_header or table.n_cols == 0:
                continue
            if cell.column == table.n_cols - 1:
                value, _ = _parse_number(cell.text, hints)
                if value is not None:
                    amount_values.append(value)
        if amount_values:
            total_value = sum(amount_values, start=Decimal("0"))
            metadata = {
                "source": "table_sum",
                "table_id": table.table_id,
                "row_count": len(amount_values),
            }
            return total_value, metadata
    return None, {}


def _preferred_table_ids_from_candidates(
    candidates: Optional[Dict[str, List[FieldCandidate]]]
) -> List[str]:
    if not candidates:
        return []
    table_ids: List[str] = []
    for field in ("subtotal", "tax_total", "grand_total"):
        for candidate in candidates.get(field, []):
            anchor_id = candidate.evidence.anchor_id
            if anchor_id and "-" in anchor_id:
                table_ids.append(anchor_id.split("-")[0])
    return table_ids


def _parse_date(
    raw: Optional[str],
    hints: Optional[OCRDocumentHints],
) -> Tuple[Optional[str], Optional[float], Dict[str, Any]]:
    metadata: Dict[str, Any] = {}
    if not raw:
        return None, None, metadata
    cleaned = raw.strip()
    if not cleaned:
        return None, None, metadata

    cleaned = cleaned.replace(",", " ").replace("  ", " ").strip()

    day_first_preference = hints.day_first_prob if hints else None
    if day_first_preference is not None:
        metadata["day_first_prob"] = day_first_preference

    format_candidates = list(DATE_FORMATS_DAY_FIRST)
    if day_first_preference is not None and day_first_preference < 0.5:
        format_candidates = list(DATE_FORMATS_MONTH_FIRST) + list(DATE_FORMATS_DAY_FIRST)
    else:
        format_candidates = list(DATE_FORMATS_DAY_FIRST) + list(DATE_FORMATS_MONTH_FIRST)
    format_candidates += DATE_FORMATS_NEUTRAL

    for date_format in format_candidates:
        try:
            parsed = datetime.strptime(cleaned, date_format)
            metadata["format"] = date_format
            iso_value = parsed.strftime("%Y-%m-%d")
            confidence = 0.9
            if day_first_preference is not None:
                confidence = max(day_first_preference, 1 - day_first_preference)
            return iso_value, confidence, metadata
        except ValueError:
            continue

    # Attempt relaxed parsing by normalising separators
    normalised = re.sub(r"[.\-]", "/", cleaned)
    if normalised != cleaned:
        for date_format in set(format_candidates):
            try:
                parsed = datetime.strptime(normalised, date_format.replace("-", "/").replace(".", "/"))
                metadata["format"] = date_format
                iso_value = parsed.strftime("%Y-%m-%d")
                confidence = 0.8
                return iso_value, confidence, metadata
            except ValueError:
                continue

    return None, 0.4, metadata


def _parse_number(
    raw: Optional[str],
    hints: Optional[OCRDocumentHints],
) -> Tuple[Optional[Decimal], Dict[str, Any]]:
    metadata: Dict[str, Any] = {}
    if not raw:
        return None, metadata
    text = raw.strip()
    if not text:
        return None, metadata

    metadata["raw"] = text

    # Remove currency glyphs and letters except minus sign
    cleaned = re.sub(r"[^\d,.\-]", "", text)

    if cleaned.count(",") > 0 and cleaned.count(".") > 0:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "")
            cleaned = cleaned.replace(",", ".")
            metadata["decimal_separator"] = ","
        else:
            cleaned = cleaned.replace(",", "")
            metadata["decimal_separator"] = "."
    elif cleaned.count(",") > 0 and cleaned.count(".") == 0:
        if hints and hints.numbering_style == "indian":
            cleaned = cleaned.replace(",", "")
            metadata["grouping_style"] = "indian"
        else:
            cleaned = cleaned.replace(",", ".")
            metadata["decimal_separator"] = ","
    else:
        cleaned = cleaned.replace(",", "")
        if "." in cleaned:
            metadata["decimal_separator"] = "."

    try:
        value = Decimal(cleaned)
        metadata["normalized"] = cleaned
        return value, metadata
    except (InvalidOperation, ValueError):
        return None, metadata


def _detect_currency(
    raw: Optional[str],
    hints: Optional[OCRDocumentHints],
    candidate: Optional[FieldCandidate],
) -> Tuple[Optional[str], Dict[str, Any]]:
    metadata: Dict[str, Any] = {}
    if raw:
        raw = raw.strip()
    if raw:
        for glyph, code in CURRENCY_GLYPH_MAP.items():
            if glyph in raw:
                metadata["glyph"] = glyph
                metadata["source"] = "candidate"
                return code, metadata
        raw_lower = raw.lower()
        if raw_lower in CURRENCY_WORD_MAP:
            metadata["source"] = "candidate"
            return CURRENCY_WORD_MAP[raw_lower], metadata

    if candidate and candidate.value_raw:
        raw_lower = candidate.value_raw.lower()
        if raw_lower in CURRENCY_WORD_MAP:
            metadata["source"] = "candidate"
            return CURRENCY_WORD_MAP[raw_lower], metadata

    if hints and hints.currency_glyphs:
        for glyph in hints.currency_glyphs:
            if glyph in CURRENCY_GLYPH_MAP:
                metadata["glyph"] = glyph
                metadata["source"] = "document_hint"
                return CURRENCY_GLYPH_MAP[glyph], metadata

    return None, metadata


def _select_candidate(
    candidate_list: Optional[Iterable[FieldCandidate]],
) -> Optional[FieldCandidate]:
    if not candidate_list:
        return None
    return next(iter(candidate_list), None)


def _candidate_metadata(candidate: FieldCandidate) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {}
    if not candidate:
        return metadata
    if candidate.evidence.anchor_label:
        metadata["anchor"] = candidate.evidence.anchor_label
    if candidate.evidence.page:
        metadata["page"] = candidate.evidence.page
    if candidate.evidence.anchor_id:
        metadata["anchor_id"] = candidate.evidence.anchor_id
    return metadata


def _decimal_to_str(value: Optional[Decimal]) -> Optional[str]:
    if value is None:
        return None
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _field_from_results(
    field_name: str, candidates: Dict[str, List[FieldCandidate]]
) -> Optional[NormalizedFieldValue]:
    candidate = _select_candidate(candidates.get(field_name))
    if not candidate:
        return None
    metadata = _candidate_metadata(candidate)
    return NormalizedFieldValue(
        raw=candidate.value_raw,
        normalized=candidate.value_raw.strip() if candidate.value_raw else None,
        value_type="string",
        parser="identity",
        confidence=1.0,
        metadata=metadata,
    )

