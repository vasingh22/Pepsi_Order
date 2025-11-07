# Pepsi Order Digitization System - Architecture

## Overview
Automated document processing system that converts unstructured order images/PDFs into structured JSON using OCR, LLM parsing, and Temporal orchestration.

## System Architecture

```
┌─────────────────┐
│   Frontend UI   │  (React/Next.js)
│  File Upload    │
│  Result Viewer  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│              Backend API (FastAPI/Flask)                │
│  ┌───────────────────────────────────────────────────┐  │
│  │   Upload Endpoint → Validate → Store → Queue     │  │
│  └───────────────────────────────────────────────────┘  │
└────────┬───────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│        Temporal Cloud Workflow Orchestration            │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Workflow: Document Processing Pipeline           │  │
│  │  1. Check Cache (Duplicate Detection)            │  │
│  │  2. OCR Extraction (Surya OCR)                   │  │
│  │  3. Text Normalization (Pre-LLM Cleaning)        │  │
│  │  4. LLM Parsing (Few-shot Prompt)                │  │
│  │  5. Field Validation & Post-normalization        │  │
│  │  6. Store Results & Metrics                      │  │
│  └───────────────────────────────────────────────────┘  │
└────────┬───────────────────────────────────────────────┘
         │
         ├──────────┬──────────────┬──────────────┬───────────┐
         ▼          ▼              ▼              ▼           ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Surya OCR   │  │  Text       │  │  LLM Service │  │  Field      │  │   Database   │
│  (Extract)   │  │  Normalizer │  │  (Parse)     │  │  Validator  │  │  (Postgres/  │
│              │  │  (Pre-LLM)  │  │              │  │  (Post-LLM) │  │   MongoDB)   │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

## Components

### 1. Frontend (React/Next.js)
- **File Upload**: Drag & drop or file picker for images/PDFs
- **Dashboard**: View processing status, results, corrections
- **Correction Interface**: Human feedback for continuous learning

### 2. Backend API (FastAPI - Python)
- **Endpoints**:
  - `POST /api/upload` - Upload document
  - `GET /api/status/{job_id}` - Check processing status
  - `GET /api/results/{job_id}` - Get structured JSON
  - `POST /api/correct/{job_id}` - Submit human corrections
  - `GET /api/metrics` - Cost and accuracy metrics

### 3. Temporal Cloud Workflow
- **Workflow**: DocumentProcessingWorkflow
- **Activities**:
  - `CheckDuplicateActivity` - Cache lookup
  - `OCRActivity` - Surya OCR extraction
  - `NormalizeTextActivity` - Pre-LLM text cleaning & normalization
  - `LLMParseActivity` - Structured data extraction (from cleaned text)
  - `ValidateFieldsActivity` - Post-LLM field validation & standardization
  - `StoreResultsActivity` - Save to database
  - `CalculateMetricsActivity` - Track cost & accuracy

### 4. OCR Service (Surya OCR)
- Extract text from images/PDFs
- Handle various formats and layouts
- Return raw text with coordinates

### 5. Text Normalizer (Pre-LLM)
- Clean raw OCR text (remove extra spaces, fix line breaks)
- Fix common OCR errors (character corrections)
- Basic text formatting and structure
- Prepare clean text for LLM parsing
- **Input**: Raw OCR text
- **Output**: Cleaned, normalized text

### 6. LLM Parser
- Use OpenAI/Anthropic/Open-source LLM
- Few-shot prompting for structured extraction
- **Input**: Cleaned, normalized text (from Normalizer)
- **Output**: Structured JSON matching invoice format

### 7. Field Validator (Post-LLM)
- Validate extracted structured data
- Field-level standardization (dates → ISO 8601, amounts, etc.)
- Business rule validation
- Confidence scoring

### 7. Database
- **Documents**: Store uploaded files metadata
- **Results**: Structured JSON outputs
- **Corrections**: Human feedback for learning
- **Cache**: Duplicate detection hashes
- **Metrics**: Cost tracking, accuracy metrics

## Data Flow

```
1. User uploads image/PDF
   ↓
2. Backend validates & stores file
   ↓
3. Temporal workflow triggered
   ↓
4. Check cache (hash-based duplicate detection)
   ↓
