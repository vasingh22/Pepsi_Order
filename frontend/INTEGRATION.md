# Backend Integration Guide

This guide explains how to integrate the frontend with your backend API.

## Quick Start

1. **Create a `.env` file** from `.env.example`:
```bash
cp .env.example .env
```

2. **Update the API URL** in `.env`:
```env
VITE_API_BASE_URL=http://your-backend-url:port
```

3. **Import and use the API utilities** in your components:

```typescript
import { uploadFiles } from './utils/api'

const handleUpload = async (files: File[]) => {
  try {
    const response = await uploadFiles(files)
    console.log('Upload successful:', response)
  } catch (error) {
    console.error('Upload failed:', error)
  }
}
```

## Example Integration in FileUpload Component

Update the `FileUpload.tsx` component to actually send files to the backend:

```typescript
import { uploadFiles } from '../utils/api'

// Inside the FileUpload component, update the submit button:

<button 
  className="submit-btn"
  onClick={async () => {
    try {
      const response = await uploadFiles(files.map(f => f.file))
      alert('Files uploaded successfully!')
      console.log('Response:', response)
    } catch (error) {
      alert('Upload failed. Please try again.')
      console.error(error)
    }
  }}
>
  <span>Process {files.length} File{files.length > 1 ? 's' : ''}</span>
  <span className="btn-icon">→</span>
</button>
```

## Expected Backend Endpoints

The API utilities expect the following backend endpoints:

### 1. Upload Files
- **Endpoint**: `POST /api/upload`
- **Content-Type**: `multipart/form-data`
- **Body**: FormData with files
- **Response**: 
```json
{
  "jobId": "unique-job-id",
  "status": "processing",
  "filesCount": 3
}
```

### 2. Check Job Status
- **Endpoint**: `GET /api/status/:jobId`
- **Response**:
```json
{
  "jobId": "unique-job-id",
  "status": "completed" | "processing" | "failed",
  "progress": 75
}
```

### 3. Get Job Results
- **Endpoint**: `GET /api/results/:jobId`
- **Response**:
```json
{
  "jobId": "unique-job-id",
  "results": [
    {
      "filename": "order1.pdf",
      "extractedData": { ... },
      "confidence": 0.95
    }
  ]
}
```

## File Upload Format

The frontend sends files as `multipart/form-data` with each file appended to the `files` field:

```typescript
const formData = new FormData()
files.forEach((file) => {
  formData.append('files', file)
})
```

Your backend should accept multiple files in the `files` field.

## Error Handling

The API utilities throw errors that you should catch and handle:

```typescript
try {
  const response = await uploadFiles(files)
  // Handle success
} catch (error) {
  // Handle error
  if (error instanceof Error) {
    console.error('Error message:', error.message)
  }
}
```

## CORS Configuration

Make sure your backend allows requests from the frontend origin. Example for Express.js:

```javascript
app.use(cors({
  origin: 'http://localhost:5173', // Vite dev server
  credentials: true
}))
```

## File Size Limits

The frontend validates files up to 10MB. Make sure your backend can handle files of this size:

- Express.js: Configure body-parser or multer
- FastAPI: Configure max request size
- Django: Configure FILE_UPLOAD_MAX_MEMORY_SIZE

## Security Considerations

1. **Validate file types** on the backend (don't trust client-side validation)
2. **Scan files** for malware before processing
3. **Use authentication** if required (add Authorization headers in api.ts)
4. **Rate limit** upload endpoints to prevent abuse
5. **Sanitize filenames** to prevent path traversal attacks

## Testing the Integration

1. Start your backend server
2. Update `.env` with the correct backend URL
3. Start the frontend dev server: `npm run dev`
4. Upload a test file and check the browser console and network tab
5. Verify the file reaches your backend endpoint

## Troubleshooting

### CORS Errors
- Ensure your backend CORS configuration allows the frontend origin
- Check that preflight OPTIONS requests are handled

### Upload Fails
- Check the backend URL in `.env`
- Verify the backend server is running
- Check backend logs for errors
- Inspect network tab in browser DevTools

### File Not Received
- Verify the FormData field name matches backend expectations
- Check backend file upload middleware configuration
- Ensure Content-Type is not manually set (let browser set it)

## Additional Features to Implement

Once basic upload works, consider adding:

1. **Upload Progress** - Show progress bar during upload
2. **Retry Logic** - Automatically retry failed uploads
3. **Authentication** - Add JWT tokens or API keys
4. **Job Status Polling** - Poll for processing completion
5. **Results Display** - Show extracted data in the UI
6. **Download Results** - Allow downloading processed data

