'use client';

import { AppShell } from '@/components/app-shell';
import { getStudentNav } from './_nav';
import { useUser } from '@clerk/nextjs';

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  const { user } = useUser();
  const items = getStudentNav();

  return (
    <AppShell items={items} children={children} role="student" />
  );
}