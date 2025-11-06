import { useState } from "react";
import type { Invoice } from "../types/invoice";
import { mockInvoices } from "../data/mockInvoices";

const Dashboard = () => {
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice>(
    mockInvoices[2]
  ); // Default to Pending one

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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-3 sm:p-4 md:p-6">
      <div className="max-w-[1800px] mx-auto">
        {/* Header */}
        <div className="bg-white rounded-xl md:rounded-2xl shadow-md p-4 sm:p-5 md:p-6 mb-4 md:mb-6">
          <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-800">
            Invoice Review Dashboard
          </h1>
        </div>

        {/* Main Content - 2 Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 md:gap-6">
          {/* Left Sidebar - Invoice List */}
          <div className="lg:col-span-4">
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
          <div className="lg:col-span-8">
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
