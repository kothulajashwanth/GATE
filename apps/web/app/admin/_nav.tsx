import { User, Users, GraduationCap, LayoutDashboard, FileQuestion, HelpCircle, Settings, BarChart3, Bell, Shield, FolderKanban } from 'lucide-react';
import { ROLE_ROUTES } from '@/lib/constants';

export const ADMIN_NAV = [
  { href: '/admin', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/admin/students', label: 'Students', icon: Users },
  { href: '/admin/departments', label: 'Departments', icon: GraduationCap },
  { href: '/admin/question-bank', label: 'Question Bank', icon: FolderKanban },
  { href: '/admin/exams', label: 'Exams', icon: FileQuestion },
  { href: '/admin/analytics', label: 'Analytics', icon: BarChart3 },
  { href: '/admin/settings', label: 'Settings', icon: Settings },
] as const;

export function getAdminNavForRole(role: string) {
  return ADMIN_NAV.filter((item) => {
    const allowed = ROLE_ROUTES[role] ?? [];
    return allowed.some((prefix) => item.href.startsWith(prefix));
  });
}