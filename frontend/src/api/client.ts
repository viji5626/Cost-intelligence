/**
 * Centralized HTTP Client for Air-Gapped HERO Platform Backend
 */

const BASE_URL = '/api/v1';

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('hero_auth_token') || 'dev-token-cost-eng';
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
    ...options.headers,
  };

  const url = `${BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errData;
      try {
        errData = await response.json();
      } catch {
        errData = await response.text();
      }
      throw new ApiError(
        (errData && errData.detail) || `HTTP error ${response.status}`,
        response.status,
        errData
      );
    }

    if (response.status === 204) {
      return {} as T;
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError((error as Error).message || 'Network request failed', 0);
  }
}
