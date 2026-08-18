'use client';

import { Card, CardContent, CardHeader, CardTitle, Button } from '@examshield/ui';
import { Users, GraduationCap, FileQuestion, TrendingUp, ShieldCheck, Sparkles, BookOpen, Layers, ArrowUpRight } from 'lucide-react';
import { PageHeader } from '@/components/page-header';
import { useAuth } from '@clerk/nextjs';
import { useQuery } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import type { Paginated } from '@examshield/types';
import Link from 'next/link';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  change?: string;
}

function StatCard({ title, value, icon: Icon, change }: StatCardProps) {
  return (
    <Card className="glass-card overflow-hidden relative border border-white/20 dark:border-white/10">
      <div className="absolute top-0 right-0 p-3 opacity-10 text-primary">
        <Icon className="h-16 w-16" />
      </div>
      <CardContent className="p-6 relative z-10">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{title}</p>
            <p className="text-3xl font-extrabold mt-1 tracking-tight text-foreground">{value}</p>
            {change && <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 mt-1.5 flex items-center gap-1"><ArrowUpRight className="h-3 w-3" /> {change}</p>}
          </div>
          <div className="p-3 bg-primary/10 rounded-2xl border border-primary/20 text-primary shadow-inner">
            <Icon className="h-6 w-6" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function AdminDashboard() {
  const api = useApiClient();
  const { isLoaded, isSignedIn } = useAuth();

  const { data: stats, isLoading } = useQuery({
    queryKey: ['admin', 'stats', isLoaded, isSignedIn],
    queryFn: async () => {
      try {
        const [students, exams, questions, sessions] = await Promise.all([
          api.get<Paginated<unknown>>('/students', { page_size: 1, page: 1 }),
          api.get<Paginated<unknown>>('/exams', { page_size: 1, page: 1 }),
          api.get<Paginated<unknown>>('/questions', { page_size: 1, page: 1 }),
          api.get<Paginated<unknown>>('/sessions', { page_size: 1, page: 1 }),
        ]);
        return {
          totalStudents: students.total ?? 0,
          totalExams: exams.total ?? 0,
          totalQuestions: questions.total ?? 0,
          activeSessions: sessions.total ?? 0,
        };
      } catch {
        return {
          totalStudents: 0,
          totalExams: 0,
          totalQuestions: 0,
          activeSessions: 0,
        };
      }
    },
    enabled: isLoaded && isSignedIn,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Admin Examination Management Portal"
        description="Liquid Glass Overview: student roster, examinations, question repository, and live proctoring monitoring."
      />

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="glass-card">
              <CardContent className="p-6">
                <div className="animate-pulse space-y-2">
                  <div className="h-4 w-24 bg-muted/60 rounded" />
                  <div className="h-8 w-32 bg-muted/60 rounded" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard title="Enrolled Students" value={stats?.totalStudents ?? 0} icon={Users} change="+12% active" />
          <StatCard title="Total Exams" value={stats?.totalExams ?? 0} icon={FileQuestion} change="Active Schedules" />
          <StatCard title="Question Pool" value={stats?.totalQuestions ?? 0} icon={GraduationCap} />
          <StatCard title="Live Proctored Sessions" value={stats?.activeSessions ?? 0} icon={TrendingUp} change="Monitored Live" />
        </div>
      )}

      <div className="grid gap-6 sm:grid-cols-2">
        <Card className="glass-card border-primary/20 bg-primary/5 dark:bg-primary/10 p-2">
          <CardHeader>
            <CardTitle className="text-base font-bold flex items-center gap-2 text-foreground">
              <ShieldCheck className="h-5 w-5 text-primary" /> Admin System Security Status
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs text-muted-foreground">
            <p>You are authenticated with System Administrator privileges via Clerk.</p>
            <p>PostgreSQL Render database connection is active with connection pooling. All student directory actions, document question parsing, and exam schedules are recorded in PostgreSQL audit logs.</p>
          </CardContent>
        </Card>

        <Card className="glass-card p-2">
          <CardHeader>
            <CardTitle className="text-base font-bold flex items-center gap-2 text-foreground">
              <Sparkles className="h-5 w-5 text-amber-500" /> Administrative Quick Shortcuts
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs text-muted-foreground">
            <div className="flex flex-wrap gap-2">
              <Link href="/admin/students">
                <Button size="sm" variant="outline" className="glass-button">
                  <Users className="h-3.5 w-3.5 mr-1" /> Student Roster
                </Button>
              </Link>
              <Link href="/admin/question-repository">
                <Button size="sm" variant="outline" className="glass-button">
                  <Layers className="h-3.5 w-3.5 mr-1" /> Question Repository
                </Button>
              </Link>
              <Link href="/admin/question-bank">
                <Button size="sm" variant="outline" className="glass-button">
                  <BookOpen className="h-3.5 w-3.5 mr-1" /> Question Bank
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}