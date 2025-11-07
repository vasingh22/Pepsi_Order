# Implementation Plan - Step by Step

## Phase 1: Project Setup & Foundation

### Step 1.1: Backend Setup
- [ ] Initialize Python virtual environment
- [ ] Install FastAPI, Uvicorn, dependencies
- [ ] Create project structure
- [ ] Set up environment variables (.env)
- [ ] Database connection (PostgreSQL/MongoDB)

### Step 1.2: Frontend Setup
- [ ] Initialize React/Next.js project
- [ ] Install dependencies (axios, tailwindcss, etc.)
- [ ] Set up API client configuration

### Step 1.3: Database Schema
- [ ] Documents table (id, filename, status, uploaded_at)
- [ ] Results table (document_id, structured_json, accuracy)
- [ ] Corrections table (result_id, corrections, feedback)
- [ ] Cache table (hash, document_id, created_at)
- [ ] Metrics table (document_id, cost, processing_time)

## Phase 2: Core API Development

### Step 2.1: File Upload Endpoint
- [ ] `POST /api/upload` - Accept images/PDFs
- [ ] File validation (type, size)
- [ ] Store file in storage (S3/local)
- [ ] Return job_id for tracking

### Step 2.2: Status & Results Endpoints
- [ ] `GET /api/status/{job_id}` - Check processing status
- [ ] `GET /api/results/{job_id}` - Get structured JSON
- [ ] Error handling

## Phase 3: OCR Integration (Surya OCR)

### Step 3.1: Surya OCR Service
- [ ] Install Surya OCR library/API client
- [ ] Create `ocr_service.py`
- [ ] Function: `extract_text(image_path)` → Returns text + coordinates
- [ ] Handle PDF conversion to images
- [ ] Error handling & retries

### Step 3.2: OCR Activity (Temporal)
- [ ] Create `ocr_activity.py`
- [ ] Integrate with workflow
- [ ] Store OCR results

## Phase 4: Text Normalization (Pre-LLM)

### Step 4.1: Text Normalization Service
- [ ] Create `text_normalizer.py`
- [ ] Remove extra whitespace and line breaks
- [ ] Fix common OCR errors (0→O, 1→I, etc.)
- [ ] Normalize text structure
- [ ] Function: `normalize_text(raw_ocr_text)` → cleaned text

### Step 4.2: Normalize Text Activity (Temporal)
- [ ] Create `normalize_text_activity.py`
- [ ] Integrate with workflow (after OCR, before LLM)
- [ ] Store normalized text

## Phase 5: LLM Parser Development

### Step 5.1: LLM Service Setup
- [ ] Choose LLM provider (OpenAI/Anthropic/Open-source)
- [ ] Create `llm_service.py`
- [ ] API key configuration
- [ ] Rate limiting

### Step 5.2: Few-Shot Prompt Design
- [ ] Analyze invoice sample (once provided)
- [ ] Define JSON schema for output
- [ ] Create few-shot examples using cleaned text
- [ ] Build prompt template
- [ ] Test prompt with normalized text sample

### Step 5.3: LLM Parse Activity
- [ ] Create `llm_activity.py`
- [ ] Function: `parse_structured_data(normalized_text, prompt)` → JSON
- [ ] **Input**: Cleaned text from Normalizer (not raw OCR)
- [ ] Error handling
- [ ] Cost tracking

## Phase 6: Field Validation (Post-LLM)

### Step 6.1: Field Validation Rules
- [ ] Date standardization (various formats → ISO 8601)
- [ ] Amount normalization (currency, decimals)
- [ ] Product code validation
- [ ] Customer name cleaning
- [ ] Address formatting
- [ ] Required field checks

### Step 6.2: Validation Logic
- [ ] Format validation on structured JSON
- [ ] Business rule validation
- [ ] Confidence scoring per field
- [ ] Overall document confidence

### Step 6.3: Validate Fields Activity
- [ ] Create `validate_fields_activity.py`
- [ ] Integrate with workflow (after LLM parsing)
- [ ] Store validated results

## Phase 7: Temporal Cloud Integration

### Step 7.1: Temporal Setup
- [ ] Create Temporal Cloud account
- [ ] Install Temporal Python SDK
- [ ] Configure connection
- [ ] Set up namespace

