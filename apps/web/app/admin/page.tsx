'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@examshield/ui';
import { Users, GraduationCap, FileQuestion, BarChart3, TrendingUp } from 'lucide-react';
import { PageHeader } from '@/components/page-header';
import { useQuery } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { formatDate } from '@examshield/utils';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  change?: string;
}

function StatCard({ title, value, icon: Icon, change }: StatCardProps) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-3xl font-bold mt-1">{value}</p>
            {change && <p className="text-sm text-emerald-600 dark:text-emerald-400 mt-1">{change}</p>}
          </div>
          <div className="p-3 bg-primary/10 rounded-xl text-primary">
            <Icon className="h-6 w-6" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function AdminDashboard() {
  const api = useApiClient();

  const { data: stats, isLoading } = useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: async () => {
      const [students, exams, questions, sessions] = await Promise.all([
        api.get('/students', { page_size: 1, page: 1 }),
        api.get('/exams', { page_size: 1, page: 1 }),
        api.get('/questions', { page_size: 1, page: 1 }),
        api.get('/exam-sessions', { page_size: 1, page: 1 }),
      ]);
      return {
        totalStudents: students.total,
        totalExams: exams.total,
        totalQuestions: questions.total,
        activeSessions: sessions.total,
      };
    },
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Overview of your examination platform"
      />

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <div className="animate-pulse space-y-2">
                  <div className="h-4 w-24 bg-muted rounded" />
                  <div className="h-8 w-32 bg-muted rounded" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard title="Total Students" value={stats?.totalStudents ?? 0} icon={Users} change="+12% this month" />
          <StatCard title="Total Exams" value={stats?.totalExams ?? 0} icon={FileQuestion} change="+5% this month" />
          <StatCard title="Questions in Bank" value={stats?.totalQuestions ?? 0} icon={GraduationCap} />
          <StatCard title="Active Sessions" value={stats?.activeSessions ?? 0} icon={TrendingUp} />
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Activity feed coming soon...</p>
        </CardContent>
      </Card>
    </div>
  );
}