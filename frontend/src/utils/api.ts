/**
 * API utility functions for backend integration
 * 
 * This file contains helper functions to interact with the backend API
 * for uploading and processing order documents.
 */

// Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Upload a PDF file and extract data using Surya OCR
 * @param file PDF file to upload
 * @returns Promise with the OCR result
 */
export const uploadAndExtractPDF = async (file: File): Promise<any> => {
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    const response = await fetch(`${API_BASE_URL}/ocr/extract`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error(`OCR extraction failed: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error extracting PDF:', error);
    throw error;
  }
};

/**
 * Get list of all processed invoices
 * @returns Promise with list of invoices
 */
export const listInvoices = async (): Promise<any> => {
  try {
    const response = await fetch(`${API_BASE_URL}/invoices`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch invoices: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching invoices:', error);
    throw error;
  }
};

/**
 * Get a specific invoice by filename
 * @param filename The invoice filename
 * @returns Promise with the invoice data
 */
export const getInvoice = async (filename: string): Promise<any> => {
  try {
    const response = await fetch(`${API_BASE_URL}/invoices/${encodeURIComponent(filename)}`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch invoice: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching invoice:', error);
    throw error;
  }
};

/**
 * Get OCR data and parsed line items for a specific invoice
 * @param filename The invoice filename
 * @returns Promise with OCR data and parsed line items
 */
export const getInvoiceOCR = async (filename: string): Promise<any> => {
  try {
    const response = await fetch(`${API_BASE_URL}/invoices/${encodeURIComponent(filename)}/ocr`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch OCR data: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching OCR data:', error);
    throw error;
  }
};

