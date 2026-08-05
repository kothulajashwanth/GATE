'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import { formatDateTime, formatDuration } from '@examshield/utils';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
  Badge,
  Input,
} from '@examshield/ui';
import {
  Calendar,
  Clock,
  FileQuestion,
  Search,
  BookOpen,
  ArrowRight,
  ShieldCheck,
  AlertCircle,
  Sparkles,
  CheckCircle2,
  Filter,
  RefreshCw,
} from 'lucide-react';
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

export default function UpcomingExamsPage() {
  const api = useApiClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [filterTab, setFilterTab] = useState<'all' | 'live' | 'upcoming'>('all');

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['student', 'exams', 'upcoming'],
    queryFn: () => api.get<Paginated<ExamPreview>>('/student/exams/upcoming', { page_size: 50 }),
  });

  const rawExams = data?.items ?? [];

  // Categorize and filter exams
  const filteredExams = useMemo(() => {
    const now = new Date();
    return rawExams.filter((exam) => {
      const start = new Date(exam.startAt);
      const end = new Date(exam.endAt);
      const isLive = now >= start && now <= end;
      const isUpcoming = now < start;

      // Filter by tab
      if (filterTab === 'live' && !isLive) return false;
      if (filterTab === 'upcoming' && !isUpcoming) return false;

      // Filter by search query
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesTitle = exam.title.toLowerCase().includes(query);
        const matchesSubject = exam.subject?.name?.toLowerCase().includes(query) ?? false;
        return matchesTitle || matchesSubject;
      }

      return true;
    });
  }, [rawExams, filterTab, searchQuery]);

  // Summary counts
  const liveCount = useMemo(() => {
    const now = new Date();
    return rawExams.filter((e) => {
      const start = new Date(e.startAt);
      const end = new Date(e.endAt);
      return now >= start && now <= end;
    }).length;
  }, [rawExams]);

  const upcomingCount = useMemo(() => {
    const now = new Date();
    return rawExams.filter((e) => new Date(e.startAt) > now).length;
  }, [rawExams]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Upcoming Examinations"
        description="View and launch scheduled tests for your department & semester."
      />

      {/* Stats Summary Bar */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="bg-card/50 backdrop-blur-sm border shadow-sm">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 bg-primary/10 rounded-xl text-primary">
              <FileQuestion className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground">Total Scheduled</p>
              <p className="text-2xl font-bold">{rawExams.length}</p>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 backdrop-blur-sm border shadow-sm">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 bg-emerald-500/10 rounded-xl text-emerald-600 dark:text-emerald-400">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground">Active / Live Now</p>
              <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{liveCount}</p>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 backdrop-blur-sm border shadow-sm">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 bg-blue-500/10 rounded-xl text-blue-600 dark:text-blue-400">
              <Calendar className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground">Starting Soon</p>
              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{upcomingCount}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters & Search Controls */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search by exam title or subject..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 bg-background"
          />
        </div>

        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-lg bg-muted p-1 text-sm font-medium">
            <button
              onClick={() => setFilterTab('all')}
              className={`px-3 py-1.5 rounded-md transition-all ${
                filterTab === 'all'
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              All ({rawExams.length})
            </button>
            <button
              onClick={() => setFilterTab('live')}
              className={`px-3 py-1.5 rounded-md transition-all ${
                filterTab === 'live'
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Live ({liveCount})
            </button>
            <button
              onClick={() => setFilterTab('upcoming')}
              className={`px-3 py-1.5 rounded-md transition-all ${
                filterTab === 'upcoming'
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Upcoming ({upcomingCount})
            </button>
          </div>
          <Button variant="outline" size="icon" onClick={() => refetch()} title="Refresh list">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Exam List Grid */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6 space-y-3">
                <div className="h-5 w-1/3 bg-muted rounded" />
                <div className="h-4 w-1/4 bg-muted rounded" />
                <div className="h-4 w-1/2 bg-muted rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : isError ? (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="p-8 text-center space-y-3">
            <AlertCircle className="h-10 w-10 text-destructive mx-auto" />
            <h3 className="text-lg font-semibold text-destructive">Failed to load upcoming exams</h3>
            <p className="text-sm text-muted-foreground">
              There was an issue connecting to the examination server.
            </p>
            <Button variant="outline" onClick={() => refetch()}>
              Try Again
            </Button>
          </CardContent>
        </Card>
      ) : filteredExams.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="p-12 text-center space-y-4">
            <div className="mx-auto w-12 h-12 rounded-full bg-muted flex items-center justify-center">
              <FileQuestion className="h-6 w-6 text-muted-foreground" />
            </div>
            <div>
              <h3 className="text-lg font-semibold">No upcoming exams found</h3>
              <p className="text-sm text-muted-foreground mt-1 max-w-sm mx-auto">
                {searchQuery || filterTab !== 'all'
                  ? 'No exams match your search filters. Try clearing your search query.'
                  : 'You have no scheduled exams at this time. Check back later for new announcements.'}
              </p>
            </div>
            {(searchQuery || filterTab !== 'all') && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setSearchQuery('');
                  setFilterTab('all');
                }}
              >
                Clear Filters
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {filteredExams.map((exam) => {
            const now = new Date();
            const start = new Date(exam.startAt);
            const end = new Date(exam.endAt);
            const isLive = now >= start && now <= end;
            const isUpcoming = now < start;
            const isEnded = now > end;

            return (
              <Card
                key={exam.id}
                className={`transition-all duration-200 hover:shadow-md ${
                  isLive
                    ? 'border-emerald-500/50 dark:border-emerald-500/30 bg-emerald-500/5'
                    : ''
                }`}
              >
                <CardContent className="p-6">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                    {/* Details */}
                    <div className="space-y-3 flex-1">
                      <div className="flex items-center gap-3 flex-wrap">
                        <Badge variant="outline" className="font-normal bg-background">
                          <BookOpen className="h-3 w-3 mr-1 text-primary" />
                          {exam.subject?.name ?? 'General Subject'}
                        </Badge>

                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                            isLive
                              ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 animate-pulse'
                              : isUpcoming
                              ? 'bg-blue-500/15 text-blue-700 dark:text-blue-400 border border-blue-500/30'
                              : 'bg-muted text-muted-foreground'
                          }`}
                        >
                          {isLive && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />}
                          {isLive ? 'LIVE NOW' : isUpcoming ? 'Scheduled' : 'Concluded'}
                        </span>
                      </div>

                      <h2 className="text-xl font-bold tracking-tight">{exam.title}</h2>

                      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1.5">
                          <Calendar className="h-4 w-4 text-primary/70" />
                          {formatDateTime(exam.startAt)}
                        </span>
                        <span className="flex items-center gap-1.5">
                          <Clock className="h-4 w-4 text-primary/70" />
                          {formatDuration(exam.durationMinutes * 60)}
                        </span>
                        <span className="flex items-center gap-1.5">
                          <ShieldCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                          AI Secure Proctoring
                        </span>
                      </div>
                    </div>

                    {/* Action Button */}
                    <div className="flex flex-col sm:flex-row md:flex-col items-stretch md:items-end justify-center gap-2 min-w-[160px]">
                      {isLive ? (
                        <Button asChild size="lg" className="w-full bg-emerald-600 hover:bg-emerald-700 text-white shadow-md">
                          <Link href={`/exam/${exam.id}`}>
                            Enter Exam <ArrowRight className="ml-2 h-4 w-4" />
                          </Link>
                        </Button>
                      ) : isUpcoming ? (
                        <Button asChild variant="outline" size="lg" className="w-full">
                          <Link href={`/exam/${exam.id}`}>
                            View Instructions
                          </Link>
                        </Button>
                      ) : (
                        <Button asChild variant="secondary" size="lg" className="w-full">
                          <Link href={`/student/results`}>
                            View Results
                          </Link>
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
