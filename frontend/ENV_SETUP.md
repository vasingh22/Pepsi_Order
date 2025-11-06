# Environment Variables Setup

## Configuration

Create a `.env` file in the frontend root directory with the following variables:

```env
# Backend API Configuration
VITE_API_BASE_URL=http://localhost:8000
```

## Variables

### VITE_API_BASE_URL
- **Description**: Base URL for the backend API
- **Default**: `http://localhost:8000`
- **Examples**:
  - Development: `http://localhost:8000`
  - Production: `https://api.yourdomain.com`

## Usage

The environment variables are accessed in the code using `import.meta.env`:

```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
```

## Important Notes

1. **Prefix Required**: All environment variables in Vite must be prefixed with `VITE_` to be exposed to the client
2. **Restart Required**: After changing `.env`, restart the dev server
3. **Not Secret**: These variables are embedded in the client bundle - don't put sensitive data here
4. **Git Ignore**: The `.env` file is git-ignored by default

## Creating the .env File

```bash
# In the frontend directory
echo "VITE_API_BASE_URL=http://localhost:8000" > .env
```

Or manually create the file with your text editor.

