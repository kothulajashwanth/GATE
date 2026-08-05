'use client';

import { useQuery } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import { formatDateTime, formatDuration } from '@examshield/utils';
import { Card, CardContent, Button, Badge } from '@examshield/ui';
import { History, CheckCircle, Clock, Calendar, ArrowRight, Award } from 'lucide-react';
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

export default function CompletedExamsPage() {
  const api = useApiClient();

  const { data, isLoading } = useQuery({
    queryKey: ['student', 'exams', 'completed'],
    queryFn: () => api.get<Paginated<ExamPreview>>('/student/exams/completed', { page_size: 20 }),
  });

  const exams = data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Completed Examinations"
        description="Review your past submitted tests and examine performance feedback."
      />

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6 space-y-2">
                <div className="h-5 w-1/3 bg-muted rounded" />
                <div className="h-4 w-1/4 bg-muted rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : exams.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="p-12 text-center space-y-3">
            <History className="h-12 w-12 text-muted-foreground/50 mx-auto" />
            <h3 className="text-lg font-semibold">No completed exams yet</h3>
            <p className="text-sm text-muted-foreground">
              Exams you complete will appear here along with your performance history.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {exams.map((exam) => (
            <Card key={exam.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{exam.subject?.name ?? 'General'}</Badge>
                    <Badge className="bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-500/20 border-emerald-500/30">
                      <CheckCircle className="h-3 w-3 mr-1" /> Submitted
                    </Badge>
                  </div>
                  <h3 className="text-lg font-bold">{exam.title}</h3>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3.5 w-3.5" /> {formatDateTime(exam.startAt)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5" /> {formatDuration(exam.durationMinutes * 60)}
                    </span>
                  </div>
                </div>
                <Button asChild variant="outline">
                  <Link href={`/student/results`}>
                    View Result <Award className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
