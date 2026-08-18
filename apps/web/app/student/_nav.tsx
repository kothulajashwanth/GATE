import { LayoutDashboard, FileQuestion, Trophy, History, User, Bell, Settings, ShieldCheck, Clock } from 'lucide-react';

export const STUDENT_NAV = [
  { href: '/student', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/student/attendance', label: 'Attendance', icon: ShieldCheck },
  { href: '/student/exams/upcoming', label: 'Upcoming Exams', icon: FileQuestion },
  { href: '/student/exams/completed', label: 'Completed Exams', icon: History },
  { href: '/student/results', label: 'Results', icon: Trophy },
  { href: '/student/profile', label: 'Profile', icon: User },
  { href: '/student/notifications', label: 'Notifications', icon: Bell },
] as const;

export function getStudentNav() {
  return STUDENT_NAV;
}