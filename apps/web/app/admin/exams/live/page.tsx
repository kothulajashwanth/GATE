'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import {
  Card, CardContent, CardHeader, CardTitle, Button, Badge, Input, Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Label, Textarea
} from '@examshield/ui';
import {
  ShieldCheck, AlertTriangle, Eye, XCircle, Search, Clock, Users, Activity, Loader2, History, AlertCircle
} from 'lucide-react';
import { DataTablePagination } from '@/components/data-table-pagination';
import { EmptyState } from '@/components/empty-state';
import { formatDateTime } from '@examshield/utils';
import { toast } from 'sonner';

interface LiveSessionRow {
  id: string;
  examId: string;
  studentId: string;
  studentRollNumber: string | null;
  studentName: string | null;
  status: string;
  startedAt: string;
  deadlineAt: string;
  warningCount: number;
  securityStatus: string;
}

interface TimelineEvent {
  id: string;
  violationType: string;
  warningNumber: int;
  reason: string | null;
  createdAt: string;
}

export default function AdminLiveMonitoringPage() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('active');

  // Modal States
  const [selectedSession, setSelectedSession] = useState<LiveSessionRow | null>(null);
  const [terminateModalSession, setTerminateModalSession] = useState<LiveSessionRow | null>(null);
  const [terminateReason, setTerminateReason] = useState('');
  const [isTerminating, setIsTerminating] = useState(false);

  const params: Record<string, unknown> = { page, page_size: 20 };
  if (statusFilter !== 'all') params.session_status = statusFilter;

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['admin-live-sessions', params],
    queryFn: () => api.get<{ items: LiveSessionRow[]; page: number; totalPages: number }>('/sessions', params),
    refetchInterval: 10000, // Poll live sessions every 10s
  });

  const { data: timelineEvents = [], isLoading: loadingTimeline } = useQuery<TimelineEvent[]>({
    queryKey: ['session-timeline', selectedSession?.id],
    queryFn: () => api.get<TimelineEvent[]>(`/sessions/${selectedSession?.id}/timeline`),
    enabled: !!selectedSession,
  });

  const terminateMutation = useMutation({
    mutationFn: ({ sessionId, reason }: { sessionId: string; reason: string }) =>
      api.post(`/sessions/${sessionId}/admin-terminate`, { reason }),
    onSuccess: () => {
      toast.success('Session force-terminated by Admin');
      setTerminateModalSession(null);
      setTerminateReason('');
      queryClient.invalidateQueries({ queryKey: ['admin-live-sessions'] });
    },
    onError: (e: Error) => toast.error(e.message || 'Termination failed'),
  });

  const sessions = data?.items || [];
  const activeCount = sessions.filter((s) => s.status === 'active').length;
  const highRiskCount = sessions.filter((s) => s.securityStatus === 'HIGH_RISK' || s.warningCount >= 2).length;
  const terminatedCount = sessions.filter((s) => s.status === 'terminated').length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Live Proctored Exams Monitoring Dashboard"
        description="Real-time live monitoring of active proctored exam sessions, warning counters, violation timelines, and force-termination controls."
      />

      {/* Metric Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground uppercase font-semibold">Active Live Sessions</p>
              <p className="text-2xl font-extrabold mt-1 text-primary">{activeCount}</p>
            </div>
            <div className="p-2.5 bg-primary/10 rounded-xl text-primary"><Activity className="h-5 w-5 animate-pulse" /></div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground uppercase font-semibold">High Risk / Warnings</p>
              <p className="text-2xl font-extrabold mt-1 text-amber-500">{highRiskCount}</p>
            </div>
            <div className="p-2.5 bg-amber-500/10 rounded-xl text-amber-500"><AlertTriangle className="h-5 w-5" /></div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground uppercase font-semibold">Terminated Sessions</p>
              <p className="text-2xl font-extrabold mt-1 text-rose-500">{terminatedCount}</p>
            </div>
            <div className="p-2.5 bg-rose-500/10 rounded-xl text-rose-500"><XCircle className="h-5 w-5" /></div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground uppercase font-semibold">Live System Integrity</p>
              <p className="text-2xl font-extrabold mt-1 text-emerald-600">100%</p>
            </div>
            <div className="p-2.5 bg-emerald-500/10 rounded-xl text-emerald-600"><ShieldCheck className="h-5 w-5" /></div>
          </CardContent>
        </Card>
      </div>

      {/* Filter Toolbar */}
      <div className="flex items-center gap-2">
        {['active', 'all', 'submitted', 'terminated'].map((st) => (
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

      {/* Live Sessions Table */}
      <Card className="glass-card">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-primary" /> Polling active live exam sessions...
            </div>
          ) : !sessions.length ? (
            <div className="p-8">
              <EmptyState
                title="No active sessions found"
                description="When students launch proctored examinations, their active telemetry will appear here in real-time."
              />
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow className="border-b border-border/50">
                    <TableHead>Student Roll / Name</TableHead>
                    <TableHead>Session ID</TableHead>
                    <TableHead>Started At</TableHead>
                    <TableHead>Warnings</TableHead>
                    <TableHead>Security Status</TableHead>
                    <TableHead>Session Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sessions.map((s) => (
                    <TableRow key={s.id} className="border-b border-border/40 hover:bg-white/30 dark:hover:bg-slate-800/30">
                      <TableCell className="font-semibold text-xs">
                        <div>{s.studentName || 'Student'}</div>
                        <div className="text-[10px] text-muted-foreground font-mono">{s.studentRollNumber || 'CS2026001'}</div>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">#{s.id.slice(0, 8)}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{formatDateTime(s.startedAt)}</TableCell>
                      <TableCell>
                        <Badge variant={s.warningCount >= 2 ? 'destructive' : s.warningCount === 1 ? 'secondary' : 'outline'}>
                          {s.warningCount} / 3 Warnings
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            s.securityStatus === 'TERMINATED' ? 'destructive' : s.securityStatus === 'HIGH_RISK' ? 'destructive' : s.securityStatus === 'WARNING' ? 'secondary' : 'default'
                          }
                          className="text-[10px]"
                        >
                          {s.securityStatus}
                        </Badge>
                      </TableCell>
                      <TableCell className="uppercase font-bold text-xs">{s.status}</TableCell>
                      <TableCell className="text-right flex items-center justify-end gap-1">
                        <Button size="sm" variant="ghost" onClick={() => setSelectedSession(s)}>
                          <Eye className="h-3.5 w-3.5 mr-1" /> Timeline
                        </Button>
                        {s.status === 'active' && (
                          <Button size="sm" variant="ghost" className="text-destructive hover:bg-rose-50" onClick={() => setTerminateModalSession(s)}>
                            <XCircle className="h-3.5 w-3.5 mr-1" /> Force Terminate
                          </Button>
                        )}
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

      {/* Security Violation Timeline Dialog */}
      {selectedSession && (
        <Dialog open={!!selectedSession} onOpenChange={(b) => { if (!b) setSelectedSession(null); }}>
          <DialogContent className="glass-modal max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <History className="h-5 w-5 text-primary" /> Security Violation Timeline
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-3 text-xs">
              <div className="p-3 bg-muted/40 rounded-xl space-y-1">
                <div className="font-semibold text-foreground">Student: {selectedSession.studentName || selectedSession.studentRollNumber}</div>
                <div className="text-muted-foreground">Session ID: #{selectedSession.id}</div>
              </div>

              <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                {loadingTimeline ? (
                  <div className="p-4 text-center text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin mx-auto" /> Loading security timeline...</div>
                ) : !timelineEvents.length ? (
                  <div className="p-4 text-center text-muted-foreground italic">No security violations recorded for this session.</div>
                ) : (
                  timelineEvents.map((evt) => (
                    <div key={evt.id} className="p-2.5 rounded-xl border border-rose-200 bg-rose-50/50 text-rose-800 space-y-1">
                      <div className="flex justify-between font-bold">
                        <span className="uppercase">{evt.violationType}</span>
                        <span>Warning #{evt.warningNumber}</span>
                      </div>
                      <div className="text-[11px]">{evt.reason || 'Security policy event'}</div>
                      <div className="text-[10px] text-rose-600">{formatDateTime(evt.createdAt)}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setSelectedSession(null)}>Close</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Admin Force Terminate Confirmation Dialog */}
      {terminateModalSession && (
        <Dialog open={!!terminateModalSession} onOpenChange={(b) => { if (!b) setTerminateModalSession(null); }}>
          <DialogContent className="glass-modal max-w-md">
            <DialogHeader>
              <DialogTitle className="text-rose-600 flex items-center gap-2">
                <AlertCircle className="h-5 w-5" /> Force Terminate Active Session
              </DialogTitle>
              <DialogDescription>
                Are you sure you want to force terminate the live exam attempt for {terminateModalSession.studentName || terminateModalSession.studentRollNumber}?
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-2 text-xs">
              <Label>Termination Reason *</Label>
              <Textarea
                value={terminateReason}
                onChange={(e) => setTerminateReason(e.target.value)}
                placeholder="State reason for admin termination..."
                className="glass-input"
                rows={3}
              />
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setTerminateModalSession(null)}>Cancel</Button>
              <Button
                variant="destructive"
                disabled={!terminateReason.trim()}
                onClick={() => terminateMutation.mutate({ sessionId: terminateModalSession.id, reason: terminateReason })}
              >
                Force Terminate & Lock Attempt
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
