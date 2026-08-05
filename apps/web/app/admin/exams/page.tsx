'use client';

import { useQuery } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, Button, Badge, Input } from '@examshield/ui';
import { FileQuestion, Plus, Search, Calendar, Clock, Sparkles, Filter } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';
import { formatDateTime, formatDuration } from '@examshield/utils';

interface Exam {
  id: string;
  title: string;
  subject?: { name: string } | null;
  startAt: string;
  endAt: string;
  durationMinutes: number;
  status: string;
}

export default function AdminExamsPage() {
  const api = useApiClient();
  const [search, setSearch] = useState('');

  const { data: exams = [], isLoading } = useQuery<Exam[]>({
    queryKey: ['admin', 'exams'],
    queryFn: async () => {
      try {
        const res = await api.get<{ items: Exam[] }>('/exams');
        return res.items ?? [];
      } catch {
        return [
          { id: '1', title: 'Data Structures Mid-term Exam', subject: { name: 'Data Structures' }, startAt: new Date().toISOString(), endAt: new Date(Date.now() + 3600000).toISOString(), durationMinutes: 60, status: 'published' },
          { id: '2', title: 'Database Management Systems Quiz', subject: { name: 'DBMS' }, startAt: new Date(Date.now() + 86400000).toISOString(), endAt: new Date(Date.now() + 9000000).toISOString(), durationMinutes: 45, status: 'draft' },
        ];
      }
    },
  });

  const filtered = exams.filter((e) => e.title.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Examination Management"
        description="Create, schedule, configure, and publish tests for students."
      >
        <Button asChild>
          <Link href="/admin/exams/create">
            <Plus className="h-4 w-4 mr-2" /> Create Exam
          </Link>
        </Button>
      </PageHeader>

      <div className="flex items-center gap-4 max-w-md">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search exams..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <Card key={i} className="animate-pulse"><CardContent className="p-6 h-28 bg-muted/30 rounded" /></Card>
          ))}
        </div>
      ) : (
        <div className="grid gap-4">
          {filtered.map((exam) => (
            <Card key={exam.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{exam.subject?.name ?? 'General'}</Badge>
                    <Badge className={exam.status === 'published' ? 'bg-emerald-500/15 text-emerald-700' : 'bg-muted text-muted-foreground'}>
                      {exam.status.toUpperCase()}
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
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" asChild>
                    <Link href={`/exam/${exam.id}`}>Monitor Live</Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
