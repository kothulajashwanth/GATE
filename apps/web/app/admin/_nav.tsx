import {
  LayoutDashboard,
  Users,
  FileQuestion,
  FolderArchive,
  FolderKanban,
  Sparkles,
  Award,
  BarChart3,
  FileText,
  History,
  Settings,
  User,
  Layers,
  Activity,
} from 'lucide-react';
import { ROLE_ROUTES } from '@/lib/constants';

export const ADMIN_NAV = [
  { href: '/admin', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/admin/students', label: 'Students', icon: Users },
  { href: '/admin/attendance', label: 'Attendance', icon: Activity },
  { href: '/admin/exams', label: 'Examinations', icon: FileQuestion },


  { href: '/admin/exams/live', label: 'Live Monitoring', icon: Activity },
  { href: '/admin/exams/blueprint', label: 'Exam Blueprint', icon: Layers },
  { href: '/admin/question-repository', label: 'Question Repository', icon: FolderArchive },
  { href: '/admin/question-bank', label: 'Question Bank', icon: FolderKanban },
  { href: '/admin/ai-generator', label: 'AI Generator', icon: Sparkles },
  { href: '/admin/results', label: 'Results', icon: Award },
  { href: '/admin/analytics', label: 'Analytics', icon: BarChart3 },
  { href: '/admin/reports', label: 'Reports', icon: FileText },
  { href: '/admin/audit-logs', label: 'Audit Logs', icon: History },
  { href: '/admin/settings', label: 'Settings', icon: Settings },
  { href: '/admin/profile', label: 'Profile', icon: User },
] as const;

export function getAdminNavForRole(role: string) {
  return ADMIN_NAV;
}