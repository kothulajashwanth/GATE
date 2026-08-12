import { createClient } from './client';
import { auth } from '@clerk/nextjs/server';

interface SessionClaims {
  metadata?: {
    role?: string;
  };
}

/**
 * Server-side API client. Mints a short-lived Clerk session JWT for the
 * current user and injects it as the bearer token. Only usable in Server
 * Components / Route Handlers / Server Actions.
 */
export async function serverApi() {
  let token: string | null = null;
  try {
    token = await getToken();
  } catch {
    try {
      token = await getToken({ template: 'examshield' });
    } catch {
      // fallback
    }
  }
  return createClient({ token });
}

export async function requireRole(roles: string[]) {
  const { userId, sessionClaims } = await auth();
  if (!userId) throw new Error('UNAUTHENTICATED');
  const claims = sessionClaims as SessionClaims | undefined;
  const role = claims?.metadata?.role;
  if (!role || !roles.includes(role)) throw new Error('FORBIDDEN');
  return { userId, role };
}
