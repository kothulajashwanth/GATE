'use client';

import { AppShell } from '@/components/app-shell';
import { ADMIN_NAV } from './_nav';
import { useUser } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { AccessDeniedModal } from '@/components/access-denied-modal';

const APPROVED_ADMIN_EMAIL = 'kothulajashwanth@gmail.com';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoaded } = useUser();
  const router = useRouter();
  const email = user?.primaryEmailAddress?.emailAddress?.toLowerCase() ?? '';

  if (isLoaded && (!user || email !== APPROVED_ADMIN_EMAIL)) {
    return <AccessDeniedModal userEmail={email} />;
  }

  return (
    <AppShell items={[...ADMIN_NAV]} children={children} role="admin" />
  );
}