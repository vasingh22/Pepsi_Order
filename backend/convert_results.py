import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_material_id(row_data: Dict[str, str], all_headers: List[str]) -> Dict[str, Any]:
    """
    Extracts material IDs based on the priority rules.
    """
    all_found_ids = []
    # Rule: Extract ALL item identifiers found
    id_keywords = ['item', 'vendor', 'product', 'material', 'sku', 'bin', 'code', 'number', 'id', 's4', 'mdg', 'mfg', 'gtin', 'ean', 'upc']
    for header, value in row_data.items():
        if any(keyword in header.lower() for keyword in id_keywords):
            all_found_ids.append({header: value})

    # Rule: Select one ID based on priority
    priority_map = {
        1: (["s4 code"], None),
        2: (["mdg id", "mfg number"], re.compile(r"^\d{9}$|^\d{18}$")),
        3: (["gtin", "ean-13", "gtin-14"], re.compile(r"^\d{11,14}$")),
        4: (["upc"], re.compile(r"^\d{1,5}$")),
        5: (["item id", "item code", "number"], None)
    }

    selected_id = ""
    selection_reason = "No priority field found."

    for priority in sorted(priority_map.keys()):
        headers, validator = priority_map[priority]
        for header_key in headers:
            # Find the actual header from the document that matches our key
            for doc_header in all_headers:
                if header_key in doc_header.lower():
                    value = row_data.get(doc_header)
                    if value:
                        if validator and not validator.match(value):
                            continue  # Failed validation
                        selected_id = value
                        selection_reason = f"Priority {priority}: '{doc_header}' column found."
                        # Return on first match within priority level
                        return {
                            "selected_id": selected_id,
                            "selection_reason": selection_reason,
                            "all_found_ids": all_found_ids or [{"<none_found>": ""}],
                        }

    # If no priority match was found
    return {
        "selected_id": selected_id,
        "selection_reason": selection_reason,
        "all_found_ids": all_found_ids or [{"<none_found>": ""}],
    }


