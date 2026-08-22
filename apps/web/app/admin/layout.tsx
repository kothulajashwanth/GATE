'use client';

import { AppShell } from '@/components/app-shell';

import { ADMIN_NAV } from './_nav';
import { useUser } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

const APPROVED_ADMIN_EMAIL = 'kothulajashwanth@gmail.com';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoaded } = useUser();
  const router = useRouter();
  const email = user?.primaryEmailAddress?.emailAddress?.toLowerCase() ?? '';

  useEffect(() => {
    if (isLoaded && user && email !== APPROVED_ADMIN_EMAIL) {
      router.replace('/student');
    }
  }, [isLoaded, user, email, router]);

  if (isLoaded && email !== APPROVED_ADMIN_EMAIL) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background text-foreground p-4">
        <div className="p-8 text-center glass-card max-w-md space-y-4">
          <h2 className="text-xl font-extrabold text-rose-600">403 - Forbidden</h2>
          <p className="text-xs text-muted-foreground">
            Access denied. Only <strong>kothulajashwanth@gmail.com</strong> is authorized to access the Admin Portal.
          </p>
        </div>
      </div>
    );
  }

  return (
    <AppShell items={[...ADMIN_NAV]} children={children} role="admin" />
  );
}