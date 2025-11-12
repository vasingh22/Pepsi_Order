import { useState, useEffect, useRef, useCallback } from "react";
import type { DragEvent, ChangeEvent } from "react";
import { uploadAndExtractPDF, listInvoices } from "../utils/api";
import * as XLSX from "xlsx";
import type {
  FileWithPreview,
  ValueWrapper,
  Address,
  LineItem,
  TaxDetail,
  PaymentInformation,
  InvoiceDataStructure,
  InvoiceData,
  ExtractedInvoiceData,
} from "../types/invoiceData";

// Helper function to safely extract values from objects or return the value directly
const extractValue = (
  val: ValueWrapper | undefined
): string | number | null => {
  if (val === null || val === undefined) return null;
  if (typeof val === "object" && val !== null && "value" in val) {
    return val.value;
  }
  return val;
};

// Helper function to safely render text
const safeRenderText = (
  val: ValueWrapper | undefined,
  defaultText: string = "N/A"
): string => {
  const extracted = extractValue(val);
  if (extracted === null || extracted === undefined) return defaultText;
  if (typeof extracted === "object") return JSON.stringify(extracted);
  return String(extracted);
};

const Dashboard = () => {
  const [invoices, setInvoices] = useState<InvoiceData[]>([]);
  const [selectedInvoice, setSelectedInvoice] = useState<InvoiceData | null>(
    null
  );
  const [showUploadSidebar, setShowUploadSidebar] = useState(true);
  const [uploadedFiles, setUploadedFiles] = useState<FileWithPreview[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editedJson, setEditedJson] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const acceptedTypes = [
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "application/pdf",
  ];
  const maxSize = 10 * 1024 * 1024; // 10MB

  const loadInvoices = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await listInvoices();
      setInvoices(response.invoices || []);
      if (
        response.invoices &&
        response.invoices.length > 0 &&
        !selectedInvoice
      ) {
        setSelectedInvoice(response.invoices[0]);
      }
    } catch (err) {
      setError(
        "Failed to load invoices. Please make sure the backend is running."
      );
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [selectedInvoice]);

  // Load invoices on mount
  useEffect(() => {
    loadInvoices();
  }, [loadInvoices]);

  // Update edited JSON when selected invoice changes
  useEffect(() => {
    if (selectedInvoice) {
      setEditedJson(JSON.stringify(selectedInvoice.data, null, 2));
    }
  }, [selectedInvoice]);

  // Helper to extract invoice data from different JSON structures
  const extractInvoiceData = (
    data: InvoiceDataStructure
  ): ExtractedInvoiceData => {
    const addressInfo = data.address_information || {};
    const contactInfo = addressInfo.contact_information || {};
    const paymentInfo = data.payment_information || {};
    const financialInfo =
      data.financial_information || data.financial_summary || {};

    // Handle structure 1: core_invoice_fields format
    if (data.core_invoice_fields) {
      return {
        sellerName: extractValue(data.core_invoice_fields.seller_name) as
          | string
          | null,
        buyerName: extractValue(data.core_invoice_fields.buyer_name) as
          | string
          | null,
        invoiceNumber: extractValue(data.core_invoice_fields.invoice_number) as
          | string
          | null,
        orderNumber: extractValue(data.core_invoice_fields.order_number) as
          | string
          | null,
        poNumber: extractValue(data.core_invoice_fields.po_number) as
          | string
          | null,
        invoiceDate: extractValue(data.core_invoice_fields.invoice_date) as
          | string
          | null,
        orderDate: extractValue(data.core_invoice_fields.order_date) as
          | string
          | null,
        poDate: extractValue(data.core_invoice_fields.po_date) as string | null,
        deliveryDate: extractValue(data.core_invoice_fields.delivery_date) as
          | string
          | null,
        customerId: extractValue(data.core_invoice_fields.customer_id) as
          | string
          | null,
        gstNumber: extractValue(data.core_invoice_fields.gst_number) as
          | string
          | null,
        taxId: extractValue(data.core_invoice_fields.tax_id) as string | null,
        buyerAddress: addressInfo.buyer_address || null,
        sellerAddress: addressInfo.seller_address || null,
        shipToAddress: addressInfo.ship_to_address || null,
        contactInfo: contactInfo,
        lineItems: data.line_items || [],
        totals: data.totals_summary || null,
        financial: financialInfo,
        payment: paymentInfo,
      };
    }

    // Handle structure 2: seller_information format
    if (data.seller_information || data.buyer_information) {
      return {
        sellerName: extractValue(data.seller_information?.seller_name) as
          | string
          | null,
        buyerName: extractValue(data.buyer_information?.buyer_name) as
          | string
          | null,
        invoiceNumber: extractValue(data.invoice_details?.invoice_number) as
          | string
          | null,
        orderNumber: extractValue(data.invoice_details?.order_number) as
          | string
          | null,
        poNumber: extractValue(data.invoice_details?.po_number) as
          | string
          | null,
        invoiceDate: extractValue(data.invoice_details?.invoice_date) as
          | string
          | null,
        orderDate: extractValue(data.invoice_details?.order_date) as
          | string
          | null,
        poDate: extractValue(data.invoice_details?.po_date) as string | null,
        deliveryDate: extractValue(data.invoice_details?.delivery_date) as
          | string
          | null,
        customerId: null,
        gstNumber: extractValue(data.seller_information?.gst_number) as
          | string
          | null,
        taxId: extractValue(data.seller_information?.tax_id) as string | null,
        buyerAddress: data.buyer_information?.buyer_address || null,
        sellerAddress: data.seller_information?.seller_address || null,
        shipToAddress: data.buyer_information?.ship_to_address || null,
        contactInfo: contactInfo,
        lineItems: data.line_items || [],
        totals: null,
        financial: financialInfo,
        payment: paymentInfo,
      };
    }

    // Handle structure 3: flat structure
    return {
      sellerName: extractValue(data.seller_name) as string | null,
      buyerName: extractValue(data.buyer_name) as string | null,
      invoiceNumber: extractValue(data.invoice_number) as string | null,
      orderNumber: extractValue(data.order_number) as string | null,
      poNumber: extractValue(data.po_number || data.PO_number) as string | null,
      invoiceDate: extractValue(data.invoice_date) as string | null,
      orderDate: extractValue(data.order_date) as string | null,
      poDate: extractValue(data.po_date || data.PO_date) as string | null,
      deliveryDate: extractValue(data.delivery_date) as string | null,
      customerId: null,
      gstNumber: extractValue(data.gst_number) as string | null,
      taxId: extractValue(data.tax_id) as string | null,
      buyerAddress: data.buyer_address || null,
      sellerAddress: data.seller_address || null,
      shipToAddress: data.ship_to_address || null,
      contactInfo: contactInfo,
      lineItems: data.line_items || [],
      totals: null,
      financial: financialInfo,
      payment: paymentInfo,
    };
  };

  const getStatusFromInvoice = (invoiceData: InvoiceDataStructure): string => {
    // Determine status based on invoice data
    if (!invoiceData) return "Pending";

    const invoice = extractInvoiceData(invoiceData);
    const hasOrderNumber =
      !!invoice.orderNumber || !!invoice.poNumber || !!invoice.invoiceNumber;
    const hasBuyer = !!invoice.buyerName;
    const hasDate =
      !!invoice.orderDate || !!invoice.poDate || !!invoice.invoiceDate;
    const hasItems = invoice.lineItems && invoice.lineItems.length > 0;

    // Check for missing critical data
    if (!hasOrderNumber || !hasBuyer || !hasDate) {
      return "Flagged";
    }

    // Check if any line items are missing prices
    if (hasItems) {
      const hasMissingPrices = invoice.lineItems.some((item: LineItem) => {
        const price = extractValue(item.unit_price || item.rate);
        const total = extractValue(item.total || item.amount);
        return price === null || total === null;
      });
      if (hasMissingPrices) {
        return "Flagged";
      }
    }

    // Check for totals mismatch
    const totalsMismatch =
      invoiceData.totals_summary?.total_mismatch ||
      invoiceData.source_metadata?.totals_verification?.status === "mismatch";
    if (totalsMismatch) {
      return "In Review";
    }

    return "Pending";
  };

  const getStatusMessage = (invoiceData: InvoiceDataStructure): string => {
    if (!invoiceData) return "No data available";

    const invoice = extractInvoiceData(invoiceData);

    if (!invoice.orderNumber && !invoice.poNumber && !invoice.invoiceNumber) {
      return "Missing order/PO number";
    }
    if (!invoice.buyerName) {
      return "Missing buyer information";
    }
    if (!invoice.orderDate && !invoice.poDate && !invoice.invoiceDate) {
      return "Missing date information";
    }

    if (invoice.lineItems && invoice.lineItems.length > 0) {
      const hasMissingPrices = invoice.lineItems.some((item: LineItem) => {
        const price = extractValue(item.unit_price || item.rate);
        const total = extractValue(item.total || item.amount);
        return price === null || total === null;
      });
      if (hasMissingPrices) {
        return "Missing SKU prices";
      }
    }

    const totalsMismatch =
      invoiceData.totals_summary?.total_mismatch ||
      invoiceData.source_metadata?.totals_verification?.status === "mismatch";
    if (totalsMismatch) {
      return "Total mismatch detected";
    }

    return "Ready for review";
  };

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

  const handleInvoiceSelect = (invoice: InvoiceData) => {
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

  const handleProcessFiles = async () => {
    if (uploadedFiles.length === 0) return;

    setIsProcessing(true);
    setError(null);

    try {
      // Process each file
      for (const fileWithPreview of uploadedFiles) {
        await uploadAndExtractPDF(fileWithPreview.file);
      }

      // Reload invoices after processing
      await loadInvoices();

      // Clear uploaded files and hide upload sidebar
      setUploadedFiles([]);
      setShowUploadSidebar(false);

      alert(`Successfully processed ${uploadedFiles.length} file(s)!`);
    } catch (err) {
      setError("Failed to process files. Please try again.");
      console.error(err);
      alert("Error processing files. Please check the console for details.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleJsonChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    const newJson = e.target.value;
    setEditedJson(newJson);

    // Try to parse and update the preview in real-time
    try {
      const parsed = JSON.parse(newJson) as InvoiceDataStructure;
      if (selectedInvoice) {
        setSelectedInvoice({
          ...selectedInvoice,
          data: parsed,
        });
      }
    } catch (err) {
      // Invalid JSON - don't update the preview, but keep the text in the editor
      // The user can continue editing to fix the JSON
      console.error("JSON parse error (preview not updated):", err);
    }
  };

  const handleSaveJson = () => {
    try {
      const parsed = JSON.parse(editedJson) as InvoiceDataStructure;
      if (selectedInvoice) {
        setSelectedInvoice({
          ...selectedInvoice,
          data: parsed,
        });
        alert("JSON saved successfully!");
      }
    } catch (err) {
      console.error("JSON parse error:", err);
      alert("Invalid JSON format. Please check your syntax.");
    }
  };

  const handleExportToExcel = () => {
    if (!selectedInvoice) {
      alert("Please select an invoice to export.");
      return;
    }

    const data = selectedInvoice.data;
    const invoice = extractInvoiceData(data);

    // Create a new workbook
    const workbook = XLSX.utils.book_new();

    // Helper function to format address
    const formatAddress = (address: Address | string | null): string => {
      if (!address) return "";
      if (typeof address === "string") return address;
      if (address.full_address) return address.full_address;
      const parts = [
        address.street_address,
        [address.city, address.state, address.zip_code]
          .filter(Boolean)
          .join(", "),
        address.country,
      ].filter(Boolean);
      return parts.join("\n");
    };

    // Sheet 1: Invoice Summary
    const summaryData = [
      ["Invoice Summary", ""],
      ["", ""],
      ["Buyer Name", safeRenderText(invoice.buyerName)],
      ["Buyer Address", formatAddress(invoice.buyerAddress)],
      ["", ""],
      ["Seller Name", safeRenderText(invoice.sellerName)],
      ["Seller Address", formatAddress(invoice.sellerAddress)],
      ["", ""],
      ["Ship To Address", formatAddress(invoice.shipToAddress)],
      ["", ""],
      ["PO Number", safeRenderText(invoice.poNumber)],
      ["Order Number", safeRenderText(invoice.orderNumber)],
      ["Invoice Number", safeRenderText(invoice.invoiceNumber)],
      [
        "Order Date",
        safeRenderText(
          invoice.orderDate || invoice.poDate || invoice.invoiceDate
        ),
      ],
      ["Delivery Date", safeRenderText(invoice.deliveryDate)],
      ["Customer ID", safeRenderText(invoice.customerId)],
      ["GST Number", safeRenderText(invoice.gstNumber)],
      ["Tax ID", safeRenderText(invoice.taxId)],
      ["", ""],
    ];

    // Add contact information
    if (invoice.contactInfo) {
      summaryData.push(["Contact Information", ""]);
      if (invoice.contactInfo.phone) {
        summaryData.push(["Phone", safeRenderText(invoice.contactInfo.phone)]);
      }
      if (invoice.contactInfo.email) {
        summaryData.push(["Email", safeRenderText(invoice.contactInfo.email)]);
      }
      if (invoice.contactInfo.seller_contact) {
        summaryData.push([
          "Seller Contact",
          safeRenderText(invoice.contactInfo.seller_contact),
        ]);
      }
      if (invoice.contactInfo.buyer_contact_person) {
        summaryData.push([
          "Buyer Contact",
          safeRenderText(invoice.contactInfo.buyer_contact_person),
        ]);
      }
      summaryData.push(["", ""]);
    }

    // Add financial summary
    const subtotal = extractValue(
      invoice.totals?.subtotal || invoice.financial?.subtotal
    );
    const tax = extractValue(
      invoice.totals?.tax || invoice.financial?.tax_details?.[0]?.amount
    );
    const grandTotal = extractValue(
      invoice.totals?.total ||
        invoice.totals?.grand_total ||
        invoice.financial?.grand_total
    );

    summaryData.push(["Financial Summary", ""]);
    if (subtotal !== null && subtotal !== undefined) {
      summaryData.push([
        "Subtotal",
        `${invoice.financial?.currency || "$"}${parseFloat(
          String(subtotal)
        ).toFixed(2)}`,
      ]);
    }
    if (
      invoice.financial?.tax_details &&
      Array.isArray(invoice.financial.tax_details)
    ) {
      invoice.financial.tax_details.forEach((taxDetail: TaxDetail) => {
        const taxType = extractValue(taxDetail.type) || "Tax";
        const taxRate = extractValue(taxDetail.rate);
        const taxAmount = extractValue(taxDetail.amount);
        if (taxAmount !== null && taxAmount !== undefined) {
          summaryData.push([
            `${taxType}${
              taxRate !== null && taxRate !== undefined ? ` (${taxRate}%)` : ""
            }`,
            `${invoice.financial?.currency || "$"}${parseFloat(
              String(taxAmount)
            ).toFixed(2)}`,
          ]);
        }
      });
    } else if (tax !== null && tax !== undefined) {
      summaryData.push([
        "Tax",
        `${invoice.financial?.currency || "$"}${parseFloat(String(tax)).toFixed(
          2
        )}`,
      ]);
    }
    if (
      invoice.financial?.discount_total !== null &&
      invoice.financial?.discount_total !== undefined
    ) {
      summaryData.push([
        "Discount Total",
        `-${invoice.financial?.currency || "$"}${parseFloat(
          String(extractValue(invoice.financial.discount_total))
        ).toFixed(2)}`,
      ]);
    }
    if (
      invoice.financial?.shipping_charges !== null &&
      invoice.financial?.shipping_charges !== undefined
    ) {
      summaryData.push([
        "Shipping Charges",
        `${invoice.financial?.currency || "$"}${parseFloat(
          String(extractValue(invoice.financial.shipping_charges))
        ).toFixed(2)}`,
      ]);
    }
    if (grandTotal !== null && grandTotal !== undefined) {
      summaryData.push([
        "Grand Total",
        `${invoice.financial?.currency || "$"}${parseFloat(
          String(grandTotal)
        ).toFixed(2)}`,
      ]);
    }

    // Add payment information
    if (invoice.payment) {
      summaryData.push(["", ""]);
      summaryData.push(["Payment Information", ""]);
      if (invoice.payment.payment_terms) {
        summaryData.push([
          "Payment Terms",
          safeRenderText(invoice.payment.payment_terms),
        ]);
      }
      if (invoice.payment.payment_mode) {
        summaryData.push([
          "Payment Mode",
          safeRenderText(invoice.payment.payment_mode),
        ]);
      }
      if (invoice.payment.due_date) {
        summaryData.push([
          "Due Date",
          safeRenderText(invoice.payment.due_date),
        ]);
      }
    }

    const summarySheet = XLSX.utils.aoa_to_sheet(summaryData);
    XLSX.utils.book_append_sheet(workbook, summarySheet, "Invoice Summary");

    // Sheet 2: Line Items
    if (invoice.lineItems && invoice.lineItems.length > 0) {
      const lineItemsData = [
        [
          "Item ID",
          "Material ID",
          "Product Code",
          "Description",
          "Quantity",
          "Unit",
          "Unit Price",
          "Discount",
          "Total",
          "HSN Code",
          "Other Details",
        ],
      ];

      invoice.lineItems.forEach((item: LineItem) => {
        const itemId = extractValue(item.item_id);
        const materialId = extractValue(item.material_id);
        const productCode = extractValue(item.product_code);
        const description = extractValue(item.description || item.name);
        const quantity = extractValue(item.quantity);
        const unit = extractValue(item.unit);
        const unitPrice = extractValue(item.unit_price || item.rate);
        const discount = extractValue(item.discount);
        const total = extractValue(item.total || item.amount);
        const hsnCode = extractValue(item.hsn_code);
        const otherDetails = extractValue(item.other_details);

        lineItemsData.push([
          safeRenderText(itemId, "-"),
          safeRenderText(materialId, "-"),
          safeRenderText(productCode, "-"),
          safeRenderText(description, "-"),
          safeRenderText(quantity, "-"),
          safeRenderText(unit, "-"),
          unitPrice !== null && unitPrice !== undefined
            ? parseFloat(String(unitPrice)).toFixed(2)
            : "-",
          discount !== null && discount !== undefined
            ? parseFloat(String(discount)).toFixed(2)
            : "-",
          total !== null && total !== undefined
            ? parseFloat(String(total)).toFixed(2)
            : "-",
          safeRenderText(hsnCode, "-"),
          safeRenderText(otherDetails, "-"),
        ]);
      });

      const lineItemsSheet = XLSX.utils.aoa_to_sheet(lineItemsData);
      XLSX.utils.book_append_sheet(workbook, lineItemsSheet, "Line Items");
    }

    // Generate filename
    const orderNumber = safeRenderText(
      invoice.orderNumber ||
        invoice.poNumber ||
        invoice.invoiceNumber ||
        "Invoice"
    );
    const filename = `${orderNumber}_${
      new Date().toISOString().split("T")[0]
    }.xlsx`;

    // Write the file
    XLSX.writeFile(workbook, filename);
  };

  const renderInvoiceDetails = () => {
    if (!selectedInvoice) {
      return (
        <div className="flex items-center justify-center h-full text-gray-500">
          No invoice selected
        </div>
      );
    }

    const data = selectedInvoice.data;
    const invoice = extractInvoiceData(data);
    const status = getStatusFromInvoice(data);
    const statusMessage = getStatusMessage(data);

    // Get totals from either totals_summary or financial_summary
    const subtotal = extractValue(
      invoice.totals?.subtotal || invoice.financial?.subtotal
    );
    const tax = extractValue(
      invoice.totals?.tax || invoice.financial?.tax_details?.[0]?.amount
    );
    const grandTotal = extractValue(
      invoice.totals?.total ||
        invoice.totals?.grand_total ||
        invoice.financial?.grand_total
    );

    return (
      <div className="space-y-4">
        {/* Status Header */}
        <div className="mb-4">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-2xl">{getStatusIcon(status)}</span>
            <h2 className="text-xl font-bold text-gray-800 break-all">
              Order:{" "}
              {safeRenderText(
                invoice.orderNumber || invoice.poNumber || invoice.invoiceNumber
              )}
            </h2>
            <span
              className={`text-xs px-3 py-1 rounded-full font-semibold ${getStatusColor(
                status
              )}`}
            >
              {status}
            </span>
          </div>
          {statusMessage && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-3 py-2 flex items-start gap-2">
              <span className="text-yellow-600">⚠</span>
              <span className="text-sm text-yellow-800">{statusMessage}</span>
            </div>
          )}
        </div>

        {/* Buyer/Seller Info - Excel Style */}
        <div className="border-2 border-gray-400 rounded overflow-hidden w-full">
          <table
            className="w-full border-collapse table-fixed"
            style={{ minWidth: "100%" }}
          >
            <tbody>
              <tr className="bg-gray-200">
                <td
                  className="border-2 border-gray-500 p-2 font-bold text-gray-900 text-center"
                  style={{ width: "15%" }}
                >
                  Buyer
                </td>
                <td
                  className="border-2 border-gray-500 p-2 text-gray-800"
                  style={{ width: "35%" }}
                >
                  <div className="font-semibold mb-1">
                    {safeRenderText(invoice.buyerName, "N/A")}
                  </div>
                  {invoice.buyerAddress && (
                    <div className="text-xs text-gray-600">
                      {typeof invoice.buyerAddress === "string" ? (
                        <div>{invoice.buyerAddress}</div>
                      ) : (
                        <>
                          {invoice.buyerAddress.full_address && (
                            <div className="whitespace-pre-line">
                              {safeRenderText(
                                invoice.buyerAddress.full_address
                              )}
                            </div>
                          )}
                          {!invoice.buyerAddress.full_address && (
                            <>
                              {invoice.buyerAddress.street_address && (
                                <div>
                                  {safeRenderText(
                                    invoice.buyerAddress.street_address
                                  )}
                                </div>
                              )}
                              {(invoice.buyerAddress.city ||
                                invoice.buyerAddress.state ||
                                invoice.buyerAddress.zip_code) && (
                                <div>
                                  {[
                                    invoice.buyerAddress.city,
                                    invoice.buyerAddress.state,
                                    invoice.buyerAddress.zip_code,
                                  ]
                                    .filter(Boolean)
                                    .join(", ")}
                                </div>
                              )}
                              {invoice.buyerAddress.country && (
                                <div>
                                  {safeRenderText(invoice.buyerAddress.country)}
                                </div>
                              )}
                            </>
                          )}
                        </>
                      )}
                    </div>
                  )}
                </td>
                <td
                  className="border-2 border-gray-500 p-2 font-bold text-gray-900 text-center"
                  style={{ width: "15%" }}
                >
                  Seller
                </td>
                <td
                  className="border-2 border-gray-500 p-2 text-gray-800"
                  style={{ width: "35%" }}
                >
                  <div className="font-semibold mb-1">
                    {safeRenderText(invoice.sellerName, "N/A")}
                  </div>
                  {invoice.sellerAddress && (
                    <div className="text-xs text-gray-600">
                      {typeof invoice.sellerAddress === "string" ? (
                        <div>{invoice.sellerAddress}</div>
                      ) : (
                        <>
                          {invoice.sellerAddress.full_address && (
                            <div className="whitespace-pre-line">
                              {safeRenderText(
                                invoice.sellerAddress.full_address
                              )}
                            </div>
                          )}
                          {!invoice.sellerAddress.full_address && (
                            <>
                              {invoice.sellerAddress.street_address && (
                                <div>
                                  {safeRenderText(
                                    invoice.sellerAddress.street_address
                                  )}
                                </div>
                              )}
                              {(invoice.sellerAddress.city ||
                                invoice.sellerAddress.state ||
                                invoice.sellerAddress.zip_code) && (
                                <div>
                                  {[
                                    invoice.sellerAddress.city,
                                    invoice.sellerAddress.state,
                                    invoice.sellerAddress.zip_code,
                                  ]
                                    .filter(Boolean)
                                    .join(", ")}
                                </div>
                              )}
                              {invoice.sellerAddress.country && (
                                <div>
                                  {safeRenderText(
                                    invoice.sellerAddress.country
                                  )}
                                </div>
                              )}
                            </>
                          )}
                        </>
                      )}
                    </div>
                  )}
                </td>
              </tr>
              {invoice.shipToAddress && (
                <tr className="bg-white">
                  <td className="border-2 border-gray-500 p-2 font-bold text-gray-900">
                    Ship To
                  </td>
                  <td
                    colSpan={3}
                    className="border-2 border-gray-500 p-2 text-gray-800"
                  >
                    {typeof invoice.shipToAddress === "string" ? (
                      <div>{invoice.shipToAddress}</div>
                    ) : (
                      <>
                        {invoice.shipToAddress.full_address && (
                          <div className="whitespace-pre-line">
                            {safeRenderText(invoice.shipToAddress.full_address)}
                          </div>
                        )}
                        {!invoice.shipToAddress.full_address && (
                          <>
                            {invoice.shipToAddress.street_address && (
                              <div>
                                {safeRenderText(
                                  invoice.shipToAddress.street_address
                                )}
                              </div>
                            )}
                            {(invoice.shipToAddress.city ||
                              invoice.shipToAddress.state ||
                              invoice.shipToAddress.zip_code) && (
                              <div>
                                {[
                                  invoice.shipToAddress.city,
                                  invoice.shipToAddress.state,
                                  invoice.shipToAddress.zip_code,
                                ]
                                  .filter(Boolean)
                                  .join(", ")}
                              </div>
                            )}
                            {invoice.shipToAddress.country && (
                              <div>
                                {safeRenderText(invoice.shipToAddress.country)}
                              </div>
                            )}
                          </>
                        )}
                      </>
                    )}
                  </td>
                </tr>
              )}
              {invoice.contactInfo &&
                Object.keys(invoice.contactInfo).length > 0 && (
                  <tr className="bg-gray-50">
                    <td className="border-2 border-gray-500 p-2 font-bold text-gray-900">
                      Contact Info
                    </td>
                    <td
                      colSpan={3}
                      className="border-2 border-gray-500 p-2 text-gray-800 text-sm"
                    >
                      {invoice.contactInfo.phone && (
                        <span>
                          Phone: {safeRenderText(invoice.contactInfo.phone)}
                        </span>
                      )}
                      {invoice.contactInfo.email && (
                        <span className="ml-4">
                          Email: {safeRenderText(invoice.contactInfo.email)}
                        </span>
                      )}
                      {invoice.contactInfo.seller_contact && (
                        <span className="ml-4">
                          Seller:{" "}
                          {safeRenderText(invoice.contactInfo.seller_contact)}
                        </span>
                      )}
                      {invoice.contactInfo.buyer_contact_person && (
                        <span className="ml-4">
                          Contact:{" "}
                          {safeRenderText(
                            invoice.contactInfo.buyer_contact_person
                          )}
                        </span>
                      )}
                      {invoice.contactInfo.shipping_contact_phone && (
                        <span className="ml-4">
                          Shipping Phone:{" "}
                          {safeRenderText(
                            invoice.contactInfo.shipping_contact_phone
                          )}
                        </span>
                      )}
                    </td>
                  </tr>
                )}
            </tbody>
          </table>
        </div>

        {/* Order Details - Excel Style */}
        <div className="border-2 border-gray-400 rounded overflow-hidden w-full">
          <table
            className="w-full border-collapse table-fixed"
            style={{ minWidth: "100%" }}
          >
            <tbody>
              <tr className="bg-gray-200">
                <td
                  className="border-2 border-gray-500 p-2 font-bold text-gray-900"
                  style={{ width: "15%" }}
                >
                  PO Number
                </td>
                <td
                  className="border-2 border-gray-500 p-2 text-gray-800"
                  style={{ width: "18%" }}
                >
                  {safeRenderText(invoice.poNumber)}
                </td>
                <td
                  className="border-2 border-gray-500 p-2 font-bold text-gray-900"
                  style={{ width: "15%" }}
                >
                  Order Number
                </td>
                <td
                  className="border-2 border-gray-500 p-2 text-gray-800"
                  style={{ width: "18%" }}
                >
                  {safeRenderText(invoice.orderNumber)}
                </td>
                <td
                  className="border-2 border-gray-500 p-2 font-bold text-gray-900"
                  style={{ width: "15%" }}
                >
                  Invoice Number
                </td>
                <td
                  className="border-2 border-gray-500 p-2 text-gray-800"
                  style={{ width: "19%" }}
                >
                  {safeRenderText(invoice.invoiceNumber)}
                </td>
              </tr>
              <tr className="bg-white">
                <td className="border-2 border-gray-500 p-2 font-bold text-gray-900">
                  Order Date
                </td>
                <td className="border-2 border-gray-500 p-2 text-gray-800">
                  {safeRenderText(
                    invoice.orderDate || invoice.poDate || invoice.invoiceDate
                  )}
                </td>
                <td className="border-2 border-gray-500 p-2 font-bold text-gray-900">
                  Delivery Date
                </td>
                <td className="border-2 border-gray-500 p-2 text-gray-800">
                  {safeRenderText(invoice.deliveryDate)}
                </td>
                <td className="border-2 border-gray-500 p-2 font-bold text-gray-900">
                  Customer ID
                </td>
                <td className="border-2 border-gray-500 p-2 text-gray-800">
                  {safeRenderText(invoice.customerId)}
                </td>
              </tr>
              {(invoice.gstNumber || invoice.taxId) && (
                <tr className="bg-gray-50">
                  <td className="border-2 border-gray-500 p-2 font-bold text-gray-900">
                    GST Number
                  </td>
                  <td className="border-2 border-gray-500 p-2 text-gray-800">
                    {safeRenderText(invoice.gstNumber)}
                  </td>
                  <td className="border-2 border-gray-500 p-2 font-bold text-gray-900">
                    Tax ID
                  </td>
                  <td
                    className="border-2 border-gray-500 p-2 text-gray-800"
                    colSpan={3}
                  >
                    {safeRenderText(invoice.taxId)}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Line Items - Excel Style */}
        {invoice.lineItems.length > 0 && (
          <div className="overflow-x-auto border-2 border-gray-400 rounded w-full">
            <table
              className="w-full border-collapse table-fixed"
              style={{ minWidth: "100%", width: "100%" }}
            >
              <thead>
                <tr className="bg-gray-300">
                  <th
                    className="border-2 border-gray-500 p-2 text-left text-xs font-bold text-gray-900"
                    style={{ width: "8%" }}
                  >
                    Item ID
                  </th>
                  <th
                    className="border-2 border-gray-500 p-2 text-left text-xs font-bold text-gray-900"
                    style={{ width: "8%" }}
                  >
                    Material ID
                  </th>
                  <th
                    className="border-2 border-gray-500 p-2 text-left text-xs font-bold text-gray-900"
                    style={{ width: "8%" }}
                  >
                    Product Code
                  </th>
                  <th
                    className="border-2 border-gray-500 p-2 text-left text-xs font-bold text-gray-900"
                    style={{ width: "25%" }}
                  >
                    Description
                  </th>
                  <th
                    className="border-2 border-gray-500 p-2 text-center text-xs font-bold text-gray-900"
                    style={{ width: "7%" }}
                  >
                    Quantity
                  </th>
                  <th
                    className="border-2 border-gray-500 p-2 text-center text-xs font-bold text-gray-900"
                    style={{ width: "6%" }}
                  >
                    Unit
                  </th>
                  <th
                    className="border-2 border-gray-500 p-2 text-right text-xs font-bold text-gray-900"
                    style={{ width: "9%" }}
                  >
                    Unit Price
                  </th>
                  <th
                    className="border-2 border-gray-500 p-2 text-right text-xs font-bold text-gray-900"
                    style={{ width: "7%" }}
                  >
                    Discount
                  </th>
                  <th
                    className="border-2 border-gray-500 p-2 text-right text-xs font-bold text-gray-900"
                    style={{ width: "9%" }}
                  >
                    Total
                  </th>
                  <th
                    className="border-2 border-gray-500 p-2 text-left text-xs font-bold text-gray-900"
                    style={{ width: "8%" }}
                  >
                    HSN Code
                  </th>
                  <th
                    className="border-2 border-gray-500 p-2 text-left text-xs font-bold text-gray-900"
                    style={{ width: "5%" }}
                  >
                    Other Details
                  </th>
                </tr>
              </thead>
              <tbody>
                {invoice.lineItems.map((item: LineItem, index: number) => {
                  const itemId = extractValue(item.item_id);
                  const materialId = extractValue(item.material_id);
                  const productCode = extractValue(item.product_code);
                  const description = extractValue(
                    item.description || item.name
                  );
                  const quantity = extractValue(item.quantity);
                  const unit = extractValue(item.unit);
                  const unitPrice = extractValue(item.unit_price || item.rate);
                  const discount = extractValue(item.discount);
                  const total = extractValue(item.total || item.amount);
                  const hsnCode = extractValue(item.hsn_code);
                  const otherDetails = extractValue(item.other_details);

                  return (
                    <tr
                      key={index}
                      className={
                        index % 2 === 0
                          ? "bg-white hover:bg-blue-50"
                          : "bg-gray-50 hover:bg-blue-50"
                      }
                    >
                      <td className="border border-gray-400 p-1.5 text-xs text-gray-800 font-medium">
                        {safeRenderText(itemId, "-")}
                      </td>
                      <td className="border border-gray-400 p-1.5 text-xs text-gray-800 font-medium">
                        {safeRenderText(materialId, "-")}
                      </td>
                      <td className="border border-gray-400 p-1.5 text-xs text-gray-800">
                        {safeRenderText(productCode, "-")}
                      </td>
                      <td className="border border-gray-400 p-1.5 text-xs text-gray-800">
                        {safeRenderText(description, "-")}
                      </td>
                      <td className="border border-gray-400 p-1.5 text-xs text-gray-800 text-center font-semibold">
                        {safeRenderText(quantity, "-")}
                      </td>
                      <td className="border border-gray-400 p-1.5 text-xs text-gray-600 text-center">
                        {safeRenderText(unit, "-")}
                      </td>
                      <td className="border border-gray-400 p-1.5 text-xs text-gray-800 text-right font-medium">
                        {unitPrice !== null && unitPrice !== undefined
                          ? `$${parseFloat(String(unitPrice)).toFixed(2)}`
                          : "-"}
                      </td>
                      <td className="border border-gray-400 p-1.5 text-xs text-gray-800 text-right">
                        {discount !== null && discount !== undefined
                          ? `$${parseFloat(String(discount)).toFixed(2)}`
                          : "-"}
                      </td>
                      <td
                        className={`border border-gray-400 p-1.5 text-xs text-gray-900 text-right font-bold ${
                          total === null || total === undefined
                            ? "bg-red-100"
                            : "bg-green-50"
                        }`}
                      >
                        {total !== null && total !== undefined
                          ? `$${parseFloat(String(total)).toFixed(2)}`
                          : "-"}
                      </td>
                      <td className="border border-gray-400 p-1.5 text-xs text-gray-600">
                        {safeRenderText(hsnCode, "-")}
                      </td>
                      <td className="border border-gray-400 p-1.5 text-xs text-gray-600">
                        {safeRenderText(otherDetails, "-")}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Financial Summary - Excel Style */}
        <div className="border-2 border-gray-400 rounded overflow-hidden w-full">
          <table
            className="w-full border-collapse table-fixed"
            style={{ minWidth: "100%" }}
          >
            <thead>
              <tr className="bg-gray-300">
                <th
                  className="border-2 border-gray-500 p-2 text-left text-sm font-bold text-gray-900"
                  style={{ width: "70%" }}
                >
                  Financial Summary
                </th>
                <th
                  className="border-2 border-gray-500 p-2 text-right text-sm font-bold text-gray-900"
                  style={{ width: "30%" }}
                >
                  Amount
                </th>
              </tr>
            </thead>
            <tbody>
              {subtotal !== null && subtotal !== undefined ? (
                <tr className="bg-white">
                  <td className="border-2 border-gray-500 p-2 text-sm font-semibold text-gray-800">
                    Subtotal
                  </td>
                  <td className="border-2 border-gray-500 p-2 text-sm font-semibold text-gray-900 text-right">
                    {invoice.financial?.currency || "$"}
                    {parseFloat(String(subtotal)).toFixed(2)}
                  </td>
                </tr>
              ) : null}
              {invoice.financial?.tax_details &&
              Array.isArray(invoice.financial.tax_details) &&
              invoice.financial.tax_details.length > 0
                ? invoice.financial.tax_details.map(
                    (taxDetail: TaxDetail, idx: number) => {
                      const taxType = extractValue(taxDetail.type) || "Tax";
                      const taxRate = extractValue(taxDetail.rate);
                      const taxAmount = extractValue(taxDetail.amount);
                      return (
                        <tr key={idx} className="bg-white">
                          <td className="border-2 border-gray-500 p-2 text-sm font-semibold text-gray-800">
                            {taxType}{" "}
                            {taxRate !== null && taxRate !== undefined
                              ? `(${taxRate}%)`
                              : ""}
                          </td>
                          <td className="border-2 border-gray-500 p-2 text-sm font-semibold text-gray-900 text-right">
                            {invoice.financial?.currency || "$"}
                            {taxAmount !== null && taxAmount !== undefined
                              ? parseFloat(String(taxAmount)).toFixed(2)
                              : "0.00"}
                          </td>
                        </tr>
                      );
                    }
                  )
                : null}
              {tax !== null &&
              tax !== undefined &&
              (!invoice.financial?.tax_details ||
                invoice.financial.tax_details.length === 0) ? (
                <tr className="bg-white">
                  <td className="border-2 border-gray-500 p-2 text-sm font-semibold text-gray-800">
                    Tax
                  </td>
                  <td className="border-2 border-gray-500 p-2 text-sm font-semibold text-gray-900 text-right">
                    {invoice.financial?.currency || "$"}
                    {parseFloat(String(tax)).toFixed(2)}
                  </td>
                </tr>
              ) : null}
              {invoice.financial?.discount_total !== null &&
              invoice.financial?.discount_total !== undefined ? (
                <tr className="bg-white">
                  <td className="border-2 border-gray-500 p-2 text-sm font-semibold text-gray-800">
                    Discount Total
                  </td>
                  <td className="border-2 border-gray-500 p-2 text-sm font-semibold text-gray-900 text-right text-red-600">
                    -{invoice.financial?.currency || "$"}
                    {parseFloat(
                      String(extractValue(invoice.financial.discount_total))
                    ).toFixed(2)}
                  </td>
                </tr>
              ) : null}
              {invoice.financial?.shipping_charges !== null &&
              invoice.financial?.shipping_charges !== undefined ? (
                <tr className="bg-white">
                  <td className="border-2 border-gray-500 p-2 text-sm font-semibold text-gray-800">
                    Shipping Charges
                  </td>
                  <td className="border-2 border-gray-500 p-2 text-sm font-semibold text-gray-900 text-right">
                    {invoice.financial?.currency || "$"}
                    {parseFloat(
                      String(extractValue(invoice.financial.shipping_charges))
                    ).toFixed(2)}
                  </td>
                </tr>
              ) : null}
              {grandTotal !== null && grandTotal !== undefined ? (
                <tr className="bg-green-200">
                  <td className="border-2 border-gray-500 p-2 text-base font-bold text-gray-900">
                    Grand Total
                  </td>
                  <td className="border-2 border-gray-500 p-2 text-base font-bold text-green-900 text-right">
                    {invoice.financial?.currency || "$"}
                    {parseFloat(String(grandTotal)).toFixed(2)}
                  </td>
                </tr>
              ) : (
                <tr className="bg-gray-50">
                  <td
                    className="border-2 border-gray-500 p-2 text-sm font-semibold text-gray-800"
                    colSpan={2}
                  >
                    No financial information available
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Payment Information - Excel Style */}
        {invoice.payment &&
          Object.keys(invoice.payment).some((key) => {
            const value = invoice.payment[key as keyof PaymentInformation];
            return value !== null && value !== undefined;
          }) && (
            <div className="border-2 border-gray-400 rounded overflow-hidden w-full">
              <table
                className="w-full border-collapse table-fixed"
                style={{ minWidth: "100%" }}
              >
                <thead>
                  <tr className="bg-gray-300">
                    <th
                      className="border-2 border-gray-500 p-2 text-left text-sm font-bold text-gray-900"
                      colSpan={2}
                    >
                      Payment Information
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {invoice.payment.payment_terms && (
                    <tr className="bg-white">
                      <td
                        className="border-2 border-gray-500 p-2 text-sm font-semibold text-gray-800"
                        style={{ width: "30%" }}
                      >
                        Payment Terms
                      </td>
                      <td className="border-2 border-gray-500 p-2 text-sm text-gray-900">
                        {safeRenderText(invoice.payment.payment_terms)}
                      </td>
                    </tr>
                  )}
                  {invoice.payment.payment_mode && (
                    <tr className="bg-gray-50">
                      <td className="border-2 border-gray-500 p-2 text-sm font-semibold text-gray-800">
                        Payment Mode
                      </td>
                      <td className="border-2 border-gray-500 p-2 text-sm text-gray-900">
                        {safeRenderText(invoice.payment.payment_mode)}
                      </td>
                    </tr>
                  )}
                  {invoice.payment.due_date && (
                    <tr className="bg-white">
                      <td className="border-2 border-gray-500 p-2 text-sm font-semibold text-gray-800">
                        Due Date
                      </td>
                      <td className="border-2 border-gray-500 p-2 text-sm text-gray-900">
                        {safeRenderText(invoice.payment.due_date)}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

        {/* Action Buttons */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-6">
          <button className="px-4 py-3 bg-green-500 text-white rounded-lg text-sm font-semibold hover:bg-green-600 transition-all flex items-center justify-center gap-2">
            <span>✓</span>
            <span>Approve</span>
          </button>
          <button
            onClick={handleExportToExcel}
            className="px-4 py-3 bg-emerald-500 text-white rounded-lg text-sm font-semibold hover:bg-emerald-600 transition-all flex items-center justify-center gap-2"
          >
            <span>📥</span>
            <span>Download Excel</span>
          </button>
          <button className="col-span-2 px-4 py-3 bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-lg text-sm font-semibold hover:shadow-lg transition-all flex items-center justify-center gap-2">
            <span>💾</span>
            <span>Save & Send</span>
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4 md:p-6">
      <div className="max-w-full mx-auto w-full px-2">
        {/* Header */}
        <div className="bg-white rounded-xl shadow-md p-5 mb-6 flex justify-between items-center">
          <h1 className="text-2xl md:text-3xl font-bold text-gray-800">
            Invoice Review Dashboard
          </h1>
          <div className="flex gap-3">
            <button
              onClick={loadInvoices}
              disabled={isLoading}
              className="px-4 py-2 bg-gray-400 text-gray-900 rounded-lg text-sm font-semibold hover:bg-gray-500 transition-all disabled:opacity-50"
            >
              {isLoading ? "Loading..." : "🔄 Refresh"}
            </button>
            <button
              onClick={() => setShowUploadSidebar(!showUploadSidebar)}
              className="px-4 py-2 bg-gray-400 text-gray-900 rounded-lg text-sm font-semibold hover:bg-gray-500 transition-all"
            >
              {showUploadSidebar ? "Hide Upload" : "Show Upload"}
            </button>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-6 flex items-center gap-2">
            <span className="text-red-600">⚠</span>
            <span className="text-red-800">{error}</span>
          </div>
        )}

        {/* Main Content - 3 Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Upload Sidebar */}
          {showUploadSidebar && (
            <div className="lg:col-span-2">
              <div className="bg-white rounded-xl shadow-md p-4">
                <h2 className="text-lg font-bold text-gray-700 mb-4">
                  Upload Documents
                </h2>

                {/* Dropzone */}
                <div
                  className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all duration-300 ${
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
                    <div className="text-4xl mb-2">📁</div>
                    <h3 className="text-base font-semibold text-gray-800 mb-1">
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
                      disabled={isProcessing}
                      className="w-full mt-4 px-4 py-2.5 bg-gradient-to-r from-[#667eea] to-[#764ba2] text-white rounded-lg text-sm font-semibold hover:shadow-lg transition-all disabled:opacity-50"
                    >
                      {isProcessing
                        ? "Processing..."
                        : `Process ${uploadedFiles.length} File${
                            uploadedFiles.length > 1 ? "s" : ""
                          } →`}
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Left Sidebar - Invoice List */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-xl shadow-md p-4">
              <h2 className="text-lg font-bold text-gray-700 mb-4">
                Processed Invoices ({invoices.length})
              </h2>
              <div className="space-y-2 max-h-[600px] overflow-y-auto">
                {isLoading ? (
                  <div className="text-center py-8 text-gray-500">
                    Loading invoices...
                  </div>
                ) : invoices.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    No invoices found. Upload a PDF to get started.
                  </div>
                ) : (
                  invoices.map((invoice) => {
                    const status = getStatusFromInvoice(invoice.data);
                    const statusMessage = getStatusMessage(invoice.data);
                    const invoiceData = extractInvoiceData(invoice.data);
                    const displayId = safeRenderText(
                      invoiceData.orderNumber ||
                        invoiceData.poNumber ||
                        invoiceData.invoiceNumber ||
                        invoice.filename.substring(0, 20) + "..."
                    );

                    return (
                      <div
                        key={invoice.filename}
                        onClick={() => handleInvoiceSelect(invoice)}
                        className={`p-3 rounded-lg cursor-pointer transition-all border-2 ${
                          selectedInvoice?.filename === invoice.filename
                            ? "border-blue-500 bg-blue-50"
                            : "border-gray-200 hover:border-gray-300 bg-white"
                        }`}
                      >
                        <div className="flex justify-between items-start mb-1">
                          <span className="font-semibold text-gray-800 text-sm truncate flex-1">
                            {displayId}
                          </span>
                          <span
                            className={`text-xs px-2 py-1 rounded-full font-semibold whitespace-nowrap ml-2 ${getStatusColor(
                              status
                            )}`}
                          >
                            {status}
                          </span>
                        </div>
                        <div className="text-xs text-gray-500 truncate">
                          {statusMessage}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>

          {/* Center - Invoice Detail View */}
          <div
            className={showUploadSidebar ? "lg:col-span-5" : "lg:col-span-7"}
          >
            <div className="bg-white rounded-xl shadow-md p-4 md:p-6 w-full overflow-x-auto">
              {renderInvoiceDetails()}
            </div>
          </div>

          {/* Right - JSON Editor */}
          <div
            className={showUploadSidebar ? "lg:col-span-3" : "lg:col-span-3"}
          >
            <div className="bg-white rounded-xl shadow-md p-4 h-full">
              <h2 className="text-lg font-bold text-gray-700 mb-4">
                Parsed JSON (Editable)
              </h2>
              {selectedInvoice ? (
                <div className="space-y-3">
                  <textarea
                    value={editedJson}
                    onChange={handleJsonChange}
                    className="w-full h-[500px] p-3 border-2 border-gray-300 rounded-lg font-mono text-xs focus:border-blue-500 focus:outline-none"
                    spellCheck={false}
                  />
                  <button
                    onClick={handleSaveJson}
                    className="w-full px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-semibold hover:bg-blue-600 transition-all"
                  >
                    Save Changes
                  </button>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  Select an invoice to view JSON
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
