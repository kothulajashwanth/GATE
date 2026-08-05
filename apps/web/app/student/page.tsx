'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@examshield/ui';
import { FileQuestion, Trophy, Clock, Award, Calendar, CheckCircle, AlertCircle } from 'lucide-react';
import { PageHeader } from '@/components/page-header';
import { useQuery } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { formatDateTime, formatDuration } from '@examshield/utils';
import { Button } from '@examshield/ui';
import Link from 'next/link';

interface ExamPreview {
  id: string;
  title: string;
  subject: { name: string } | null;
  startAt: string;
  endAt: string;
  durationMinutes: number;
  status: string;
}

function StatCard({ title, value, icon: Icon, href }: { title: string; value: string | number; icon: React.ComponentType<{ className?: string }>; href?: string }) {
  return (
    <Card className={href ? 'cursor-pointer hover:shadow-md transition-shadow' : ''}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-3xl font-bold mt-1">{value}</p>
          </div>
          <div className="p-3 bg-primary/10 rounded-xl text-primary">
            <Icon className="h-6 w-6" />
          </div>
        </div>
        {href && (
          <div className="mt-4 text-sm text-primary font-medium flex items-center gap-1">
            View all <span>→</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function UpcomingExamCard({ exam }: { exam: ExamPreview }) {
  const now = new Date();
  const start = new Date(exam.startAt);
  const isActive = now >= start && now <= new Date(exam.endAt);
  const isUpcoming = now < start;

  return (
    <div className="border rounded-xl p-4 hover:bg-muted/30 transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold truncate">{exam.title}</h3>
          <p className="text-sm text-muted-foreground">{exam.subject?.name ?? 'General'}</p>
          <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              {formatDateTime(exam.startAt)}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              {formatDuration(exam.durationMinutes * 60)}
            </span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
            isActive ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200' :
            isUpcoming ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' :
            'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200'
          }`}>
            {isActive ? 'In Progress' : isUpcoming ? 'Upcoming' : 'Ended'}
          </span>
          <Button asChild variant="outline" size="sm" disabled={!isActive}>
            <Link href={`/exam/${exam.id}`}>
              {isActive ? 'Continue' : isUpcoming ? 'View' : 'View Results'}
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function StudentDashboard() {
  const api = useApiClient();

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['student', 'stats'],
    queryFn: async () => {
      const [upcoming, completed, results] = await Promise.all([
        api.get('/student/exams/upcoming', { page_size: 5 }),
        api.get('/student/exams/completed', { page_size: 5 }),
        api.get('/student/results', { page_size: 5 }),
      ]);
      return {
        upcomingCount: upcoming.total,
        completedCount: completed.total,
        averageScore: results.items.length ? Math.round(results.items.reduce((a: number, r: any) => a + (r.percentage || 0), 0) / results.items.length) : 0,
        rank: results.items[0]?.rank ?? null,
      };
    },
  });

  const { data: upcoming, isLoading: examsLoading } = useQuery({
    queryKey: ['student', 'exams', 'upcoming'],
    queryFn: () => api.get('/student/exams/upcoming', { page_size: 4 }),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Your examination overview"
      />

      {statsLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}><CardContent className="p-6 animate-pulse space-y-2">
              <div className="h-4 w-24 bg-muted rounded" />
              <div className="h-8 w-32 bg-muted rounded" />
            </CardContent></Card>
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard title="Upcoming Exams" value={stats?.upcomingCount ?? 0} icon={FileQuestion} href="/student/exams/upcoming" />
          <StatCard title="Completed Exams" value={stats?.completedCount ?? 0} icon={CheckCircle} href="/student/exams/completed" />
          <StatCard title="Average Score" value={`${stats?.averageScore ?? 0}%`} icon={Award} href="/student/results" />
          <StatCard title="Current Rank" value={stats?.rank ?? '—'} icon={Trophy} href="/student/results" />
        </div>
      )}

      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Upcoming Exams</h2>
        <Button asChild variant="ghost" size="sm">
          <Link href="/student/exams/upcoming">View all →</Link>
        </Button>
      </div>

      {examsLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}><CardContent className="p-4 animate-pulse">
              <div className="h-5 w-48 bg-muted rounded mb-2" />
              <div className="h-4 w-64 bg-muted rounded" />
            </CardContent></Card>
          ))}
        </div>
      ) : upcoming?.items.length ? (
        <div className="space-y-3">
          {upcoming.items.map((exam: ExamPreview) => (
            <UpcomingExamCard key={exam.id} exam={exam} />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="p-8 text-center">
            <Calendar className="h-12 w-12 mx-auto text-muted-foreground/50 mb-3" />
            <h3 className="text-lg font-semibold">No upcoming exams</h3>
            <p className="text-muted-foreground mt-1">You have no exams scheduled at the moment.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}