import { toQueryString } from '@examshield/utils';

/**
 * Thin fetch wrapper for the GATE IGNITE REST API.
 * - Attaches bearer token (Clerk JWT) when present.
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
  getToken?: () => Promise<string | null>;
}

export function buildFullUrl(path: string): string {
  const configuredUrl =
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.API_URL ||
    (process.env.NODE_ENV === 'development'
      ? 'http://localhost:8000'
      : 'https://gate-ds9h.onrender.com');

  let base = configuredUrl.replace(/\/+$/, '');

  // Guard against self-referencing frontend domain in production
  if (base.includes('fabgate.vercel.app')) {
    base = 'https://gate-ds9h.onrender.com';
  }

  // Enforce https if base URL uses http (prevent Render HTTP -> HTTPS 301 redirects)
  if (base.startsWith('http://') && base.includes('onrender.com')) {
    base = base.replace('http://', 'https://');
  }

  const cleanPath = path.startsWith('/') ? path : `/${path}`;

  if (base.endsWith('/api/v1')) {
    base = base.replace(/\/api\/v1$/, '');
  }

  if (cleanPath.startsWith('/api/v1')) {
    return `${base}${cleanPath}`;
  }
  return `${base}/api/v1${cleanPath}`;
}

export function createClient(opts: ClientOptions = {}) {
  let staticToken = opts.token ?? null;

  async function resolveAuthToken(): Promise<string | null> {
    if (opts.getToken) {
      try {
        const clerkToken = await opts.getToken();
        if (clerkToken) return clerkToken;
      } catch {
        // Fallback to static token
      }
    }
    return staticToken;
  }

  async function request<T>(
    method: string,
    path: string,
    body?: unknown,
    signal?: AbortSignal,
  ): Promise<T> {
    const isFormData =
      body !== null &&
      typeof body === 'object' &&
      ((typeof FormData !== 'undefined' && body instanceof FormData) ||
        (body as any)?.constructor?.name === 'FormData' ||
        Object.prototype.toString.call(body) === '[object FormData]' ||
        typeof (body as any).append === 'function');

    const headers: Record<string, string> = {
      'X-Request-Id':
        typeof crypto !== 'undefined' && crypto.randomUUID
          ? crypto.randomUUID()
          : String(Date.now()),
    };

    if (!isFormData) {
      headers['Content-Type'] = 'application/json';
    }

    const token = await resolveAuthToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const fullUrl = buildFullUrl(path);

    const response = await fetch(fullUrl, {
      method,
      headers,
      body: isFormData ? (body as FormData) : body === undefined ? undefined : JSON.stringify(body),
      signal,
    });

    if (!response.ok) {
      let payload: {
        error?: { code?: string; message?: string; details?: unknown };
        detail?: string | any[];
      } = {};
      try {
        payload = (await response.json()) as typeof payload;
      } catch {
        // non-json error body
      }

      let errorMsg = payload.error?.message;
      if (!errorMsg && typeof payload.detail === 'string') {
        errorMsg = payload.detail;
      }
      if (Array.isArray(payload.error?.details) && payload.error.details.length > 0) {
        const detailMsgs = payload.error.details
          .map((d: any) => (d.loc ? `${d.loc.join('.')}: ${d.msg}` : d.msg || JSON.stringify(d)))
          .join('; ');
        errorMsg = errorMsg ? `${errorMsg} (${detailMsgs})` : detailMsgs;
      }
      if (!errorMsg) {
        errorMsg = `Request failed with status ${response.status}`;
      }

      throw new ApiError(
        response.status,
        payload.error?.code ?? 'request_failed',
        errorMsg,
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
    upload<T>(path: string, formData: FormData, signal?: AbortSignal) {
      return request<T>('POST', path, formData, signal);
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
    setToken: (t: string | null) => {
      staticToken = t;
    },
    raw: {
      async download(path: string, params?: Record<string, unknown>): Promise<Blob> {
        const token = await resolveAuthToken();
        const headers: Record<string, string> = {};
        if (token) headers.Authorization = `Bearer ${token}`;
        const fullUrl = buildFullUrl(path + toQueryString(params ?? {}));
        const response = await fetch(fullUrl, { headers });
        if (!response.ok) {
          throw new ApiError(response.status, 'download_failed', 'Failed to download file');
        }
        return response.blob();
      },
    },
  };
}

export type ApiClient = ReturnType<typeof createClient>;
