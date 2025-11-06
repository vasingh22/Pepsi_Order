// Type definitions for invoice data
export interface InvoiceItem {
  name: string;
  hsn_code?: string;
  quantity: number;
  unit?: string;
  rate: number;
  discount?: number;
  amount: number;
}

export interface StoreDetails {
  name: string;
  address: string;
  gst_number?: string;
}

export interface BuyerDetails {
  name: string;
  address: string;
  contact?: string;
}

export interface SellerDetails {
  name: string;
  address: string;
  gst_number?: string;
}

export interface TaxDetails {
  type: string;
  rate: number;
  amount: number;
}

export interface PaymentDetails {
  mode: string;
  paid: boolean;
  due_date?: string;
}

export interface Invoice {
  id: string;
  invoice_number: string;
  invoice_date: string;
  status: 'Approved' | 'Flagged' | 'Pending' | 'In Review';
  statusMessage?: string;
  store_name: string;
  address: string;
  gst_number?: string;
  buyer_details: BuyerDetails;
  seller_details: SellerDetails;
  items: InvoiceItem[];
  charges?: {
    subtotal: number;
  };
  tax_details: TaxDetails;
  round_off?: number;
  total: number;
  payment_details: PaymentDetails;
}

