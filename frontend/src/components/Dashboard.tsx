import { useState, useRef } from "react";
import type { DragEvent, ChangeEvent } from "react";
import type { Invoice } from "../types/invoice";
import { mockInvoices } from "../data/mockInvoices";

interface FileWithPreview {
  file: File;
  preview?: string;
}

const Dashboard = () => {
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice>(
    mockInvoices[2]
  ); // Default to Pending one
  const [showUploadSidebar, setShowUploadSidebar] = useState(true);
  const [uploadedFiles, setUploadedFiles] = useState<FileWithPreview[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const acceptedTypes = [
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "application/pdf",
  ];
  const maxSize = 10 * 1024 * 1024; // 10MB

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Approved":
        return "text-green-600 bg-green-50";
      case "Flagged":
        return "text-orange-600 bg-orange-50";
      case "Pending":
        return "text-blue-600 bg-blue-50";
      case "In Review":
        return "text-purple-600 bg-purple-50";
      default:
        return "text-gray-600 bg-gray-50";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "Approved":
        return "✓";
      case "Flagged":
        return "⚠";
      case "Pending":
        return "○";
      case "In Review":
        return "◐";
      default:
        return "○";
    }
  };

  const handleInvoiceSelect = (invoice: Invoice) => {
    setSelectedInvoice(invoice);
  };

  const validateFile = (file: File): string | null => {
    if (!acceptedTypes.includes(file.type)) {
      return `${file.name}: Invalid file type. Only images (JPEG, PNG, WEBP) and PDFs are allowed.`;
    }
    if (file.size > maxSize) {
      return `${file.name}: File size exceeds 10MB limit.`;
    }
    return null;
  };

  const processFiles = (fileList: FileList | null) => {
    if (!fileList) return;

    const newFiles: FileWithPreview[] = [];
    const errors: string[] = [];

    Array.from(fileList).forEach((file) => {
      const error = validateFile(file);
      if (error) {
        errors.push(error);
      } else {
        const fileWithPreview: FileWithPreview = { file };

        // Generate preview for images
        if (file.type.startsWith("image/")) {
          const reader = new FileReader();
          reader.onload = (e) => {
            fileWithPreview.preview = e.target?.result as string;
            setUploadedFiles((prev) => [...prev]);
          };
          reader.readAsDataURL(file);
        }

        newFiles.push(fileWithPreview);
      }
    });

    if (errors.length > 0) {
      alert(errors.join("\n"));
    }

    if (newFiles.length > 0) {
      const updatedFiles = [...uploadedFiles, ...newFiles];
      setUploadedFiles(updatedFiles);
    }
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    processFiles(e.dataTransfer.files);
  };

  const handleFileInput = (e: ChangeEvent<HTMLInputElement>) => {
    processFiles(e.target.files);
  };

  const removeFile = (index: number) => {
    const updatedFiles = uploadedFiles.filter((_, i) => i !== index);
    setUploadedFiles(updatedFiles);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  const handleProcessFiles = () => {
    if (uploadedFiles.length > 0) {
      console.log("Processing files:", uploadedFiles);
      // TODO: Send files to backend
      // For now, just hide the upload sidebar
      setShowUploadSidebar(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-3 sm:p-4 md:p-6">
      <div className="max-w-[1800px] mx-auto">
        {/* Header */}
        <div className="bg-white rounded-xl md:rounded-2xl shadow-md p-4 sm:p-5 md:p-6 mb-4 md:mb-6">
          <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-800">
            Invoice Review Dashboard
          </h1>
        </div>

        {/* Main Content - 3 Column Layout (with conditional upload sidebar) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 md:gap-6">
          {/* Upload Sidebar - Only show if not processed */}
          {showUploadSidebar && (
            <div className="lg:col-span-3">
              <div className="bg-white rounded-xl md:rounded-2xl shadow-md p-3 sm:p-4">
                <h2 className="text-base sm:text-lg font-bold text-gray-700 mb-3 sm:mb-4">
                  Upload Documents
                </h2>

                {/* Dropzone */}
                <div
                  className={`border-2 border-dashed rounded-xl p-4 sm:p-6 text-center cursor-pointer transition-all duration-300 ${
                    isDragging
                      ? "border-[#667eea] bg-gray-100"
                      : "border-gray-300 hover:border-[#667eea] hover:bg-gray-50"
                  }`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <div className="pointer-events-none">
                    <div className="text-3xl sm:text-4xl mb-2 animate-float">
                      📁
                    </div>
                    <h3 className="text-sm sm:text-base font-semibold text-gray-800 mb-1">
                      Drop Files Here
                    </h3>
                    <p className="text-xs text-gray-600 mb-2">
                      or click to browse
                    </p>
                    <div className="text-xs text-gray-500">
                      <p>JPG, PNG, WEBP, PDF</p>
                      <p>Max 10MB</p>
                    </div>
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept="image/jpeg,image/jpg,image/png,image/webp,application/pdf"
                    onChange={handleFileInput}
                    className="hidden"
                  />
                </div>

                {/* Files Preview */}
                {uploadedFiles.length > 0 && (
                  <div className="mt-4">
                    <div className="flex justify-between items-center mb-2">
                      <h3 className="text-sm font-semibold text-gray-700">
                        Files ({uploadedFiles.length})
                      </h3>
                      <button
                        className="text-xs text-red-500 hover:text-red-600 font-semibold"
                        onClick={() => setUploadedFiles([])}
                      >
                        Clear
                      </button>
                    </div>

                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {uploadedFiles.map((fileWithPreview, index) => (
                        <div
                          key={index}
                          className="relative border border-gray-200 rounded-lg p-2 hover:border-gray-300 transition-all group"
                        >
                          <div className="flex items-center gap-2">
                            <div className="w-10 h-10 flex-shrink-0 bg-gray-100 rounded flex items-center justify-center overflow-hidden">
                              {fileWithPreview.preview ? (
                                <img
                                  src={fileWithPreview.preview}
                                  alt={fileWithPreview.file.name}
                                  className="w-full h-full object-cover"
                                />
                              ) : (
                                <span className="text-xl">📄</span>
                              )}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-xs font-semibold text-gray-800 truncate">
                                {fileWithPreview.file.name}
                              </p>
                              <p className="text-xs text-gray-500">
                                {formatFileSize(fileWithPreview.file.size)}
                              </p>
                            </div>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                removeFile(index);
                              }}
                              className="w-6 h-6 rounded-full bg-red-500 text-white text-sm flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600"
                            >
                              ×
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>

                    <button
                      onClick={handleProcessFiles}
                      className="w-full mt-4 px-4 py-2.5 bg-gradient-to-r from-[#667eea] to-[#764ba2] text-white rounded-lg text-sm font-semibold hover:shadow-lg transition-all"
                    >
                      Process {uploadedFiles.length} File
                      {uploadedFiles.length > 1 ? "s" : ""} →
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Left Sidebar - Invoice List */}
          <div
            className={showUploadSidebar ? "lg:col-span-3" : "lg:col-span-4"}
          >
            <div className="bg-white rounded-xl md:rounded-2xl shadow-md p-3 sm:p-4">
              <h2 className="text-base sm:text-lg font-bold text-gray-700 mb-3 sm:mb-4">
                Pending / Flagged Invoices
              </h2>
              <div className="space-y-2 max-h-[400px] lg:max-h-none overflow-y-auto">
                {mockInvoices.map((invoice) => (
                  <div
                    key={invoice.id}
                    onClick={() => handleInvoiceSelect(invoice)}
                    className={`p-2.5 sm:p-3 rounded-lg cursor-pointer transition-all border-2 ${
                      selectedInvoice.id === invoice.id
                        ? "border-blue-500 bg-blue-50"
                        : "border-gray-200 hover:border-gray-300 bg-white"
                    }`}
                  >
                    <div className="flex justify-between items-start mb-1">
                      <span className="font-semibold text-gray-800 text-xs sm:text-sm">
                        {invoice.id}
                      </span>
                      <span
                        className={`text-xs px-2 py-1 rounded-full font-semibold whitespace-nowrap ${getStatusColor(
                          invoice.status
                        )}`}
                      >
                        {invoice.status}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500">
                      {invoice.statusMessage || "Verified"}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right - Invoice Detail View */}
          <div
            className={showUploadSidebar ? "lg:col-span-6" : "lg:col-span-8"}
          >
            <div className="bg-white rounded-xl md:rounded-2xl shadow-md p-3 sm:p-4 md:p-6">
              {/* Invoice Header with Status */}
              <div className="mb-4 sm:mb-6">
                <div>
                  <div className="flex items-center gap-2 sm:gap-3 mb-2">
                    <span className="text-xl sm:text-2xl">
                      {getStatusIcon(selectedInvoice.status)}
                    </span>
                    <h2 className="text-base sm:text-lg md:text-xl font-bold text-gray-800 break-all">
                      Invoice ID: {selectedInvoice.invoice_number}
                    </h2>
                  </div>
                  {selectedInvoice.statusMessage && (
                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-3 py-2 flex items-start gap-2">
                      <span className="text-yellow-600 flex-shrink-0">⚠</span>
                      <span className="text-xs sm:text-sm text-yellow-800">
                        Reason for Flag: {selectedInvoice.statusMessage}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Store Info */}
              <div className="text-center mb-4 sm:mb-6 pb-4 sm:pb-6 border-b-2 border-gray-200">
                <h3 className="text-lg sm:text-xl md:text-2xl font-bold text-gray-800 mb-2">
                  {selectedInvoice.store_name}
                </h3>
                <p className="text-xs sm:text-sm text-gray-600 mb-1">
                  {selectedInvoice.address}
                </p>
                {selectedInvoice.gst_number && (
                  <p className="text-xs sm:text-sm text-gray-600">
                    GST: {selectedInvoice.gst_number}
                  </p>
                )}
              </div>

              {/* Invoice Metadata */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-4 mb-4 sm:mb-6 bg-gray-50 p-3 sm:p-4 rounded-lg">
                <div className="sm:text-left">
                  <span className="text-xs sm:text-sm font-semibold text-gray-600">
                    Invoice No:
                  </span>
                  <span className="ml-2 text-xs sm:text-sm text-gray-800 break-all">
                    {selectedInvoice.invoice_number}
                  </span>
                </div>
                <div className="sm:text-right">
                  <span className="text-xs sm:text-sm font-semibold text-gray-600">
                    Date:
                  </span>
                  <span className="ml-2 text-xs sm:text-sm text-gray-800">
                    {selectedInvoice.invoice_date}
                  </span>
                </div>
              </div>

              {/* Items Table - Excel Style */}
              <div className="mb-4 sm:mb-6 overflow-x-auto border-2 border-gray-300 rounded-lg">
                <table className="w-full border-collapse min-w-[600px]">
                  <thead>
                    <tr className="bg-gray-200">
                      <th className="border border-gray-300 p-2 sm:p-3 text-left text-xs sm:text-sm font-bold text-gray-800">
                        Item
                      </th>
                      <th className="border border-gray-300 p-2 sm:p-3 text-left text-xs sm:text-sm font-bold text-gray-800 hidden md:table-cell">
                        HSN Code
                      </th>
                      <th className="border border-gray-300 p-2 sm:p-3 text-center text-xs sm:text-sm font-bold text-gray-800">
                        Qty
                      </th>
                      <th className="border border-gray-300 p-2 sm:p-3 text-left text-xs sm:text-sm font-bold text-gray-800 hidden sm:table-cell">
                        Unit
                      </th>
                      <th className="border border-gray-300 p-2 sm:p-3 text-right text-xs sm:text-sm font-bold text-gray-800">
                        Rate
                      </th>
                      <th className="border border-gray-300 p-2 sm:p-3 text-right text-xs sm:text-sm font-bold text-gray-800">
                        Total
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedInvoice.items.map((item, index) => (
                      <tr
                        key={index}
                        className={index % 2 === 0 ? "bg-white" : "bg-gray-50"}
                      >
                        <td className="border border-gray-300 p-2 sm:p-3 text-xs sm:text-sm text-gray-800">
                          {item.name}
                        </td>
                        <td className="border border-gray-300 p-2 sm:p-3 text-xs sm:text-sm text-gray-600 hidden md:table-cell">
                          {item.hsn_code || "-"}
                        </td>
                        <td className="border border-gray-300 p-2 sm:p-3 text-xs sm:text-sm text-gray-800 text-center font-semibold">
                          {item.quantity}
                        </td>
                        <td className="border border-gray-300 p-2 sm:p-3 text-xs sm:text-sm text-gray-600 hidden sm:table-cell">
                          {item.unit || "-"}
                        </td>
                        <td className="border border-gray-300 p-2 sm:p-3 text-xs sm:text-sm text-gray-800 text-right">
                          ₹{item.rate.toFixed(2)}
                        </td>
                        <td className="border border-gray-300 p-2 sm:p-3 text-xs sm:text-sm text-gray-900 text-right font-bold bg-blue-50">
                          ₹{item.amount.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Totals Section - Excel Style */}
              <div className="border-2 border-gray-300 rounded-lg overflow-hidden">
                <table className="w-full">
                  <tbody>
                    <tr className="bg-gray-50">
                      <td className="border border-gray-300 p-2 sm:p-3 text-xs sm:text-sm font-semibold text-gray-700">
                        Subtotal
                      </td>
                      <td className="border border-gray-300 p-2 sm:p-3 text-xs sm:text-sm font-bold text-gray-900 text-right">
                        ₹{selectedInvoice.charges?.subtotal.toFixed(2)}
                      </td>
                    </tr>
                    <tr className="bg-white">
                      <td className="border border-gray-300 p-2 sm:p-3 text-xs sm:text-sm font-semibold text-gray-700">
                        {selectedInvoice.tax_details.type} (
                        {selectedInvoice.tax_details.rate}%)
                      </td>
                      <td className="border border-gray-300 p-2 sm:p-3 text-xs sm:text-sm font-bold text-gray-900 text-right">
                        ₹{selectedInvoice.tax_details.amount.toFixed(2)}
                      </td>
                    </tr>
                    <tr className="bg-green-50">
                      <td className="border border-gray-300 p-2 sm:p-3 text-sm sm:text-base font-bold text-gray-900">
                        Total
                      </td>
                      <td className="border border-gray-300 p-2 sm:p-3 text-sm sm:text-base font-bold text-green-700 text-right">
                        ₹{selectedInvoice.total.toFixed(2)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Thank You Note */}
              <div className="mt-4 sm:mt-6 text-center text-xs sm:text-sm text-gray-500 italic">
                Thank you for your business!
              </div>

              {/* Action Buttons */}
              <div className="mt-6 sm:mt-8 grid grid-cols-2 sm:grid-cols-3 gap-2 sm:gap-3">
                <button className="px-3 sm:px-6 py-2.5 sm:py-3 bg-green-500 text-white rounded-lg text-xs sm:text-base font-semibold hover:bg-green-600 transition-all flex items-center justify-center gap-1 sm:gap-2">
                  <span>✓</span>
                  <span>Approve</span>
                </button>
                <button className="px-3 sm:px-6 py-2.5 sm:py-3 bg-blue-500 text-white rounded-lg text-xs sm:text-base font-semibold hover:bg-blue-600 transition-all flex items-center justify-center gap-1 sm:gap-2">
                  <span>✏️</span>
                  <span>Edit Field</span>
                </button>
                <button className="px-3 sm:px-6 py-2.5 sm:py-3 bg-orange-500 text-white rounded-lg text-xs sm:text-base font-semibold hover:bg-orange-600 transition-all flex items-center justify-center gap-1 sm:gap-2">
                  <span>🔄</span>
                  <span>Re-parse</span>
                </button>
                <button className="px-3 sm:px-6 py-2.5 sm:py-3 bg-yellow-500 text-white rounded-lg text-xs sm:text-base font-semibold hover:bg-yellow-600 transition-all flex items-center justify-center gap-1 sm:gap-2">
                  <span>⏭</span>
                  <span>Skip</span>
                </button>
                <button className="col-span-2 px-3 sm:px-6 py-2.5 sm:py-3 bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-lg text-xs sm:text-base font-semibold hover:shadow-lg transition-all flex items-center justify-center gap-1 sm:gap-2">
                  <span>💾</span>
                  <span>Save & Send</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
