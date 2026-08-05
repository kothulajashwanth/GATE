import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';
import { NextResponse } from 'next/server';
import { ROLE_HOME } from '@/lib/constants';

/**
 * Route-based access control.
 * - Public routes: landing, auth pages, static assets.
 * - Protected routes require a signed-in session.
 * - Role routes require the matching publicMetadata.role and redirect
 *   cross-role users to their own home.
 */
const isPublic = createRouteMatcher([
  '/',
  '/sign-in(.*)',
  '/sign-up(.*)',
  '/api/webhooks(.*)',
  '/api/clerk(.*)',
  '/_next(.*)',
  '/favicon.ico',
  '/fonts(.*)',
]);

const isAdmin = createRouteMatcher(['/admin(.*)']);
const isStudent = createRouteMatcher(['/student(.*)', '/exam(.*)']);
const isFaculty = createRouteMatcher(['/faculty(.*)']);

export default clerkMiddleware(async (auth, req) => {
  const { userId, sessionClaims, redirectToSignIn } = await auth();

  if (!isPublic(req)) {
    if (!userId) return redirectToSignIn({ returnBackUrl: req.url });

    const role = sessionClaims?.metadata?.role as string | undefined;

    if (isAdmin(req) && role !== 'admin' && role !== 'super_admin') {
      return NextResponse.redirect(new URL(ROLE_HOME[role] ?? '/', req.url));
    }
    if (isStudent(req) && role !== 'student') {
      return NextResponse.redirect(new URL(ROLE_HOME[role] ?? '/', req.url));
    }
    if (isFaculty(req) && role !== 'faculty') {
      return NextResponse.redirect(new URL(ROLE_HOME[role] ?? '/', req.url));
    }
  }

  return NextResponse.next();
});

export const config = {
  matcher: [
    // Run on everything except next internals and static files.
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    '/(api|trpc)(.*)',
  ],
};
