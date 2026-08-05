'use client';

import { createClient, type ApiClient } from './client';
import { createContext, useContext, type ReactNode } from 'react';

/**
 * Provides the API client to the component tree. The token is refreshed via
 * `auth.getToken()` whenever it expires; refreshing the client mid-flight is
 * handled by the caller swapping the context value.
 */
const ApiClientContext = createContext<ApiClient | null>(null);

export function ApiClientProvider({ client, children }: { client: ApiClient; children: ReactNode }) {
  return <ApiClientContext.Provider value={client}>{children}</ApiClientContext.Provider>;
}

export function useApiClient(): ApiClient {
  const client = useContext(ApiClientContext);
  if (!client) {
    throw new Error('useApiClient must be used within ApiClientProvider');
  }
  return client;
}
