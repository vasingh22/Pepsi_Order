# Pepsi Order Digitization - Backend API

FastAPI backend for automated document processing system.

## Setup

### 1. Create Virtual Environment

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` with your configuration:
- Database URL (SQLite for development, PostgreSQL for production)
- API keys (OpenAI, Anthropic, etc.)
- File upload settings

### 4. Run the Application

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use Python directly
python -m app.main
```

The API will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## API Endpoints

### Upload Document
```
POST /api/upload
Content-Type: multipart/form-data

Body: file (PDF, PNG, JPG, JPEG)
Response: { job_id, filename, status, message }
```

### Check Status
```
GET /api/status/{job_id}
Response: { job_id, status, progress, message }
```

### Get Results
```
GET /api/results/{job_id}
Response: { structured_json, validated_json, confidence_score, ... }
```

### Submit Correction
```
POST /api/correct/{job_id}
Body: { corrected_json, feedback }
Response: { correction_id, message }
```

### Get Metrics
```
GET /api/metrics/{job_id}
Response: { ocr_cost, llm_cost, total_cost, processing_time, ... }
```

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── routes/          # API endpoints
│   ├── core/
│   │   └── config.py        # Configuration
│   ├── database/
│   │   ├── database.py      # DB connection
│   │   └── models.py        # Database models
│   ├── models/
│   │   └── schemas.py       # Pydantic schemas
│   ├── services/            # Business logic (to be added)
│   └── main.py              # FastAPI app
├── uploads/                 # Uploaded files (created automatically)
├── requirements.txt
└── README.md
```

## Next Steps

1. Integrate Surya OCR service
2. Implement text normalizer
3. Add LLM parsing service
4. Set up Temporal Cloud workflows
5. Implement field validation

## Development

- Database migrations: Use Alembic (to be configured)
- Testing: Add pytest (to be configured)
- Linting: Use black, flake8 (to be configured)

## Run with Docker

### Build and run with docker-compose (recommended)

```bash
cd /Users/vasingh/Desktop/Pepsi_Order
docker compose up --build -d
```

- API: http://localhost:8000
- Docs: http://localhost:8000/docs

The image includes Tesseract and Poppler, so PDF and image OCR work without host installs.

### Rebuild after code changes

```bash
docker compose build backend && docker compose up -d
```

### View logs

```bash
docker compose logs -f backend
```



