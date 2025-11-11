import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def extract_address_lines(address_data: Optional[Dict[str, Any]]) -> str:
    """Extract clean address from address data."""
    if not address_data:
        return ""
    
    lines = address_data.get("normalized", {}).get("lines", [])
    if not lines:
        raw = address_data.get("raw", "")
        if raw:
            # Clean up the raw address
            lines = [line.strip() for line in raw.split("\\n") if line.strip()]
    
    # Filter out common noise words and numbers that are likely not part of address
    filtered_lines = []
    skip_patterns = ["subtotal", "total", "cases", "unit", "price", "count", "order", "description", "item"]
    
    for line in lines:
        line_lower = line.lower().strip()
        # Skip if it's just a number or matches skip patterns
        if line_lower in skip_patterns or re.match(r'^[\d.,\s]+$', line_lower):
            continue
        # Skip very short lines that are likely OCR artifacts
        if len(line.strip()) < 3:
            continue
        filtered_lines.append(line.strip())
    
    # Take first few meaningful lines (usually 2-4 lines for an address)
    return ", ".join(filtered_lines[:4])


def extract_contact_from_address(address_data: Optional[Dict[str, Any]]) -> str:
    """Extract contact number from address if present."""
    if not address_data:
        return ""
    
    raw = address_data.get("raw", "")
    # Look for phone number patterns
    phone_pattern = r'[\+]?[\d\s\-\(\)]{10,}'
    matches = re.findall(phone_pattern, raw)
    if matches:
        return matches[0].strip()
    return ""


def extract_gst_number(source_data: Dict[str, Any]) -> str:
    """Extract GST number from various possible locations."""
    # Check in fields
    fields = source_data.get("fields", {})
    
    # Look for GST in any field
    for field_name, field_data in fields.items():
        if field_data and isinstance(field_data, dict):
            raw = field_data.get("raw", "")
            normalized = field_data.get("normalized", "")
            # GST number pattern: 2 digits, 10 alphanumeric, 1 letter, 1 digit, 1 letter, 1 digit
            gst_pattern = r'\d{2}[A-Z0-9]{10}[A-Z]\d[Z][A-Z0-9]'
            for text in [raw, normalized]:
                if text:
                    match = re.search(gst_pattern, text.upper())
                    if match:
                        return match.group(0)
    
    # Check in addresses
    for addr_type in ["bill_to", "ship_to"]:
        addr = source_data.get("addresses", {}).get(addr_type)
        if addr:
            raw = addr.get("raw", "")
            gst_pattern = r'\d{2}[A-Z0-9]{10}[A-Z]\d[Z][A-Z0-9]'
            match = re.search(gst_pattern, raw.upper())
            if match:
                return match.group(0)
    
    return ""


