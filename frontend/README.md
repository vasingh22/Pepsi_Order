# PepsiCo Order Processing Frontend

A modern React + TypeScript application for uploading and processing unstructured order documents (images and PDFs) using AI-powered OCR and LLM workflows.

## Features

- 📊 **Invoice Review Dashboard** - Comprehensive interface for reviewing extracted data
- 📤 **Integrated Upload Sidebar** - Upload files directly from the dashboard
- 📋 **Excel-style Table View** - Display invoice items in a clean, tabular format with grid borders
- 🖼️ **Image Preview** - Real-time preview of uploaded images in the upload sidebar
- 📄 **PDF Support** - Upload and process PDF documents
- ✅ **Validation** - File type and size validation (max 10MB per file)
- 🎯 **Multi-file Support** - Upload one or multiple files at once
- 🎯 **Status Management** - Track invoices with Approved, Flagged, Pending, and In Review states
- 📱 **Fully Responsive** - Works seamlessly on desktop, tablet, and mobile devices
- 🔄 **Mock Data** - Sample invoices for UI demonstration before backend integration
- 🚀 **Smart Layout** - Upload sidebar disappears after processing files for cleaner view

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
│   │   ├── Dashboard.tsx      # Invoice review dashboard with integrated upload
│   │   └── FileUpload.tsx     # File upload component (legacy - not used)
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

### Dashboard Component
All-in-one invoice review interface with:
- **Integrated upload sidebar**: Upload files directly in the dashboard
  - Drag & drop or click to browse
  - File validation and preview
  - Automatically hides after processing
- **Invoice list panel**: View all pending/flagged invoices with status badges
- **Detail view panel**: 
  - Excel-style table with grid borders (Item, HSN Code, Qty, Unit, Rate, Total)
  - Store information and invoice metadata
  - Tax calculations and totals
  - Status indicators and warning messages
- **Action buttons**: Approve, Edit, Re-parse, Skip, Save & Send
- **Responsive 3-column layout**: Adapts to 2-column when upload sidebar is hidden
- **Mock data**: 5 sample invoices for demonstration

## Backend Integration

The application is designed to send uploaded files to a backend API. The file handling logic in `Dashboard.tsx` includes a placeholder for backend integration:

```typescript
const handleProcessFiles = () => {
  if (uploadedFiles.length > 0) {
    console.log("Processing files:", uploadedFiles);
    // TODO: Send files to backend
    // For now, just hide the upload sidebar
    setShowUploadSidebar(false);
  }
};
```

To integrate with your backend:
1. Import the API utilities: `import { uploadFiles } from '../utils/api'`
2. Update the `handleProcessFiles` function to send files to backend:
```typescript
const handleProcessFiles = async () => {
  if (uploadedFiles.length > 0) {
    try {
      const files = uploadedFiles.map(f => f.file);
      const response = await uploadFiles(files);
      console.log('Files processed:', response);
      setShowUploadSidebar(false);
      // Update invoice list with response data
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Failed to process files. Please try again.');
    }
  }
};
```
3. Handle response and update the invoice list with real data

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