def parse_number(raw: Optional[str]) -> Optional[float]:
    """Simple number parser."""
    if not raw:
        return None
    try:
        # Remove currency, commas, and whitespace
        cleaned = re.sub(r"[^\d.-]", "", raw).strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def map_line_items(source_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Maps table data to a structured list of line items."""
    line_items = []
    if not source_data.get("tables"):
        return line_items

    for table in source_data["tables"]:
        headers = table.get("column_headers", [])
        if not headers:
            continue

        # Group cells by row
        rows: Dict[int, Dict[str, str]] = {}
        for cell in table.get("cells", []):
            row_idx = cell.get("row")
            col_idx = cell.get("column")
            if row_idx is None or col_idx is None or cell.get("is_header"):
                continue

            if row_idx not in rows:
                rows[row_idx] = {}
            if col_idx < len(headers):
                rows[row_idx][headers[col_idx]] = cell.get("text", "")

        # Process rows
        for line_num, row_data in enumerate(rows.values(), 1):
            # A simple heuristic to find description, qty, price columns
            desc_header = next((h for h in headers if "description" in h.lower() or "item" in h.lower()), headers[0] if headers else "")
            qty_header = next((h for h in headers if "qty" in h.lower() or "quantity" in h.lower()), "")
            unit_price_header = next((h for h in headers if "unit" in h.lower() or "price" in h.lower()), "")
            total_price_header = next((h for h in headers if "total" in h.lower() or "amount" in h.lower()), headers[-1] if headers else "")

            line_item = {
                "line_number": line_num,
                "description": row_data.get(desc_header, ""),
                "material_id": get_material_id(row_data, headers),
                "quantity": {
                    "raw": row_data.get(qty_header, ""),
                    "normalized": parse_number(row_data.get(qty_header)),
                },
                "unit_price": {
                    "raw": row_data.get(unit_price_header, ""),
                    "normalized": parse_number(row_data.get(unit_price_header)),
                },
                "total_price": {
                    "raw": row_data.get(total_price_header, ""),
                    "normalized": parse_number(row_data.get(total_price_header)),
                },
                "evidence": {"page": table.get("page"), "bounding_box": table.get("bbox_rel")}
            }
            line_items.append(line_item)
    return line_items


def map_addresses(source_data: Dict[str, Any]) -> Dict[str, Any]:
    """Finds address blocks from anchors and context tokens."""
    addresses = {}
    
    anchors = source_data.get("anchors")
    if not anchors:
        return addresses

    token_map = {token['id']: token for token in source_data.get('tokens', [])}
    if not token_map:
        return addresses

    for anchor in anchors:
        label = anchor.get("label")
        if label in ["bill_to", "ship_to"]:
            context_ids = anchor.get("context_token_ids", [])
            context_tokens = [token_map[t_id] for t_id in context_ids if t_id in token_map]
            # Sort tokens by reading order to reconstruct the address block
            context_tokens.sort(key=lambda t: t.get('reading_order', 0))
            
            raw_text = "\\n".join(token.get('text', '') for token in context_tokens)
            
            addresses[label] = {
                "raw": raw_text,
                "normalized": {"lines": raw_text.split("\\n")},
                "evidence": {
                    "page": anchor.get("page"),
                    "bounding_box": anchor.get("bbox_rel"),
                }
            }
    return addresses


def convert_file(source_path: Path, output_dir: Path):
    """Converts a single OCR result JSON to the standardized format."""
    try:
        source_data = json.loads(source_path.read_text(encoding="utf-8"))
        
        # --- Mapping ---
        normalized_data = source_data.get("normalized") or {}
        normalized_fields = normalized_data.get("fields") or {}
        
        def get_field(name: str) -> Optional[Dict[str, Any]]:
            field_data = normalized_fields.get(name)
            if not field_data:
                return None
            return {
                "raw": field_data.get("raw"),
                "normalized": field_data.get("normalized"),
                "confidence": field_data.get("confidence"),
                "evidence": {
                    "page": field_data.get("metadata", {}).get("page"),
                    "bounding_box": None # Bbox not easily available here, would need to trace back to anchor
                }
            }

        totals = normalized_data.get("totals") or {}
        
        # --- Assemble Final JSON ---
        target_json = {
            "document_summary": {
                "filename": source_data.get("filename"),
                "document_type_guess": "Purchase Order" if "purchase_order_number" in normalized_fields else "Unknown",
                "page_count": len(source_data.get("pages") or []),
            },
            "document_fingerprint": {
                "vendor_guess": (source_data.get("fingerprint") or {}).get("vendor_guess"),
                "languages": (source_data.get("fingerprint") or {}).get("languages"),
                "currency_iso": (normalized_data.get("currency") or {}).get("normalized"),
                "numbering_style": (source_data.get("fingerprint") or {}).get("numbering_style"),
                "day_first_date_probability": (source_data.get("hints") or {}).get("day_first_prob"),
            },
            "fields": {
                "purchase_order_number": get_field("po_number"),
                "purchase_order_date": get_field("po_date"),
                "delivery_date": get_field("delivery_date"), # Note: not in original normalization
            },
            "addresses": map_addresses(source_data),
            "line_items": map_line_items(source_data),
            "totals": {
                "subtotal": get_field("subtotal"),
                "tax": get_field("tax_total"),
                "grand_total": get_field("grand_total"),
                "verification": {
                    "status": totals.get("status"),
                    "recomputed_total": (totals.get("recomputed_total") or {}).get("normalized"),
                    "difference": totals.get("difference"),
                    "notes": totals.get("notes"),
                },
            },
            "anomalies": source_data.get("anomalies") or [],
        }

        # Remove empty fields for clarity
        target_json["fields"] = {k: v for k, v in target_json["fields"].items() if v}

        output_path = output_dir / source_path.name
        output_path.write_text(json.dumps(target_json, indent=2, ensure_ascii=False))
        logging.info(f"Successfully converted {source_path.name}")

    except Exception as e:
        logging.error(f"Failed to convert {source_path.name}: {e}", exc_info=True)


def main():
    """Main function to run the conversion process."""
    # Use absolute paths to prevent issues with the current working directory
    script_dir = Path(__file__).parent.resolve()
    input_dir = script_dir / "results"
    output_dir = script_dir / "results_standardized"
    output_dir.mkdir(exist_ok=True)

    json_files = list(input_dir.glob("*.json"))
    total_files = len(json_files)
    logging.info(f"Found {total_files} JSON files to convert.")

    for i, file_path in enumerate(json_files):
        logging.info(f"Converting file {i+1}/{total_files}: {file_path.name}")
        convert_file(file_path, output_dir)

    logging.info("Conversion process complete.")


if __name__ == "__main__":
    main()
