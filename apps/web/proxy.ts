import { clerkMiddleware, createRouteMatcher, createClerkClient } from '@clerk/nextjs/server';
import { NextResponse } from 'next/server';

/**
 * ExamShield AI - Role-Based Middleware & Auth Isolation Proxy
 */
const isPublicRoute = createRouteMatcher([
  '/',
  '/login(.*)',
  '/portal/admin/login(.*)',
  '/sign-in(.*)',
  '/sign-up(.*)',
  '/access-denied',
  '/api/webhooks(.*)',
  '/api/clerk(.*)',
  '/api/v1(.*)',
]);

const isAdminRoute = createRouteMatcher(['/admin(.*)']);
const isStudentRoute = createRouteMatcher(['/student(.*)', '/exam(.*)']);
const isLoginRoute = createRouteMatcher(['/login(.*)', '/portal/admin/login(.*)', '/sign-in(.*)']);

interface SessionClaims {
  metadata?: { role?: string };
  role?: string;
  public_metadata?: { role?: string };
  email?: string;
  email_address?: string;
  username?: string;
}

export default clerkMiddleware(async (auth, req) => {
  const { pathname } = req.nextUrl;

  // 0. OPTIONS preflight and API v1 routes must never be redirected by Next.js middleware
  if (req.method === 'OPTIONS' || pathname.startsWith('/api/v1')) {
    return NextResponse.next();
  }

  const { userId, sessionClaims } = await auth();

  // 1. Unauthenticated users on public routes -> allow access
  if (!userId && isPublicRoute(req)) {
    return NextResponse.next();
  }

  // 2. Unauthenticated users on protected routes -> redirect to appropriate login page
  if (!userId) {
    const isTargetingAdmin = isAdminRoute(req);
    const loginPath = isTargetingAdmin ? '/portal/admin/login' : '/login';
    const loginUrl = new URL(loginPath, req.url);
    loginUrl.searchParams.set('redirect_url', req.url);
    return NextResponse.redirect(loginUrl);
  }

  // 3. Extract role & user details from session claims
  const claims = sessionClaims as (SessionClaims & Record<string, any>) | undefined;
  let role = (
    claims?.metadata?.role ||
    claims?.role ||
    claims?.public_metadata?.role ||
    ''
  ).toLowerCase();

  let email = (claims?.email || claims?.email_address || '').toLowerCase();
  let username = (claims?.username || '').toLowerCase();

  // 4. Server-Side Clerk API Fallback: If role is not admin in claims, fetch full user metadata from Clerk API
  if (role !== 'admin' && role !== 'super_admin') {
    try {
      const secretKey = process.env.CLERK_SECRET_KEY;
      if (secretKey) {
        const clerk = createClerkClient({ secretKey });
        const user = await clerk.users.getUser(userId);
        const clerkRole = (
          (user.publicMetadata?.role as string) ||
          (user.unsafeMetadata?.role as string) ||
          ''
        ).toLowerCase();

        const clerkEmail = (user.primaryEmailAddress?.emailAddress || '').toLowerCase();
        const clerkUsername = (user.username || '').toLowerCase();

        if (clerkRole) role = clerkRole;
        if (clerkEmail) email = clerkEmail;
        if (clerkUsername) username = clerkUsername;
      }
    } catch {
      // Ignore API fetch error if offline
    }
  }

  // 5. Strict Admin role validation: ONLY kothulajashwanth@gmail.com is an Admin
  const isAdmin = email === 'kothulajashwanth@gmail.com';


  // 6. Signed-in users on Login / Root pages -> Redirect to their respective dashboard
  if (pathname === '/' || isLoginRoute(req)) {
    const targetUrl = isAdmin ? '/admin' : '/student';
    return NextResponse.redirect(new URL(targetUrl, req.url));
  }

  // 7. Role-based Route Protection
  // A. Non-admin attempting to access Admin routes (/admin) -> Access Denied
  if (isAdminRoute(req) && !isAdmin) {
    return NextResponse.redirect(new URL('/access-denied', req.url));
  }

  // B. Admin attempting to access Student routes (/student) -> Redirect to Admin Dashboard
  if (isStudentRoute(req) && isAdmin) {
    return NextResponse.redirect(new URL('/admin', req.url));
  }

  return NextResponse.next();
});

export const config = {
  matcher: [
    // Skip Next.js internals and static files
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
};
