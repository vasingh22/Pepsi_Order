# Invoice OCR Backend

This FastAPI service provides REST endpoints and Swagger UI to extract the textual content of invoice PDFs using the [Surya OCR](https://github.com/datalab-to/surya) toolkit. It exposes endpoints for uploading PDFs as well as for processing sample files already present on the server.

## Project structure

```
app/
  api/            # API routers and dependency wiring
  config.py       # Application settings (paths, limits, defaults)
  main.py         # FastAPI application factory
  schemas.py      # Pydantic models used in requests/responses
  services/       # Surya OCR integration and result normalisation
PickSample200/    # Reference invoices (provided by the user)
requirements.txt  # Python dependencies
```

## Prerequisites

1. **Python 3.10+** (Surya requires Python 3.10 or newer).
2. **System Dependencies**  
   Surya relies on PyTorch and a few native libraries (Poppler, Tesseract). Review Surya's documentation for the most recent setup instructions:
   ```
   https://github.com/datalab-to/surya
   ```
3. (Optional) Create a virtual environment to isolate dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

## Installation

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> The first run of Surya OCR downloads model weights (~1.5 GB). Keep the server online during that step.

## Running the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Once running:

- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

## Endpoints

- `GET /health`  
  Simple heartbeat check.

- `GET /ocr/samples`  
  Lists available sample PDFs located in `PickSample200/`.

- `GET /ocr/extract/sample?filename=XYZ.pdf`  
  Runs Surya OCR on a sample file already on the server. Optional query params:  
  - `languages`: Comma-separated language codes (default: `en`).  
  - `include_raw`: Include Surya's raw output in the response (boolean).

- `POST /ocr/extract` (multipart/form-data)  
  Upload a PDF invoice via Swagger or any HTTP client. Supported query params match the sample endpoint.  
  Response now includes:
  - Document-level and per-page `tokens` with bounding boxes, confidence, reading order, and engine provenance.  
  - `zones` (header/body/footer per page) and `anchors` (labelled spans such as PO No, Order Date) with 300px context token windows for downstream deterministic lookup.
  - `tables` describing inferred table skeletons (header rows, column headers, per-cell texts/bboxes) so you can reconstruct line items deterministically before handing them to validators.
  - Field `candidates` with supporting evidence and `hints` (date/day-first probability, numbering style, currency glyphs) so downstream tools can route to deterministic parsers.
  - `normalized` deterministic parsing output (selected candidates, parsed ISO dates, decimal totals, currency detection, and reconciliation metadata for table-driven totals).
  - Optional `master_data` alias lists (when configured), `fingerprint` priors (vendor guess, layout hash), and `anomalies` to highlight questionable sections for follow-up tools.

## Configuration

Default settings live in `app/config.py`. You can override them with environment variables (via `.env`), for example:

```bash
export OCR_SAMPLE_DIR=/absolute/path/to/your/samples
export OCR_TEMP_DIR=/absolute/path/to/temp
export OCR_DEFAULT_LANGUAGES=en,hi
export OCR_MAX_UPLOAD_SIZE_MB=50
export OCR_VENDOR_MASTER_PATH=/absolute/path/to/vendor_aliases.json
export OCR_SKU_MASTER_PATH=/absolute/path/to/sku_aliases.json
export OCR_UOM_MASTER_PATH=/absolute/path/to/uom_aliases.json
```

`OCR_DEFAULT_LANGUAGES` accepts comma-separated values. Paths are expanded automatically.

## Notes & Troubleshooting

- Surya OCR can be resource intensive. Run the API on a machine with a GPU (recommended) or a powerful CPU.
- If Surya's public API changes, adjust `app/services/ocr_service.py` in `_run_surya`.
- The service normalises Surya's output into a consistent structure, but you can request the raw payload (beware of large responses).
- Temporary files are written to `.tmp/`. They are deleted after each request; ensure the process has write permissions.

## Development

- Format/lint as needed (e.g. `ruff`, `black`).
- Extend schemas and add persistence if the extracted results need to be stored.
- Consider adding authentication/authorisation before exposing the service publicly.

