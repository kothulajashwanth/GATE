import { auth, createClerkClient } from '@clerk/nextjs/server';
import { redirect } from 'next/navigation';

export default async function HomePage() {
  const { userId, sessionClaims } = await auth();

  if (!userId) {
    redirect('/login');
  }

  const claims = sessionClaims as any;
  let role = (
    claims?.metadata?.role ||
    claims?.role ||
    claims?.public_metadata?.role ||
    ''
  ).toLowerCase();

  let email = (claims?.email || claims?.email_address || '').toLowerCase();
  let username = (claims?.username || '').toLowerCase();

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
      // Fallback
    }
  }

  const isAdmin =
    role === 'admin' ||
    role === 'super_admin' ||
    email === 'kothulajashwanth@gmail.com' ||
    email.startsWith('admin@') ||
    username === 'admin';

  if (isAdmin) {
    redirect('/admin');
  }

  redirect('/student');
}
