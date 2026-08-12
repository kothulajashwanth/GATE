'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import {
  Card, CardContent, CardHeader, CardTitle, Button, Badge, Input, Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle
} from '@examshield/ui';
import {
  Award, Send, RefreshCw, Eye, CheckCircle2, XCircle, Search, Loader2, Sparkles, AlertTriangle
} from 'lucide-react';
import { DataTablePagination } from '@/components/data-table-pagination';
import { EmptyState } from '@/components/empty-state';
import { formatDateTime } from '@examshield/utils';
import { toast } from 'sonner';

interface AdminResultRow {
  id: string;
  examId: string;
  examTitle: string | null;
  studentRollNumber: string | null;
  studentName: string | null;
  totalMarks: number;
  obtainedMarks: number;
  percentage: number;
  rank: number | null;
  isPassed: boolean | null;
  status: string;
  publishedAt: string | null;
}

export default function AdminResultsPage() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedResult, setSelectedResult] = useState<AdminResultRow | null>(null);

  const params: Record<string, unknown> = { page, page_size: 20 };
  if (statusFilter !== 'all') params.result_status = statusFilter;

  const { data, isLoading } = useQuery({
    queryKey: ['admin-results', params],
    queryFn: () => api.get<{ items: AdminResultRow[]; page: number; totalPages: number }>('/results/admin', params),
  });

  const publishMutation = useMutation({
    mutationFn: (resultId: string) => api.post(`/results/admin/${resultId}/publish`),
    onSuccess: () => {
      toast.success('Result published to student portal!');
      queryClient.invalidateQueries({ queryKey: ['admin-results'] });
    },
    onError: (e: Error) => toast.error(e.message || 'Publish failed'),
  });

  const recalculateMutation = useMutation({
    mutationFn: (resultId: string) => api.post(`/results/admin/${resultId}/recalculate`),
    onSuccess: () => {
      toast.success('Result score snapshot recalculated!');
      queryClient.invalidateQueries({ queryKey: ['admin-results'] });
    },
    onError: (e: Error) => toast.error(e.message || 'Recalculation failed'),
  });

  const results = data?.items || [];
  const publishedCount = results.filter((r) => r.status === 'published').length;
  const autoCount = results.filter((r) => r.status === 'auto' || r.status === 'pending').length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Examination Results & Grading Management"
        description="Review server-evaluated results, trigger score recalculations, assign manual marks, and publish final grade reports to student portals."
      />

      {/* Metric Overview */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground uppercase font-semibold">Total Results Evaluated</p>
              <p className="text-2xl font-extrabold mt-1 text-primary">{results.length}</p>
            </div>
            <div className="p-2.5 bg-primary/10 rounded-xl text-primary"><Award className="h-5 w-5" /></div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground uppercase font-semibold">Published Results</p>
              <p className="text-2xl font-extrabold mt-1 text-emerald-600">{publishedCount}</p>
            </div>
            <div className="p-2.5 bg-emerald-500/10 rounded-xl text-emerald-600"><CheckCircle2 className="h-5 w-5" /></div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground uppercase font-semibold">Pending / Unpublished</p>
              <p className="text-2xl font-extrabold mt-1 text-amber-500">{autoCount}</p>
            </div>
            <div className="p-2.5 bg-amber-500/10 rounded-xl text-amber-500"><Send className="h-5 w-5" /></div>
          </CardContent>
        </Card>
      </div>

      {/* Status Filter */}
      <div className="flex items-center gap-2">
        {['all', 'auto', 'published', 'withheld'].map((st) => (
          <Button
            key={st}
            size="sm"
            variant={statusFilter === st ? 'default' : 'outline'}
            className="capitalize text-xs glass-button"
            onClick={() => { setStatusFilter(st); setPage(1); }}
          >
            {st}
          </Button>
        ))}
      </div>

      {/* Results Table */}
      <Card className="glass-card">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-primary" /> Loading evaluated exam results...
            </div>
          ) : !results.length ? (
            <div className="p-8">
              <EmptyState
                title="No exam results found"
                description="Results will automatically be computed when students submit completed exam sessions."
              />
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow className="border-b border-border/50">
                    <TableHead>Student Roll / Name</TableHead>
                    <TableHead>Examination</TableHead>
                    <TableHead>Marks Obtained</TableHead>
                    <TableHead>Percentage</TableHead>
                    <TableHead>Pass Status</TableHead>
                    <TableHead>Result Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.map((r) => (
                    <TableRow key={r.id} className="border-b border-border/40 hover:bg-white/30 dark:hover:bg-slate-800/30">
                      <TableCell className="font-semibold text-xs">
                        <div>{r.studentName || 'Student'}</div>
                        <div className="text-[10px] text-muted-foreground font-mono">{r.studentRollNumber || 'CS2026001'}</div>
                      </TableCell>
                      <TableCell className="text-xs font-semibold">{r.examTitle || 'Exam'}</TableCell>
                      <TableCell className="text-xs font-bold">{r.obtainedMarks} / {r.totalMarks}</TableCell>
                      <TableCell className="text-xs font-bold text-emerald-600">{r.percentage}%</TableCell>
                      <TableCell>
                        <Badge variant={r.isPassed ? 'default' : 'destructive'} className={r.isPassed ? 'bg-emerald-600 text-[10px]' : 'text-[10px]'}>
                          {r.isPassed ? 'PASSED' : 'FAILED'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={r.status === 'published' ? 'default' : 'outline'} className="text-[10px] uppercase">
                          {r.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right flex items-center justify-end gap-1">
                        {r.status !== 'published' && (
                          <Button size="sm" variant="ghost" className="text-emerald-600" onClick={() => publishMutation.mutate(r.id)}>
                            <Send className="h-3.5 w-3.5 mr-1" /> Publish
                          </Button>
                        )}
                        <Button size="sm" variant="ghost" onClick={() => recalculateMutation.mutate(r.id)}>
                          <RefreshCw className="h-3.5 w-3.5 mr-1" /> Recalculate
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="p-4">
                <DataTablePagination page={page} totalPages={data?.totalPages || 1} onPageChange={setPage} />
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
