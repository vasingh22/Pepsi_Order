# Backend Setup Guide

## Quick Start

### 1. Install Python Dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Create Environment File

Create a `.env` file in the `backend` directory:

```bash
# Database (SQLite for development)
DATABASE_URL=sqlite:///./pepsi_order.db

# Application
APP_NAME=Pepsi Order Digitization API
DEBUG=True

# File Upload
MAX_FILE_SIZE_MB=10
UPLOAD_DIR=./uploads
ALLOWED_EXTENSIONS=pdf,PDF,png,PNG,jpg,JPG,jpeg,JPEG

# CORS (for frontend)
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### 3. Run the Server

```bash
# Option 1: Using run.py
python run.py

# Option 2: Using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test the API

- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Root: http://localhost:8000/

## Testing Upload Endpoint

You can test the upload endpoint using curl:

```bash
curl -X POST "http://localhost:8000/api/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/document.pdf"
```

Or use the interactive API docs at `/docs` to test all endpoints.

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── routes/          # API endpoints
│   │       ├── upload.py     # File upload
│   │       ├── status.py     # Status check
│   │       ├── results.py    # Get results
│   │       ├── corrections.py # Submit corrections
│   │       └── metrics.py    # Get metrics
│   ├── core/
│   │   └── config.py         # Configuration settings
│   ├── database/
│   │   ├── database.py       # DB connection
│   │   └── models.py         # SQLAlchemy models
│   ├── models/
│   │   └── schemas.py        # Pydantic schemas
│   ├── services/             # Business logic (to be added)
│   └── main.py               # FastAPI application
├── uploads/                  # Uploaded files (created automatically)
├── requirements.txt          # Python dependencies
├── run.py                    # Simple runner script
└── README.md
```

## Database

The application uses SQLite by default for development. To use PostgreSQL:

1. Update `DATABASE_URL` in `.env`:
   ```
   DATABASE_URL=postgresql://user:password@localhost:5432/pepsi_order_db
   ```

2. Install PostgreSQL and create the database:
   ```sql
   CREATE DATABASE pepsi_order_db;
   ```

3. Tables are created automatically on first run.

## Next Steps

1. ✅ Backend structure created
2. ✅ API endpoints ready
3. ⏭️ Integrate Surya OCR
4. ⏭️ Implement text normalizer
5. ⏭️ Add LLM parsing
6. ⏭️ Set up Temporal workflows

