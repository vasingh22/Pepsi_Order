/**
 * API utility functions for backend integration
 * 
 * This file contains helper functions to interact with the backend API
 * for uploading and processing order documents.
 */

// Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Upload files to the backend for processing
 * @param files Array of files to upload
 * @returns Promise with the API response
 */
export const uploadFiles = async (files: File[]): Promise<any> => {
  const formData = new FormData();
  
  // Append each file to the FormData
  files.forEach((file, index) => {
    formData.append(`files`, file);
  });
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/upload`, {
      method: 'POST',
      body: formData,
      // Don't set Content-Type header - browser will set it with boundary
    });
    
    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error uploading files:', error);
    throw error;
  }
};

/**
 * Check the status of a processing job
 * @param jobId The job ID to check
 * @returns Promise with the job status
 */
export const checkJobStatus = async (jobId: string): Promise<any> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/status/${jobId}`);
    
    if (!response.ok) {
      throw new Error(`Status check failed: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error checking job status:', error);
    throw error;
  }
};

/**
 * Get the results of a completed job
 * @param jobId The job ID to get results for
 * @returns Promise with the job results
 */
export const getJobResults = async (jobId: string): Promise<any> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/results/${jobId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to get results: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error getting job results:', error);
    throw error;
  }
};

