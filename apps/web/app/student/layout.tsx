'use client';

import { AppShell } from '@/components/app-shell';
import { getStudentNav } from './_nav';
import { useUser } from '@clerk/nextjs';
import { NavItem } from '@/components/app-shell';

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  const { user } = useUser();
  const items = [...getStudentNav()] as NavItem[];

  return (
    <AppShell items={items} children={children} role="student" />
  );
}