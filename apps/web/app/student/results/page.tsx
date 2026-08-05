'use client';

import { useQuery } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, Badge, Button } from '@examshield/ui';
import { Trophy, Award, CheckCircle, XCircle } from 'lucide-react';
import type { Paginated } from '@examshield/types';

interface ResultRow {
  id: string;
  examId: string;
  percentage: number | null;
  rank: number | null;
  isPassed: boolean | null;
  status: string;
}

export default function ResultsPage() {
  const api = useApiClient();

  const { data, isLoading } = useQuery({
    queryKey: ['student', 'results'],
    queryFn: () => api.get<Paginated<ResultRow>>('/student/results', { page_size: 20 }),
  });

  const results = data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Examination Results"
        description="Your academic performance and leaderboard status."
      />

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6 h-24 bg-muted/50 rounded" />
            </Card>
          ))}
        </div>
      ) : results.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="p-12 text-center space-y-3">
            <Trophy className="h-12 w-12 text-muted-foreground/50 mx-auto" />
            <h3 className="text-lg font-semibold">No results published yet</h3>
            <p className="text-sm text-muted-foreground">
              Exam results will appear here once graded and published by your faculty.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {results.map((r) => (
            <Card key={r.id}>
              <CardContent className="p-6 flex items-center justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold">Exam ID: {r.examId}</p>
                    <Badge variant={r.isPassed ? 'default' : 'destructive'}>
                      {r.isPassed ? 'Passed' : 'Failed'}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">Rank: #{r.rank ?? 'N/A'}</p>
                </div>
                <div className="text-right">
                  <p className="text-3xl font-bold">{r.percentage ?? 0}%</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
