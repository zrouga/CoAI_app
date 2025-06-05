'use client';

import useSWR, { SWRConfiguration, mutate } from 'swr';
import toast from 'react-hot-toast';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Central error logger
async function logError(error: any, context: string) {
  try {
    await fetch(`${API_BASE}/log`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        level: 'error',
        message: error.message || String(error),
        context,
        timestamp: new Date().toISOString(),
        stack: error.stack
      })
    });
  } catch (e) {
    console.error('Failed to log error:', e);
  }
}

// Central fetcher with error handling
export async function fetcher(url: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers
    }
  });

  if (!res.ok) {
    const error = new Error(`HTTP ${res.status}`);
    try {
      const data = await res.json();
      error.message = data.detail || data.message || error.message;
    } catch {}
    
    await logError(error, `${options?.method || 'GET'} ${url}`);
    throw error;
  }

  return res.json();
}

// SWR hook wrapper
export function useApi<T>(
  endpoint: string | null,
  options?: SWRConfiguration
) {
  return useSWR<T>(endpoint, fetcher, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
    onError: (err) => {
      toast.error(err.message || 'Request failed');
    },
    ...options
  });
}

// API mutation helpers
export const api = {
  post: (url: string, data?: any) => 
    fetcher(url, { method: 'POST', body: JSON.stringify(data) }),
  
  put: (url: string, data?: any) =>
    fetcher(url, { method: 'PUT', body: JSON.stringify(data) }),
  
  delete: (url: string) =>
    fetcher(url, { method: 'DELETE' }),

  // Invalidate SWR cache
  refresh: (key: string) => mutate(key)
};

// Pagination helper
export function usePaginatedApi<T>(
  endpoint: string,
  page: number = 1,
  pageSize: number = 25,
  params?: Record<string, any>
) {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize), ...params });
  return useApi<T>(`${endpoint}?${query}`);
} 