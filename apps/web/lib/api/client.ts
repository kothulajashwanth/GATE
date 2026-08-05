import { toQueryString } from '@examshield/utils';

/**
 * Thin fetch wrapper for the ExamShield REST API.
 * - Attaches bearer token (JWT minted server-side via Clerk session) when present.
 * - Sets a request id and json headers.
 * - Throws ApiError with the server's structured error body.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

interface ClientOptions {
  token?: string | null;
}

export function createClient(opts: ClientOptions = {}) {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

  async function request<T>(
    method: string,
    path: string,
    body?: unknown,
    signal?: AbortSignal,
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-Request-Id': crypto.randomUUID(),
    };
    if (opts.token) headers.Authorization = `Bearer ${opts.token}`;

    const response = await fetch(`${baseUrl}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });

    if (!response.ok) {
      let payload: { error?: { code?: string; message?: string; details?: unknown } } = {};
      try {
        payload = (await response.json()) as typeof payload;
      } catch {
        // non-json error body; fall through with defaults
      }
      throw new ApiError(
        response.status,
        payload.error?.code ?? 'request_failed',
        payload.error?.message ?? `Request failed with status ${response.status}`,
        payload.error?.details,
      );
    }

    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  return {
    get<T>(path: string, params?: Record<string, unknown>, signal?: AbortSignal) {
      return request<T>('GET', path + toQueryString(params ?? {}), undefined, signal);
    },
    post<T>(path: string, body?: unknown, signal?: AbortSignal) {
      return request<T>('POST', path, body, signal);
    },
    put<T>(path: string, body?: unknown, signal?: AbortSignal) {
      return request<T>('PUT', path, body, signal);
    },
    patch<T>(path: string, body?: unknown, signal?: AbortSignal) {
      return request<T>('PATCH', path, body, signal);
    },
    delete<T>(path: string, signal?: AbortSignal) {
      return request<T>('DELETE', path, undefined, signal);
    },
    raw: {
      /** Download a non-json resource (report, export) as a Blob. */
      async download(path: string, token?: string): Promise<Blob> {
        const headers: Record<string, string> = {};
        if (token) headers.Authorization = `Bearer ${token}`;
        const response = await fetch(`${baseUrl}${path}`, { headers });
        if (!response.ok) {
          throw new ApiError(response.status, 'download_failed', 'Failed to download file');
        }
        return response.blob();
      },
    },
  };
}

export type ApiClient = ReturnType<typeof createClient>;
