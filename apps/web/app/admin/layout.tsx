'use client';

import { AppShell } from '@/components/app-shell';
import { ADMIN_NAV } from './_nav';
import { useUser } from '@clerk/nextjs';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user } = useUser();
  const email = user?.primaryEmailAddress?.emailAddress?.toLowerCase() ?? '';
  const username = user?.username?.toLowerCase() ?? '';

  const role = (
    (user?.publicMetadata?.role as string) ||
    (email === 'kothulajashwanth@gmail.com' || email.startsWith('admin@') || username === 'admin' ? 'admin' : 'admin')
  ).toLowerCase();

  return (
    <AppShell items={[...ADMIN_NAV]} children={children} role={role} />
  );
}