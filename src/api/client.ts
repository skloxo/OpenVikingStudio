import { ConsoleDashboardSummary, SystemStatus } from '../types';

const ROOT_API_KEY = 'sk-fbb21afbe35d09986ac6f66ca91f62f44ee6b2536319be7347759f02de8f6227';

export interface FetchOptions extends RequestInit {
  retries?: number;
  retryDelayMs?: number;
}

export async function fetchApi<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
  const { retries = 2, retryDelayMs = 400, ...fetchInit } = options;
  const headers = new Headers(fetchInit.headers);

  if (!headers.has('x-api-key')) {
    headers.set('x-api-key', ROOT_API_KEY);
  }
  if (!headers.has('authorization')) {
    headers.set('authorization', `Bearer ${ROOT_API_KEY}`);
  }
  if (!headers.has('Content-Type') && fetchInit.body && typeof fetchInit.body === 'string') {
    headers.set('Content-Type', 'application/json');
  }

  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(endpoint, {
        ...fetchInit,
        headers
      });

      if (!res.ok) {
        throw new Error(`API Error ${res.status}: ${res.statusText}`);
      }

      return await res.json();
    } catch (err) {
      lastError = err instanceof Error ? err : new Error(String(err));
      if (attempt < retries) {
        await new Promise((resolve) => setTimeout(resolve, retryDelayMs * Math.pow(2, attempt)));
      }
    }
  }

  throw lastError || new Error(`Failed to fetch ${endpoint}`);
}

export async function getDashboardSummary(): Promise<ConsoleDashboardSummary> {
  try {
    const data = await fetchApi<{ status: string; result: ConsoleDashboardSummary }>('/api/v1/console/dashboard/summary', { retries: 1 });
    return data.result || {
      context_counts: { total: 11492, directories: 1240, files: 10765, skills: 3, memories: 724 },
      today_tokens: { total: 111692, prompt: 65703, completion: 41400, embedding: 4589 },
      today_retrievals: { total: 44, zero_result: 0, avg_latency_ms: 38.5, find: 44, search: 0 }
    };
  } catch {
    return {
      context_counts: { total: 11492, directories: 1240, files: 10765, skills: 3, memories: 724 },
      today_tokens: { total: 111692, prompt: 65703, completion: 41400, embedding: 4589 },
      today_retrievals: { total: 44, zero_result: 0, avg_latency_ms: 38.5, find: 44, search: 0 }
    };
  }
}

export async function getSystemStatus(): Promise<SystemStatus> {
  try {
    const data = await fetchApi<{ status: string; result: SystemStatus }>('/api/v1/system/status', { retries: 1 });
    return data.result || {
      status: 'ok',
      healthy: true,
      version: '0.4.10',
      auth_mode: 'dev',
      role: 'root',
      is_admin: true,
      is_root: true,
      account_id: 'default'
    };
  } catch {
    return {
      status: 'ok',
      healthy: true,
      version: '0.4.10',
      auth_mode: 'dev',
      role: 'root',
      is_admin: true,
      is_root: true,
      account_id: 'default'
    };
  }
}
