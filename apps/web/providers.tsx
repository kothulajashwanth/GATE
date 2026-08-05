'use client';

import { useState, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuth } from '@clerk/nextjs';
import { createClient } from '@/lib/api/client';
import { ApiClientProvider } from '@/lib/api/client-provider';
import { Toaster } from '@examshield/ui';
import { TooltipProvider } from '@radix-ui/react-tooltip';
import { ThemeProvider } from 'next-themes';

/**
 * Top-level provider composition. The API client is recreated with a fresh
 * Clerk JWT whenever the session changes, so every request carries a valid
 * bearer token.
 */
export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30 * 1000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  const { getToken, isLoaded } = useAuth();
  const [client] = useState(() => createClient({}));

  return (
    <QueryClientProvider client={queryClient}>
      <ApiClientProvider client={client}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <TooltipProvider delayDuration={200}>{children}</TooltipProvider>
          <Toaster />
        </ThemeProvider>
      </ApiClientProvider>
    </QueryClientProvider>
  );
}
