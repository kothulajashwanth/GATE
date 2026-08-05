'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { AppShell } from '@/components/app-shell';
import { getAdminNavForRole } from './_nav';
import { useUser } from '@clerk/nextjs';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user } = useUser();
  const pathname = usePathname();
  const role = user?.publicMetadata?.role as string ?? 'student';
  const items = getAdminNavForRole(role);

  return (
    <AppShell items={items} children={children} role={role} />
  );
}