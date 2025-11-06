# Invoice Review Dashboard

## Overview

The Invoice Review Dashboard provides a comprehensive interface for reviewing, editing, and approving invoice data extracted from uploaded documents.

## Features

### 📋 Two-Panel Layout

1. **Left Panel - Invoice List**
   - Shows all pending/flagged invoices
   - Color-coded status indicators:
     - 🟢 **Approved** - Successfully verified and approved
     - 🟠 **Flagged** - Requires attention (missing data, low confidence)
     - 🔵 **Pending** - Awaiting review
     - 🟣 **In Review** - Currently being processed
   - Click any invoice to view details

2. **Right Panel - Invoice Detail View**
   - Store information (name, address, GST number)
   - Invoice metadata (number, date)
   - **Excel-style table** showing:
     - Item names
     - Quantities
     - Rates (per unit)
     - Total amounts
   - Calculated totals:
     - Subtotal
     - Tax (GST with percentage)
     - Final total
   - Status indicators and warning messages
   - Action buttons for workflow management

### 🎯 Action Buttons

- **Approve** ✓ - Mark invoice as verified and approved
- **Edit Field** ✏️ - Open field-level editing mode
- **Re-parse** 🔄 - Re-run OCR/LLM parsing on the document
- **Skip** ⏭ - Move to next invoice without changes
- **Save & Send** 💾 - Save changes and send to backend

## Mock Data

Currently using mock data from `src/data/mockInvoices.ts` with 5 sample invoices:

1. **Big Bazaar** - Approved ✓
2. **Reliance Fresh** - Flagged (Missing SKU price)
3. **Sai Super Mart** - Pending (Low OCR confidence)
4. **More Megastore** - In Review (Partial total mismatch)
5. **D-Mart** - Flagged (Unreadable date)

## How It Works

### Upload Flow

1. **Upload Files** on the main page
2. Click **"Process Files"** button
3. Dashboard displays with mock invoice data
4. Review, edit, and approve invoices
5. Click **"Back to Upload"** to return

### Data Structure

Each invoice contains:
```typescript
{
  id: string;                    // Unique identifier
  invoice_number: string;        // Invoice number
  invoice_date: string;          // Date in YYYY-MM-DD format
  status: 'Approved' | 'Flagged' | 'Pending' | 'In Review';
  statusMessage?: string;        // Reason for flag/issue
  store_name: string;            // Store name
  address: string;               // Store address
  gst_number?: string;           // GST registration number
  buyer_details: {...};          // Buyer information
  seller_details: {...};         // Seller information
  items: [...];                  // Array of invoice items
  charges: {...};                // Subtotal and other charges
  tax_details: {...};            // Tax information
  total: number;                 // Final total amount
  payment_details: {...};        // Payment mode and status
}
```

### Invoice Items (Table Rows)

Each item in the table contains:
```typescript
{
  name: string;          // Product name
  hsn_code?: string;     // HSN/SAC code
  quantity: number;      // Quantity ordered
  unit?: string;         // Unit type (bottle, packet, etc.)
  rate: number;          // Price per unit
  discount?: number;     // Discount applied
  amount: number;        // Total amount (qty × rate - discount)
}
```

## Integration with Backend

When ready to integrate with real backend:

1. **Replace mock data** with actual API calls
2. **Update** `handleProcessFiles()` in `App.tsx`:
   ```typescript
   const handleProcessFiles = async () => {
     const response = await uploadFiles(uploadedFiles);
     // Use response data instead of mockInvoices
     setInvoiceData(response.invoices);
     setShowDashboard(true);
   };
   ```

3. **Add API endpoints** for:
   - Upload and process documents
   - Get invoice list
   - Get individual invoice details
   - Update invoice data
   - Approve/reject invoices
   - Re-parse documents

## Customization

### Colors and Styling

All styling uses **Tailwind CSS**. Modify colors in:
- Status badges: `getStatusColor()` function
- Buttons: Change gradient colors in button classes
- Layout: Adjust `grid-cols-*` classes for responsiveness

### Adding New Status Types

1. Add to TypeScript type in `src/types/invoice.ts`
2. Update `getStatusColor()` function
3. Update `getStatusIcon()` function

### Table Columns

To add/modify columns in the items table:
1. Update `InvoiceItem` type in `src/types/invoice.ts`
2. Add column header in `<thead>`
3. Add column data in `<tbody>`

## File Structure

```
src/
├── components/
│   ├── Dashboard.tsx          # Main dashboard component
│   ├── FileUpload.tsx         # File upload component
│   └── Hero.tsx               # Landing page hero
├── data/
│   └── mockInvoices.ts        # Mock invoice data
├── types/
│   └── invoice.ts             # TypeScript type definitions
└── App.tsx                    # Main app with routing logic
```

## Future Enhancements

- [ ] Add pagination for invoice list
- [ ] Add search/filter functionality
- [ ] Add export to Excel feature
- [ ] Add batch approval
- [ ] Add invoice comparison view
- [ ] Add audit log/history
- [ ] Add keyboard shortcuts
- [ ] Add inline editing in table
- [ ] Add drag-and-drop field mapping
- [ ] Add confidence score visualization

## Testing

Currently using static mock data. To test:

1. Upload any PDF/image files
2. Click "View Dashboard" button
3. Navigate through different invoices
4. Test all action buttons
5. Edit JSON in right panel
6. Return to upload page

All data is client-side only until backend integration.

