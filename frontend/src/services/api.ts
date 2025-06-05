// API Service for Market Intelligence Dashboard
import { 
  RunRequest, 
  KeywordStatus, 
  ProductResult, 
  DashboardStats,
  LogEntry
} from '@/types/api';

// API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Run pipeline for a keyword
 */
export async function runKeywordPipeline(request: RunRequest): Promise<KeywordStatus> {
  const response = await fetch(`${API_BASE_URL}/run`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to run pipeline');
  }

  return response.json();
}

/**
 * Get status for a keyword pipeline run
 */
export async function getKeywordStatus(keyword: string): Promise<KeywordStatus> {
  const response = await fetch(`${API_BASE_URL}/status/${keyword}`);
  
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || `Failed to get status for ${keyword}`);
  }

  return response.json();
}

/**
 * Get results for a keyword pipeline run
 */
export async function getKeywordResults(
  keyword: string,
  page = 1,
  pageSize = 20,
  sortBy = 'monthly_visits',
  sortDesc = true
): Promise<ProductResult[]> {
  const url = new URL(`${API_BASE_URL}/results/${keyword}`);
  url.searchParams.append('page', page.toString());
  url.searchParams.append('page_size', pageSize.toString());
  url.searchParams.append('sort_by', sortBy);
  url.searchParams.append('sort_desc', sortDesc.toString());

  const response = await fetch(url);
  
  if (!response.ok) {
    if (response.status === 404) {
      return [];
    }
    const errorData = await response.json();
    throw new Error(errorData.detail || `Failed to get results for ${keyword}`);
  }

  return response.json();
}

/**
 * Get logs for a keyword pipeline run
 */
export async function getKeywordLogs(keyword: string, limit = 100): Promise<LogEntry[]> {
  const url = new URL(`${API_BASE_URL}/logs/${keyword}`);
  url.searchParams.append('limit', limit.toString());

  const response = await fetch(url);
  
  if (!response.ok) {
    if (response.status === 404) {
      return [];
    }
    const errorData = await response.json();
    throw new Error(errorData.detail || `Failed to get logs for ${keyword}`);
  }

  return response.json();
}

/**
 * Get dashboard statistics
 */
export async function getDashboardStats(): Promise<DashboardStats> {
  const response = await fetch(`${API_BASE_URL}/dashboard/stats`);
  
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to get dashboard stats');
  }

  return response.json();
}

/**
 * Get all processed keywords
 */
export async function getAllKeywords(): Promise<string[]> {
  const response = await fetch(`${API_BASE_URL}/keywords`);
  
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to get keywords');
  }

  return response.json();
}

/**
 * Delete results for a keyword
 */
export async function deleteKeywordResults(keyword: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/results/${keyword}`, {
    method: 'DELETE',
  });
  
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || `Failed to delete results for ${keyword}`);
  }
}

/**
 * Delete multiple keywords results
 */
export async function deleteMultipleKeywordResults(keywords: string[]): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/results`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(keywords),
  });
  
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to delete multiple results');
  }
}

/**
 * Connect to SSE endpoint for real-time status updates
 */
export function subscribeToStatusUpdates(
  keyword: string,
  onStatusUpdate: (status: KeywordStatus) => void,
  onError: (error: Error) => void
): () => void {
  const eventSource = new EventSource(`${API_BASE_URL}/sse/status/${keyword}`);

  eventSource.addEventListener('status', (event) => {
    try {
      const data = JSON.parse(event.data);
      onStatusUpdate(data);
    } catch (error) {
      onError(new Error('Failed to parse status update'));
    }
  });

  eventSource.addEventListener('error', (event) => {
    onError(new Error('SSE connection error'));
    eventSource.close();
  });

  // Return cleanup function
  return () => {
    eventSource.close();
  };
}
