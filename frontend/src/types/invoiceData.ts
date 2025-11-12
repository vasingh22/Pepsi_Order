// Type definitions for invoice data structures used in Dashboard

export type ValueWrapper = string | number | null | { value: string | number | null };

export interface FileWithPreview {
  file: File;
  preview?: string;
}

export interface Address {
  full_address?: string | null;
  street_address?: string | null;
  city?: string | null;
  state?: string | null;
  zip_code?: string | null;
  country?: string | null;
}

export interface ContactInformation {
  phone?: string | null;
  email?: string | null;
  seller_contact?: string | null;
  buyer_contact_person?: string | null;
  shipping_contact_phone?: string | null;
}

export interface LineItem {
  item_id?: ValueWrapper;
  material_id?: ValueWrapper;
  product_code?: ValueWrapper;
  description?: ValueWrapper;
  name?: ValueWrapper;
  quantity?: ValueWrapper;
  unit?: ValueWrapper;
  unit_price?: ValueWrapper;
  rate?: ValueWrapper;
  discount?: ValueWrapper;
  total?: ValueWrapper;
  amount?: ValueWrapper;
  hsn_code?: ValueWrapper;
  other_details?: ValueWrapper;
}

export interface TaxDetail {
  type?: ValueWrapper;
  rate?: ValueWrapper;
  amount?: ValueWrapper;
}

export interface FinancialInformation {
  subtotal?: ValueWrapper;
  tax?: ValueWrapper;
  tax_details?: TaxDetail[];
  discount_total?: ValueWrapper;
  shipping_charges?: ValueWrapper;
  grand_total?: ValueWrapper;
  total?: ValueWrapper;
  currency?: string | null;
}

export interface PaymentInformation {
  payment_terms?: ValueWrapper;
  payment_mode?: ValueWrapper;
  due_date?: ValueWrapper;
  [key: string]: ValueWrapper | undefined;
}

export interface CoreInvoiceFields {
  seller_name?: ValueWrapper;
  buyer_name?: ValueWrapper;
  invoice_number?: ValueWrapper;
  order_number?: ValueWrapper;
  po_number?: ValueWrapper;
  invoice_date?: ValueWrapper;
  order_date?: ValueWrapper;
  po_date?: ValueWrapper;
  delivery_date?: ValueWrapper;
  customer_id?: ValueWrapper;
  gst_number?: ValueWrapper;
  tax_id?: ValueWrapper;
}

export interface SellerInformation {
  seller_name?: ValueWrapper;
  seller_address?: Address | string | null;
  gst_number?: ValueWrapper;
  tax_id?: ValueWrapper;
}

export interface BuyerInformation {
  buyer_name?: ValueWrapper;
  buyer_address?: Address | string | null;
  ship_to_address?: Address | string | null;
}

export interface InvoiceDetails {
  invoice_number?: ValueWrapper;
  order_number?: ValueWrapper;
  po_number?: ValueWrapper;
  invoice_date?: ValueWrapper;
  order_date?: ValueWrapper;
  po_date?: ValueWrapper;
  delivery_date?: ValueWrapper;
}

export interface AddressInformation {
  seller_address?: Address | string | null;
  buyer_address?: Address | string | null;
  ship_to_address?: Address | string | null;
  contact_information?: ContactInformation;
}

export interface TotalsSummary {
  subtotal?: ValueWrapper;
  tax?: ValueWrapper;
  total?: ValueWrapper;
  grand_total?: ValueWrapper;
  total_mismatch?: boolean;
}

export interface SourceMetadata {
  totals_verification?: {
    status?: string;
  };
}

export interface InvoiceDataStructure {
  // Structure 1: core_invoice_fields format
  core_invoice_fields?: CoreInvoiceFields;
  address_information?: AddressInformation;
  line_items?: LineItem[];
  totals_summary?: TotalsSummary;
  financial_information?: FinancialInformation;
  financial_summary?: FinancialInformation;
  payment_information?: PaymentInformation;

  // Structure 2: seller_information format
  seller_information?: SellerInformation;
  buyer_information?: BuyerInformation;
  invoice_details?: InvoiceDetails;

  // Structure 3: flat structure
  seller_name?: ValueWrapper;
  buyer_name?: ValueWrapper;
  invoice_number?: ValueWrapper;
  order_number?: ValueWrapper;
  po_number?: ValueWrapper;
  PO_number?: ValueWrapper;
  invoice_date?: ValueWrapper;
  order_date?: ValueWrapper;
  po_date?: ValueWrapper;
  PO_date?: ValueWrapper;
  delivery_date?: ValueWrapper;
  customer_id?: ValueWrapper;
  gst_number?: ValueWrapper;
  tax_id?: ValueWrapper;
  buyer_address?: Address | string | null;
  seller_address?: Address | string | null;
  ship_to_address?: Address | string | null;

  // Common fields
  source_metadata?: SourceMetadata;
  [key: string]: unknown;
}

export interface InvoiceData {
  filename: string;
  data: InvoiceDataStructure;
  modified_at: string;
}

export interface ExtractedInvoiceData {
  sellerName: string | null;
  buyerName: string | null;
  invoiceNumber: string | null;
  orderNumber: string | null;
  poNumber: string | null;
  invoiceDate: string | null;
  orderDate: string | null;
  poDate: string | null;
  deliveryDate: string | null;
  customerId: string | null;
  gstNumber: string | null;
  taxId: string | null;
  buyerAddress: Address | string | null;
  sellerAddress: Address | string | null;
  shipToAddress: Address | string | null;
  contactInfo: ContactInformation;
  lineItems: LineItem[];
  totals: TotalsSummary | null;
  financial: FinancialInformation;
  payment: PaymentInformation;
}

