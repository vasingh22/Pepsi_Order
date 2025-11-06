# PepsiCo Order Processing Frontend

A modern React + TypeScript application for uploading and processing unstructured order documents (images and PDFs) using AI-powered OCR and LLM workflows.

## Features

- 🎨 **Modern UI/UX** - Beautiful landing page with gradient backgrounds and smooth animations
- 📤 **File Upload** - Drag & drop or click to upload multiple files
- 🖼️ **Image Preview** - Real-time preview of uploaded images
- 📄 **PDF Support** - Upload and process PDF documents
- ✅ **Validation** - File type and size validation (max 10MB per file)
- 🎯 **Multi-file Support** - Upload one or multiple files at once
- 📱 **Responsive Design** - Works seamlessly on desktop and mobile devices
- 📊 **Invoice Review Dashboard** - Comprehensive 2-panel interface for reviewing extracted data
- 📋 **Excel-style Table View** - Display invoice items in a clean, tabular format
- 🎯 **Status Management** - Track invoices with Approved, Flagged, Pending, and In Review states
- 🔄 **Mock Data** - Sample invoices for UI demonstration before backend integration

## Supported File Types

- Images: JPEG, JPG, PNG, WEBP
- Documents: PDF

## Technology Stack

- **React 19** - Modern React with hooks
- **TypeScript** - Type-safe development
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework for rapid UI development

## Getting Started

### Prerequisites

- Node.js (v18 or higher)
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Hero.tsx           # Landing page hero section
│   │   ├── FileUpload.tsx     # File upload component
│   │   └── Dashboard.tsx      # Invoice review dashboard
│   ├── data/
│   │   └── mockInvoices.ts    # Mock invoice data (5 samples)
│   ├── types/
│   │   └── invoice.ts         # TypeScript type definitions
│   ├── utils/
│   │   └── api.ts             # Backend API utilities
│   ├── App.tsx                # Main application component
│   ├── main.tsx               # Application entry point
│   └── index.css              # Tailwind CSS imports
├── tailwind.config.js         # Tailwind configuration
├── postcss.config.js          # PostCSS configuration
├── DASHBOARD_USAGE.md         # Dashboard documentation
├── INTEGRATION.md             # Backend integration guide
├── index.html                 # HTML template
└── package.json               # Project dependencies
```

## Component Overview

### Hero Component
Displays the landing page with:
- Project description
- Problem statement
- Solution overview
- Key features

### FileUpload Component
Handles file uploads with:
- Drag and drop functionality
- File validation
- Image preview
- File management (add/remove)
- Ready for backend integration

### Dashboard Component
Invoice review interface with:
- **2-panel layout**: Invoice list and detail view
- **Excel-style table**: Display items with qty, rate, and totals
- **Status indicators**: Approved, Flagged, Pending, In Review
- **Action buttons**: Approve, Edit, Re-parse, Skip, Save & Send
- **Mock data**: 5 sample invoices for demonstration
- See `DASHBOARD_USAGE.md` for detailed documentation

## Backend Integration

The application is designed to send uploaded files to a backend API. The file handling logic in `App.tsx` includes a placeholder for backend integration:

```typescript
const handleFilesUpload = (files: File[]) => {
  setUploadedFiles(files)
  console.log('Files ready to send to backend:', files)
  // TODO: Integrate with backend API when ready
}
```

To integrate with your backend:
1. Add axios or fetch calls in the `handleFilesUpload` function
2. Create FormData with the uploaded files
3. Send POST request to your backend endpoint
4. Handle response and error states

## Development

The application uses:
- ESLint for code linting
- TypeScript for type checking
- Vite for hot module replacement (HMR)
- Tailwind CSS for utility-first styling

### Styling with Tailwind CSS

All components use Tailwind CSS utility classes for styling. The configuration is in `tailwind.config.js` and includes:
- Custom animations (float, move-bg)
- Extended theme colors and gradients
- Responsive breakpoints
- Custom keyframes

To customize the design, modify the Tailwind config or add custom classes in `index.css`.

## License

This project is part of the PepsiCo Order Processing system.
