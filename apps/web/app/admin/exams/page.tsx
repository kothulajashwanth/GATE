'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import {
  Card, CardContent, Button, Input, Badge, Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Label, Textarea,
} from '@examshield/ui';
import {
  FileQuestion, Plus, Search, MoreHorizontal, Eye, Edit3, Trash2, CheckCircle2, Clock, XCircle, Send, ShieldCheck, Layers, FileCheck, AlertTriangle, Calendar, Loader2
} from 'lucide-react';
import { DataTablePagination } from '@/components/data-table-pagination';
import { EmptyState } from '@/components/empty-state';
import { formatDateTime } from '@examshield/utils';
import { toast } from 'sonner';
import Link from 'next/link';

interface ExamRow {
  id: string;
  title: string;
  description: string | null;
  durationMinutes: number;
  startAt: string;
  endAt: string;
  passingMarks: number;
  totalMarks: number;
  status: string;
  securityMode: boolean;
  cameraProctoringEnabled: boolean;
  createdAt: string;
}

export default function ExamsPage() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('all');
  const [cancelModalExam, setCancelModalExam] = useState<ExamRow | null>(null);
  const [cancelReason, setCancelReason] = useState('');
  const [isCancelling, setIsCancelling] = useState(false);

  const params: Record<string, unknown> = { page, page_size: 20 };
  if (statusFilter !== 'all') params.exam_status = statusFilter;

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['admin-exams', params],
    queryFn: () => api.get<{ items: ExamRow[]; page: number; totalPages: number }>('/exams', params),
  });

  const publishMutation = useMutation({
    mutationFn: (examId: string) => api.post(`/exams/${examId}/publish`),
    onSuccess: () => {
      toast.success('Exam published successfully! Eligible students can now see the schedule.');
      queryClient.invalidateQueries({ queryKey: ['admin-exams'] });
    },
    onError: (e: Error) => toast.error(e.message || 'Publishing failed'),
  });

  const cancelMutation = useMutation({
    mutationFn: ({ examId, reason }: { examId: string; reason: string }) =>
      api.post(`/exams/${examId}/cancel`, { reason }),
    onSuccess: () => {
      toast.success('Exam cancelled');
      setCancelModalExam(null);
      setCancelReason('');
      queryClient.invalidateQueries({ queryKey: ['admin-exams'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (examId: string) => api.delete(`/exams/${examId}`),
    onSuccess: () => {
      toast.success('Exam draft deleted');
      queryClient.invalidateQueries({ queryKey: ['admin-exams'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const getStatusBadge = (statusStr: string) => {
    switch (statusStr.toLowerCase()) {
      case 'published':
        return <Badge variant="default" className="bg-emerald-600">Published</Badge>;
      case 'live':
      case 'in_progress':
        return <Badge variant="default" className="bg-blue-600 animate-pulse">LIVE NOW</Badge>;
      case 'scheduled':
        return <Badge variant="secondary">Scheduled</Badge>;
      case 'completed':
        return <Badge variant="outline" className="bg-slate-100 text-slate-700">Completed</Badge>;
      case 'cancelled':
        return <Badge variant="destructive">Cancelled</Badge>;
      default:
        return <Badge variant="outline">Draft</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Examinations Management Portal"
        description="Build multi-step exams, assign Question Bank questions, target student cohorts, set proctoring security policies, and publish schedules."
      >
        <Link href="/admin/exams/blueprint">
          <Button size="sm" variant="outline" className="glass-button">
            <Layers className="h-4 w-4 mr-1 text-primary" /> Exam Blueprint
          </Button>
        </Link>
        <Link href="/admin/exams/create">
          <Button size="sm" className="glass-button bg-primary text-white">
            <Plus className="h-4 w-4 mr-1" /> Create Examination Wizard
          </Button>
        </Link>
      </PageHeader>

      {/* Filter Toolbar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto pb-2 sm:pb-0">
          {['all', 'draft', 'scheduled', 'published', 'live', 'completed', 'cancelled'].map((st) => (
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
      </div>

      <Card className="glass-card">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-primary" /> Loading examinations from database...
            </div>
          ) : !data?.items.length ? (
            <div className="p-8">
              <EmptyState
                title="No examination schedules found"
                description="Click 'Create Examination Wizard' to configure an exam schedule."
                action={
                  <Link href="/admin/exams/create">
                    <Button size="sm"><Plus className="h-4 w-4 mr-1" /> Create Examination</Button>
                  </Link>
                }
              />
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow className="border-b border-border/50">
                    <TableHead>Exam Title</TableHead>
                    <TableHead>Active Window</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Marks</TableHead>
                    <TableHead>Proctoring</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((exam) => (
                    <TableRow key={exam.id} className="border-b border-border/40 hover:bg-white/30 dark:hover:bg-slate-800/30">
                      <TableCell className="font-bold text-xs">
                        <div>{exam.title}</div>
                        <div className="text-[10px] text-muted-foreground font-mono">ID: #{exam.id.slice(0, 8)}</div>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        <div className="flex items-center gap-1"><Calendar className="h-3 w-3 text-primary" /> {formatDateTime(exam.startAt)}</div>
                        <div className="flex items-center gap-1 text-[10px]">to {formatDateTime(exam.endAt)}</div>
                      </TableCell>
                      <TableCell className="text-xs font-semibold">{exam.durationMinutes} mins</TableCell>
                      <TableCell className="text-xs font-semibold">{exam.totalMarks} Marks</TableCell>
                      <TableCell>
                        <Badge variant={exam.securityMode ? 'default' : 'outline'} className="text-[10px]">
                          {exam.securityMode ? 'Proctored' : 'Standard'}
                        </Badge>
                      </TableCell>
                      <TableCell>{getStatusBadge(exam.status)}</TableCell>
                      <TableCell className="text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon"><MoreHorizontal className="h-4 w-4" /></Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="glass-modal">
                            {exam.status === 'draft' && (
                              <DropdownMenuItem onClick={() => publishMutation.mutate(exam.id)}>
                                <Send className="h-4 w-4 mr-2 text-emerald-600" /> Publish Exam
                              </DropdownMenuItem>
                            )}
                            {exam.status !== 'completed' && exam.status !== 'cancelled' && (
                              <DropdownMenuItem onClick={() => setCancelModalExam(exam)}>
                                <XCircle className="h-4 w-4 mr-2 text-amber-600" /> Cancel Exam
                              </DropdownMenuItem>
                            )}
                            {exam.status === 'draft' && (
                              <DropdownMenuItem className="text-destructive" onClick={() => deleteMutation.mutate(exam.id)}>
                                <Trash2 className="h-4 w-4 mr-2" /> Delete Draft
                              </DropdownMenuItem>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="p-4">
                <DataTablePagination page={page} totalPages={data.totalPages} onPageChange={setPage} />
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Cancel Exam Modal */}
      {cancelModalExam && (
        <Dialog open={!!cancelModalExam} onOpenChange={(b) => { if (!b) setCancelModalExam(null); }}>
          <DialogContent className="glass-modal max-w-md">
            <DialogHeader>
              <DialogTitle>Cancel Examination Schedule</DialogTitle>
              <DialogDescription>
                Are you sure you want to cancel {cancelModalExam.title}? Please state a cancellation reason for audit logging.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-2 text-xs">
              <Label>Cancellation Reason *</Label>
              <Textarea
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder="e.g. Schedule conflict / technical rescheduling..."
                className="glass-input"
                rows={3}
              />
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setCancelModalExam(null)}>Close</Button>
              <Button
                variant="destructive"
                disabled={!cancelReason.trim()}
                onClick={() => cancelMutation.mutate({ examId: cancelModalExam.id, reason: cancelReason })}
              >
                Confirm Cancellation
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