5. If not cached:
   a. OCR Activity → Extract raw text (Surya)
   b. Normalize Text Activity → Clean & normalize raw OCR text
   c. LLM Parse Activity → Structure data from cleaned text (few-shot prompt)
   d. Validate Fields Activity → Post-LLM validation & standardization
   e. Store results
   ↓
6. Return structured JSON
   ↓
7. Optional: Human correction → Update prompts/cache
```

## Key Features

### Reliability (Temporal Cloud)
- Automatic retries on failures
- Workflow versioning
- Full audit trail
- State management

### Cost Optimization
- Caching duplicates (no re-processing)
- Efficient LLM usage (few-shot prompts)
- Cost tracking per document
- Target: <$0.04/document

### Accuracy (≥95%)
- Multi-stage validation
- Rule-based normalization
- Human correction feedback
- Continuous prompt refinement

### Continuous Learning
- Cache duplicate documents
- Store human corrections
- Refine prompts over time
- A/B test prompt versions

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Orchestration**: Temporal Cloud (Python SDK)
- **Database**: PostgreSQL or MongoDB
- **File Storage**: AWS S3 / Local storage

### Frontend
- **Framework**: React or Next.js
- **UI Library**: Tailwind CSS / Material-UI

### Services
- **OCR**: Surya OCR API
- **LLM**: OpenAI GPT-4 / Anthropic Claude / Open-source (Llama)
- **Infrastructure**: Temporal Cloud

## Project Structure

```
Pepsi_Order/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── upload.py
│   │   │   │   ├── status.py
│   │   │   │   └── results.py
│   │   │   └── main.py
│   │   ├── services/
│   │   │   ├── ocr_service.py         # Surya OCR integration
│   │   │   ├── text_normalizer.py     # Pre-LLM text cleaning
│   │   │   ├── llm_service.py         # LLM parsing
│   │   │   ├── field_validator.py     # Post-LLM validation
│   │   │   └── cache_service.py       # Duplicate detection
│   │   ├── workflows/
│   │   │   └── document_workflow.py   # Temporal workflows
│   │   ├── activities/
│   │   │   ├── ocr_activity.py
│   │   │   ├── normalize_text_activity.py
│   │   │   ├── llm_activity.py
│   │   │   └── validate_fields_activity.py
│   │   ├── models/
│   │   │   └── schemas.py          # Pydantic models
│   │   └── database/
│   │       └── models.py           # DB models
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── FileUpload.tsx
│   │   │   ├── ResultViewer.tsx
│   │   │   └── CorrectionForm.tsx
│   │   ├── pages/
│   │   │   └── Dashboard.tsx
│   │   └── services/
│   │       └── api.ts
│   ├── package.json
│   └── Dockerfile
└── README.md
```

## Implementation Phases

### Phase 1: Core Infrastructure
1. Set up backend API with FastAPI
2. Basic file upload endpoint
3. Database schema
4. File storage setup

### Phase 2: OCR Integration
1. Integrate Surya OCR
2. Handle image/PDF processing
3. Text extraction workflow

### Phase 3: Text Normalization (Pre-LLM)
1. Implement text cleaning (spaces, line breaks)
2. Fix common OCR errors
3. Text structure normalization
4. Prepare clean input for LLM

### Phase 4: LLM Parsing
1. Design few-shot prompt template
2. Integrate LLM service
3. Structured JSON extraction (from cleaned text)
4. Error handling

### Phase 5: Field Validation (Post-LLM)
1. Rule-based validation on structured data
2. Field standardization (dates, amounts, etc.)
3. Business rule validation
4. Confidence scoring

### Phase 6: Temporal Integration
1. Set up Temporal Cloud
2. Create workflow
3. Implement activities
4. Retry logic

### Phase 6: Caching & Optimization
1. Duplicate detection
2. Cache management
3. Cost tracking

### Phase 7: Frontend
1. Upload UI
2. Result visualization
3. Correction interface

### Phase 8: Continuous Learning
1. Feedback collection
2. Prompt refinement
3. Metrics dashboard

## Next Steps
1. Review sample invoice file to understand data structure
2. Define JSON output schema
3. Create few-shot prompt examples
4. Start implementation

