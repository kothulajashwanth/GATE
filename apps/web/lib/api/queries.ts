'use client';

import { useApiClient } from './client-provider';
import { useQuery, type UseQueryOptions } from '@tanstack/react-query';
import type { Paginated, User } from '@examshield/types';

/**
 * Shared TanStack Query hooks. Each call-site page composes these with its own
 * staleTime / selectors. Keep hooks thin: they only map an API call to a query.
 */

export function useMe(options?: Partial<UseQueryOptions<User>>) {
  const api = useApiClient();
  return useQuery({
    queryKey: ['me'],
    queryFn: () => api.get<User>('/me'),
    staleTime: 5 * 60 * 1000,
    ...options,
  });
}

export interface StudentRow {
  id: string;
  rollNumber: string;
  name: string;
  email: string;
  department: { id: string; name: string } | null;
  semester: { id: string; name: string } | null;
  section: { id: string; name: string } | null;
  isActive: boolean;
}

export function useStudents(params: Record<string, unknown>) {
  const api = useApiClient();
  return useQuery({
    queryKey: ['students', params],
    queryFn: () => api.get<Paginated<StudentRow>>('/students', params),
  });
}
