'use client';

import { Card, CardContent, CardHeader, CardTitle, Button } from '@examshield/ui';
import { FileQuestion, Trophy, Clock, Award, Calendar, CheckCircle, AlertCircle, ArrowRight, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { PageHeader } from '@/components/page-header';
import { useAuth } from '@clerk/nextjs';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { useApiClient } from '@/lib/api/client-provider';
import { formatDateTime, formatDuration } from '@examshield/utils';
import Link from 'next/link';

import type { Paginated } from '@examshield/types';

interface ExamPreview {
  id: string;
  title: string;
  subject: { name: string } | null;
  startAt: string;
  endAt: string;
  durationMinutes: number;
  status: string;
}

interface ResultRow {
  id: string;
  examId: string;
  percentage: number | null;
  rank: number | null;
  isPassed: boolean | null;
  status: string;
}

function StatCard({ title, value, icon: Icon, href }: { title: string; value: string | number; icon: React.ComponentType<{ className?: string }>; href?: string }) {
  return (
    <Card className="glass-card overflow-hidden border border-white/20 dark:border-white/10">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{title}</p>
            <p className="text-3xl font-extrabold mt-1 text-foreground tracking-tight">{value}</p>
          </div>
          <div className="p-3 bg-primary/10 rounded-2xl border border-primary/20 text-primary">
            <Icon className="h-6 w-6" />
          </div>
        </div>
        {href && (
          <Link href={href} className="mt-4 text-xs text-primary font-bold flex items-center gap-1 hover:underline">
            View all <ArrowRight className="h-3 w-3" />
          </Link>
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
    <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-xl border border-border/50 bg-white/40 dark:bg-slate-800/40 gap-4">
      <div className="space-y-1">
        <div className="font-bold text-sm text-foreground">{exam.title}</div>
        <div className="text-xs text-muted-foreground flex items-center gap-3">
          <span>Subject: {exam.subject?.name ?? 'General'}</span>
          <span>Duration: {exam.durationMinutes} mins</span>
        </div>
        <div className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
          <Calendar className="h-3.5 w-3.5 text-primary" />
          {formatDateTime(exam.startAt)}
        </div>
      </div>
      <div>
        {isActive ? (
          <Link href={`/exam/${exam.id}`}>
            <Button size="sm" className="glass-button bg-emerald-600 hover:bg-emerald-700 text-white">
              Start Exam Now
            </Button>
          </Link>
        ) : isUpcoming ? (
          <Button size="sm" variant="outline" disabled className="glass-button">
            Scheduled
          </Button>
        ) : (
          <Button size="sm" variant="ghost" disabled>
            Ended
          </Button>
        )}
      </div>
    </div>
  );
}

import { ActiveStudentAttendanceCheckinCard } from '@/components/active-student-attendance-checkin-card';

export default function StudentDashboard() {
  const api = useApiClient();
  const { isLoaded, isSignedIn } = useAuth();

  const { data: examsData, isLoading: loadingExams } = useQuery({
    queryKey: ['student', 'exams', isLoaded, isSignedIn],
    queryFn: () => api.get<Paginated<ExamPreview>>('/student/exams/upcoming', { page_size: 5, page: 1 }),
    enabled: isLoaded && isSignedIn,
    retry: 2,
  });

  const { data: resultsData, isLoading: loadingResults } = useQuery({
    queryKey: ['student', 'results', isLoaded, isSignedIn],
    queryFn: () => api.get<Paginated<ResultRow>>('/results', { page_size: 5, page: 1 }),
    enabled: isLoaded && isSignedIn,
    retry: 2,
  });

  const exams = examsData?.items ?? [];
  const results = resultsData?.items ?? [];

  const passedCount = results.filter((r) => r.isPassed === true).length;
  const avgPercentage = results.length
    ? Math.round(results.reduce((acc, r) => acc + (r.percentage ?? 0), 0) / results.length)
    : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Student Examination Dashboard"
        description="View available scheduled exams, launch proctored sessions, and track performance results."
      />

      <ActiveStudentAttendanceCheckinCard />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">


        <StatCard title="Available Exams" value={exams.length} icon={FileQuestion} href="/student/exams/upcoming" />
        <StatCard title="Exams Completed" value={results.length} icon={CheckCircle} href="/student/results" />
        <StatCard title="Passed Exams" value={passedCount} icon={Trophy} />
        <StatCard title="Average Score" value={`${avgPercentage}%`} icon={Award} />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <Clock className="h-5 w-5 text-primary" /> Scheduled & Active Examinations
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {loadingExams ? (
              <div className="p-4 text-center text-xs text-muted-foreground">Loading exam schedules...</div>
            ) : !exams.length ? (
              <div className="p-6 text-center text-xs text-muted-foreground">No active examinations scheduled right now.</div>
            ) : (
              exams.map((exam) => <UpcomingExamCard key={exam.id} exam={exam} />)
            )}
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <Award className="h-5 w-5 text-amber-500" /> Recent Examination Performance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {loadingResults ? (
              <div className="p-4 text-center text-xs text-muted-foreground">Loading results...</div>
            ) : !results.length ? (
              <div className="p-6 text-center text-xs text-muted-foreground">No examination attempts recorded yet.</div>
            ) : (
              results.map((r) => (
                <div key={r.id} className="flex items-center justify-between p-3 rounded-xl border border-border/40 bg-white/30 dark:bg-slate-800/30 text-xs">
                  <div>
                    <div className="font-semibold text-foreground">Exam Attempt #{r.id.slice(0, 8)}</div>
                    <div className="text-muted-foreground">Score: {r.percentage ?? 0}%</div>
                  </div>
                  <div>
                    {r.isPassed ? (
                      <span className="px-2.5 py-1 rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 font-bold text-[10px]">PASSED</span>
                    ) : (
                      <span className="px-2.5 py-1 rounded-full bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300 font-bold text-[10px]">FAILED</span>
                    )}
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}