### Step 7.2: Workflow Implementation
- [ ] Create `document_workflow.py`
- [ ] Define workflow steps (CORRECT ORDER):
  1. CheckDuplicateActivity
  2. OCRActivity
  3. NormalizeTextActivity (Pre-LLM cleaning)
  4. LLMParseActivity (from cleaned text)
  5. ValidateFieldsActivity (Post-LLM validation)
  6. StoreResultsActivity
- [ ] Error handling & retries
- [ ] Timeout configuration

### Step 7.3: Activities Implementation
- [ ] CheckDuplicateActivity - Hash-based duplicate detection
- [ ] OCRActivity - OCR extraction (raw text)
- [ ] NormalizeTextActivity - Pre-LLM text cleaning
- [ ] LLMParseActivity - LLM parsing (from cleaned text)
- [ ] ValidateFieldsActivity - Post-LLM field validation
- [ ] StoreResultsActivity - Save to DB

## Phase 8: Caching & Duplicate Detection

### Step 8.1: Cache Service
- [ ] Create `cache_service.py`
- [ ] Hash generation (MD5/SHA256 of file content)
- [ ] Cache lookup
- [ ] Cache storage

### Step 8.2: Duplicate Detection
- [ ] Implement in CheckDuplicateActivity
- [ ] Return cached results if found
- [ ] Skip processing if duplicate

## Phase 9: Cost Tracking & Metrics

### Step 9.1: Cost Calculation
- [ ] Track OCR API costs
- [ ] Track LLM API costs (tokens) - reduced due to cleaner input
- [ ] Calculate total per document
- [ ] Store in metrics table
- [ ] Alert if >$0.04/document

### Step 9.2: Accuracy Metrics
- [ ] Compare with human-verified data
- [ ] Calculate field-level accuracy
- [ ] Overall accuracy tracking
- [ ] Dashboard endpoint

## Phase 10: Frontend Development

### Step 10.1: File Upload UI
- [ ] Drag & drop component
- [ ] File picker
- [ ] Progress indicator
- [ ] Multiple file support

### Step 10.2: Result Viewer
- [ ] Display structured JSON
- [ ] Formatted table view
- [ ] Download JSON
- [ ] Visual comparison (OCR vs Final)

### Step 10.3: Correction Interface
- [ ] Form for corrections
- [ ] Submit feedback
- [ ] Update prompts (future)

## Phase 11: Continuous Learning

### Step 11.1: Feedback Collection
- [ ] Store human corrections
- [ ] Track correction patterns
- [ ] Identify common errors

### Step 11.2: Prompt Refinement
- [ ] Analyze corrections
- [ ] Update few-shot examples
- [ ] A/B test prompt versions
- [ ] Version control for prompts

## Phase 12: Testing & Optimization

### Step 12.1: Unit Tests
- [ ] OCR service tests
- [ ] LLM service tests
- [ ] Normalizer tests
- [ ] API endpoint tests

### Step 12.2: Integration Tests
- [ ] End-to-end workflow tests
- [ ] Temporal workflow tests
- [ ] Cost validation tests

### Step 12.3: Performance Optimization
- [ ] Parallel processing
- [ ] Batch operations
- [ ] Cache optimization
- [ ] Cost optimization

## Phase 13: Deployment & Monitoring

### Step 13.1: Deployment
- [ ] Docker containers
- [ ] Docker Compose setup
- [ ] Environment configuration
- [ ] Deployment scripts

### Step 13.2: Monitoring
- [ ] Logging setup
- [ ] Error tracking
- [ ] Performance metrics
- [ ] Cost alerts

## Dependencies & Requirements

### Backend
- FastAPI
- Temporal Python SDK
- Surya OCR (or API client)
- OpenAI/Anthropic SDK (for LLM)
- PostgreSQL/Redis (for cache)
- Pydantic (for validation)
- python-multipart (for file uploads)

### Frontend
- React/Next.js
- Axios (API client)
- Tailwind CSS (styling)
- React Dropzone (file upload)

## Next Immediate Steps

1. **Wait for invoice sample** - To understand data structure
2. **Define JSON schema** - Based on invoice fields
3. **Create few-shot prompt** - With examples from invoice
4. **Start Phase 1** - Set up project structure