def parse_line_items_from_tables(source_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract line items from tables in the detailed JSON."""
    items = []
    tables = source_data.get("tables", [])
    
    if not tables:
        return items
    
    for table in tables:
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
                rows[row_idx][headers[col_idx]] = cell.get("text", "").strip()
        
        # Process each row as a line item
        for row_data in rows.values():
            # Find relevant columns
            desc_header = next(
                (h for h in headers if any(keyword in h.lower() for keyword in ["description", "item", "product", "name"])),
                headers[0] if headers else ""
            )
            qty_header = next(
                (h for h in headers if any(keyword in h.lower() for keyword in ["qty", "quantity", "count", "cases"])),
                ""
            )
            unit_header = next(
                (h for h in headers if any(keyword in h.lower() for keyword in ["unit", "packing", "pack"])),
                ""
            )
            rate_header = next(
                (h for h in headers if any(keyword in h.lower() for keyword in ["rate", "price", "unit price"])),
                ""
            )
            amount_header = next(
                (h for h in headers if any(keyword in h.lower() for keyword in ["amount", "total", "subtotal"])),
                headers[-1] if headers else ""
            )
            hsn_header = next(
                (h for h in headers if any(keyword in h.lower() for keyword in ["hsn", "code", "product id", "item id"])),
                ""
            )
            
            # Extract values
            name = row_data.get(desc_header, "").strip()
            if not name or len(name) < 2:
                continue  # Skip empty rows
            
            # Parse numeric values
            def parse_float(value_str):
                if not value_str:
                    return 0.0
                try:
                    # Remove commas and currency symbols
                    cleaned = re.sub(r'[^\d.-]', '', str(value_str))
                    return float(cleaned) if cleaned else 0.0
                except (ValueError, TypeError):
                    return 0.0
            
            quantity = parse_float(row_data.get(qty_header, ""))
            rate = parse_float(row_data.get(rate_header, ""))
            amount = parse_float(row_data.get(amount_header, ""))
            
            # If amount is missing, calculate from quantity * rate
            if amount == 0 and quantity > 0 and rate > 0:
                amount = quantity * rate
            
            # Extract unit
            unit = row_data.get(unit_header, "").strip() or "unit"
            # Clean up unit (remove common prefixes like "cs", "pk", etc.)
            unit = re.sub(r'^(cs|pk|pack|case|bottle|packet)\s*', '', unit.lower())
            if not unit:
                unit = "unit"
            
            # Extract HSN code
            hsn_code = row_data.get(hsn_header, "").strip()
            
            item_obj = {
                "name": name,
                "hsn_code": hsn_code,
                "quantity": quantity,
                "unit": unit,
                "rate": rate,
                "discount": 0,
                "amount": round(amount, 2)
            }
            
            items.append(item_obj)
    
    return items


def parse_line_items(source_data: Dict[str, Any], detailed_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Extract and format line items from standardized or detailed JSON."""
    items = []
    
    # First try to get from detailed JSON (has table data)
    if detailed_data:
        items = parse_line_items_from_tables(detailed_data)
        if items:
            return items
    
    # Fallback to standardized format
    line_items = source_data.get("line_items", [])
    
    for item in line_items:
        item_obj = {
            "name": item.get("description", "").strip() or "Unknown Item",
            "hsn_code": "",
            "quantity": item.get("quantity", {}).get("normalized") or 0,
            "unit": "unit",
            "rate": item.get("unit_price", {}).get("normalized") or 0.0,
            "discount": 0,
            "amount": item.get("total_price", {}).get("normalized") or 0.0
        }
        
        # Try to extract HSN code from material_id if present
        material_id = item.get("material_id", {})
        if material_id:
            all_ids = material_id.get("all_found_ids", [])
            for id_dict in all_ids:
                for key, value in id_dict.items():
                    if "hsn" in key.lower() or "code" in key.lower():
                        item_obj["hsn_code"] = str(value)
                        break
        
        # Convert numeric values
        try:
            item_obj["quantity"] = float(item_obj["quantity"]) if item_obj["quantity"] else 0
            item_obj["rate"] = float(item_obj["rate"]) if item_obj["rate"] else 0.0
            item_obj["amount"] = float(item_obj["amount"]) if item_obj["amount"] else 0.0
        except (ValueError, TypeError):
            pass
        
        items.append(item_obj)
    
    return items


def parse_charges(source_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract charges and tax information."""
    totals = source_data.get("totals", {})
    
    subtotal_value = 0.0
    tax_amount = 0.0
    tax_rate = 0
    total_value = 0.0
    
    # Get subtotal
    subtotal_field = totals.get("subtotal")
    if subtotal_field and subtotal_field.get("normalized"):
        try:
            subtotal_value = float(subtotal_field["normalized"])
        except (ValueError, TypeError):
            pass
    
    # Get tax
    tax_field = totals.get("tax")
    if tax_field and tax_field.get("normalized"):
        try:
            tax_amount = float(tax_field["normalized"])
            # Try to calculate tax rate if we have subtotal
            if subtotal_value > 0:
                tax_rate = round((tax_amount / subtotal_value) * 100, 2)
        except (ValueError, TypeError):
            pass
    
    # Get grand total
    grand_total_field = totals.get("grand_total")
    if grand_total_field and grand_total_field.get("normalized"):
        try:
            total_value = float(grand_total_field["normalized"])
        except (ValueError, TypeError):
            pass
    
    # If we have subtotal and tax but no grand total, calculate it
    if total_value == 0 and subtotal_value > 0:
        total_value = subtotal_value + tax_amount
    
    # Determine tax type (GST is common in India)
    tax_type = "GST"
    currency = source_data.get("document_fingerprint", {}).get("currency_iso")
    if currency and currency != "INR":
        tax_type = "VAT"  # Use VAT for non-Indian currencies
    
    return {
        "subtotal": round(subtotal_value, 2),
        "tax_details": {
            "type": tax_type,
            "rate": tax_rate,
            "amount": round(tax_amount, 2)
        },
        "round_off": 0.0,
        "total": round(total_value, 2)
    }


def generate_invoice_json(source_path: Path, output_dir: Path, detailed_json_dir: Optional[Path] = None):
    """Convert standardized JSON to invoice-specific JSON format."""
    try:
        with open(source_path, "r", encoding="utf-8") as f:
            source_data = json.load(f)
        
        # Try to load corresponding detailed JSON for better line item extraction
        detailed_data = None
        if detailed_json_dir:
            detailed_json_path = detailed_json_dir / source_path.name
            if detailed_json_path.exists():
                try:
                    with open(detailed_json_path, "r", encoding="utf-8") as f:
                        detailed_data = json.load(f)
                except Exception:
                    pass
        
        # Extract document summary
        doc_summary = source_data.get("document_summary", {})
        filename = doc_summary.get("filename", "")
        
        # Extract fields
        fields = source_data.get("fields", {})
        addresses = source_data.get("addresses", {})
        
        # Store/Seller information
        vendor_guess = source_data.get("document_fingerprint", {}).get("vendor_guess")
        seller_address = addresses.get("ship_to") or addresses.get("bill_to")
        
        store_name = vendor_guess or "Unknown Store"
        if seller_address:
            addr_lines = seller_address.get("normalized", {}).get("lines", [])
            if addr_lines:
                # First line might be store name
                first_line = addr_lines[0].strip()
                if len(first_line) > 3 and not re.match(r'^[\d\s,]+$', first_line):
                    store_name = first_line
        
        seller_address_str = extract_address_lines(seller_address)
        seller_gst = extract_gst_number(source_data)
        
        # Buyer information
        buyer_address = addresses.get("bill_to") or addresses.get("ship_to")
        buyer_address_str = extract_address_lines(buyer_address)
        buyer_contact = extract_contact_from_address(buyer_address)
        
        # Extract buyer name from address
        buyer_name = "Unknown Buyer"
        if buyer_address:
            addr_lines = buyer_address.get("normalized", {}).get("lines", [])
            if addr_lines:
                first_line = addr_lines[0].strip()
                if len(first_line) > 3 and not re.match(r'^[\d\s,]+$', first_line):
                    buyer_name = first_line
        
        # Invoice number and date
        invoice_number = ""
        invoice_date = ""
        
        po_number_field = fields.get("purchase_order_number")
        if po_number_field and po_number_field.get("normalized"):
            invoice_number = po_number_field["normalized"]
        
        po_date_field = fields.get("purchase_order_date")
        if po_date_field and po_date_field.get("normalized"):
            invoice_date = po_date_field["normalized"]
        
        # If no invoice number found, try to extract from filename
        if not invoice_number:
            # Look for patterns like PO_271931 in filename
            po_match = re.search(r'PO[_\s-]?(\d+)', filename, re.IGNORECASE)
            if po_match:
                invoice_number = po_match.group(1)
            else:
                invoice_number = filename.split(".")[0][:20]  # Use filename prefix
        
        # Parse line items (prefer detailed JSON for table data)
        items = parse_line_items(source_data, detailed_data)
        
        # Parse charges
        charges = parse_charges(source_data)
        
        # Build the invoice JSON with ALL fields from standardized JSON
        # Start with reference format fields (for UI compatibility)
        invoice_json = {
            # Reference format fields (for UI compatibility - these are the primary fields)
            "store_name": store_name,
            "address": seller_address_str or "Address not available",
            "gst_number": seller_gst,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date,
            "buyer_details": {
                "name": buyer_name,
                "address": buyer_address_str or "Address not available",
                "contact": buyer_contact
            },
            "seller_details": {
                "name": store_name,
                "address": seller_address_str or "Address not available",
                "gst_number": seller_gst
            },
            "items": items,
            "charges": charges,
            "payment_details": {
                "mode": "Cash",  # Default, could be enhanced to detect from document
                "paid": False,
                "due_date": ""  # Could calculate from invoice_date if needed
            }
        }
        
        # Now include ALL additional fields from the standardized JSON
        # This preserves all extracted data that might be specific to each document
        # The reference format fields above are the primary/display fields
        # All other fields from standardized JSON are included to ensure no data is lost
        reference_format_keys = {"items", "charges", "payment_details", "store_name", "address", 
                                "gst_number", "invoice_number", "invoice_date", "buyer_details", "seller_details"}
        
        for key, value in source_data.items():
            if key not in reference_format_keys and value is not None:
                # Include all standardized JSON fields (document_summary, document_fingerprint, 
                # fields, addresses, line_items, totals, anomalies, etc.)
                invoice_json[key] = value
        
        # Calculate due date (typically 7-30 days from invoice date)
        if invoice_date:
            try:
                inv_date = datetime.strptime(invoice_date, "%Y-%m-%d")
                due_date = inv_date.replace(day=min(inv_date.day + 7, 28))  # 7 days later
                invoice_json["payment_details"]["due_date"] = due_date.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pass
        
        # Save the invoice JSON
        output_path = output_dir / f"{source_path.stem}_invoice.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(invoice_json, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Successfully generated invoice JSON: {output_path.name}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to generate invoice JSON for {source_path.name}: {e}", exc_info=True)
        return False


def main():
    """Main function to process all standardized JSON files."""
    script_dir = Path(__file__).parent.resolve()
    input_dir = script_dir / "results_standardized"
    detailed_json_dir = script_dir / "results"  # Original detailed JSON files
    output_dir = script_dir / "results_invoice"
    output_dir.mkdir(exist_ok=True)
    
    json_files = list(input_dir.glob("*.json"))
    total_files = len(json_files)
    logging.info(f"Found {total_files} standardized JSON files to convert.")
    
    success_count = 0
    for i, file_path in enumerate(json_files):
        logging.info(f"Processing file {i+1}/{total_files}: {file_path.name}")
        if generate_invoice_json(file_path, output_dir, detailed_json_dir):
            success_count += 1
    
    logging.info(f"Conversion complete. Successfully processed {success_count}/{total_files} files.")
    logging.info(f"Invoice JSON files saved to: {output_dir}")


if __name__ == "__main__":
    main()

