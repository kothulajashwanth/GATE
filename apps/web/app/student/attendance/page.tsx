'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import {
  Card, CardContent, CardHeader, CardTitle, Button, Badge, Input,
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Progress
} from '@examshield/ui';
import {
  QrCode, CheckCircle2, XCircle, Clock, Percent, ShieldCheck, AlertCircle, Loader2, Sparkles, Send, BookOpen
} from 'lucide-react';
import { toast } from 'sonner';

interface StudentAttendanceSummary {
  overallPercentage: number;
  totalSessions: number;
  presentCount: number;
  absentCount: number;
  lateCount: number;
  subjectBreakdown: {
    subjectName: string;
    total: number;
    present: number;
    absent: number;
    percentage: number;
  }[];
  history: {
    id: string;
    sessionTitle: string;
    subjectName: string;
    sessionDate: string;
    status: 'PRESENT' | 'ABSENT' | 'LATE';
    markedAt: string;
  }[];
}

function ActiveStudentAttendanceCheckinCard() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  const sessionIdFromUrl = typeof window !== 'undefined' ? new URLSearchParams(window.location.search).get('session') : null;

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['student-active-attendance-page', sessionIdFromUrl],
    queryFn: () => api.get<any>('/attendance/active', sessionIdFromUrl ? { session_id: sessionIdFromUrl } : undefined),
    refetchInterval: 5000,
  });


  const respondMutation = useMutation({
    mutationFn: ({ sessionId, status }: { sessionId: string; status: 'PRESENT' | 'ABSENT' }) =>
      api.post(`/attendance/sessions/${sessionId}/respond`, { status }),
    onSuccess: (res: any) => {
      toast.success(`Attendance Recorded! Status: ${res.status}`);
      refetch();
      queryClient.invalidateQueries({ queryKey: ['student-attendance-summary'] });
    },
    onError: (e: Error) => {
      toast.error(e.message || 'Failed to submit attendance response.');
    },
  });

  if (isLoading || !data?.hasActiveSession || !data?.session) {
    return null;
  }

  const { session, myResponse } = data;
  const remainingMinutes = Math.floor((session.remainingSeconds || 0) / 60);
  const remainingSecs = (session.remainingSeconds || 0) % 60;
  const timerStr = `${String(remainingMinutes).padStart(2, '0')}:${String(remainingSecs).padStart(2, '0')}`;

  return (
    <Card className="glass-card border-2 border-primary/60 bg-primary/5 shadow-xl relative overflow-hidden">
      <CardContent className="p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-primary/20 pb-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="bg-emerald-600 text-white font-bold text-[11px] px-2.5 py-0.5 rounded-md animate-pulse">
                🔔 ATTENDANCE IS OPEN
              </span>
              <span className="text-xs font-mono text-amber-500 font-bold flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" /> Time Remaining: {timerStr}
              </span>
            </div>
            <h3 className="text-base font-extrabold text-foreground tracking-tight mt-1">
              {session.subjectName}
            </h3>
            <p className="text-xs text-muted-foreground font-medium">
              Batch: <span className="font-semibold text-foreground">{session.batchName}</span> | Date: {session.sessionDate ? new Date(session.sessionDate).toLocaleDateString() : 'Today'}
            </p>
          </div>
        </div>

        {myResponse ? (
          <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="flex items-center gap-2 font-bold text-emerald-600 text-sm">
                <CheckCircle2 className="h-4 w-4" /> Attendance Recorded Successfully
              </div>
              <p className="text-xs text-muted-foreground">
                Recorded at: {myResponse.markedAt ? new Date(myResponse.markedAt).toLocaleTimeString() : 'Just now'}
              </p>
            </div>
            <span
              className={myResponse.status === 'PRESENT' ? 'px-3 py-1 rounded-full bg-emerald-600 text-white font-bold text-xs' : 'px-3 py-1 rounded-full bg-rose-600 text-white font-bold text-xs'}
            >
              Status: {myResponse.status}
            </span>
          </div>
        ) : (
          <div className="space-y-3 pt-1">
            <p className="text-xs font-semibold text-foreground">
              Please check in your attendance status for this live class session:
            </p>
            <div className="flex flex-wrap gap-3">
              <Button
                size="sm"
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-5 py-2 cursor-pointer shadow-md flex-1 sm:flex-initial"
                disabled={respondMutation.isPending}
                onClick={() => respondMutation.mutate({ sessionId: session.id, status: 'PRESENT' })}
              >
                <CheckCircle2 className="h-4 w-4 mr-2" /> ✓ MARK PRESENT
              </Button>
              <Button
                size="sm"
                variant="destructive"
                className="font-bold px-5 py-2 cursor-pointer shadow-md flex-1 sm:flex-initial"
                disabled={respondMutation.isPending}
                onClick={() => respondMutation.mutate({ sessionId: session.id, status: 'ABSENT' })}
              >
                <XCircle className="h-4 w-4 mr-2" /> ✕ MARK ABSENT
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function StudentAttendancePage() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  const [scanToken, setScanToken] = useState('');
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);

  // Queries
  const { data: summary, isLoading: loadingSummary, refetch } = useQuery<StudentAttendanceSummary>({
    queryKey: ['student-attendance-summary'],
    queryFn: () => api.get<StudentAttendanceSummary>('/attendance/students/me'),
  });

  const { data: activeSessionsData } = useQuery({
    queryKey: ['active-attendance-sessions'],
    queryFn: () => api.get<any>('/attendance/sessions', { status_filter: 'ACTIVE', page_size: 10 }),
  });

  const activeSessions = activeSessionsData?.items || [];

  // Mutation
  const scanMutation = useMutation({
    mutationFn: ({ sessionId, token }: { sessionId: string; token: string }) =>
      api.post('/attendance/scan', { sessionId, token }),
    onSuccess: (res: any) => {
      toast.success(`Attendance Marked! Marked ${res.status} for ${res.sessionTitle || 'class session'}.`);
      setScanToken('');
      setSelectedSessionId(null);
      refetch();
      queryClient.invalidateQueries({ queryKey: ['student-attendance-summary'] });
    },
    onError: (e: Error) => {
      toast.error(e.message || 'Failed to mark attendance. Check QR token.');
    },
  });

  const handleScanSubmit = (sessionId: string) => {
    if (!scanToken.trim()) {
      toast.error('Please enter or scan the dynamic QR token');
      return;
    }
    scanMutation.mutate({ sessionId, token: scanToken.trim() });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="My Attendance Dashboard"
        description="View your personal attendance percentages, subject-wise statistics, conduct history, and scan live classroom QR codes."
      />

      <ActiveStudentAttendanceCheckinCard />


      {/* Metrics Header */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground font-semibold uppercase">Overall Attendance</p>
              <p className="text-2xl font-extrabold mt-1 text-emerald-600">{summary?.overallPercentage ?? 100}%</p>
            </div>
            <div className="p-2.5 bg-emerald-500/10 rounded-xl text-emerald-600"><Percent className="h-5 w-5" /></div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground font-semibold uppercase">Total Classes</p>
              <p className="text-2xl font-extrabold mt-1 text-primary">{summary?.totalSessions ?? 0}</p>
            </div>
            <div className="p-2.5 bg-primary/10 rounded-xl text-primary"><BookOpen className="h-5 w-5" /></div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground font-semibold uppercase">Present Count</p>
              <p className="text-2xl font-extrabold mt-1 text-emerald-600">{summary?.presentCount ?? 0}</p>
            </div>
            <div className="p-2.5 bg-emerald-500/10 rounded-xl text-emerald-600"><CheckCircle2 className="h-5 w-5" /></div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground font-semibold uppercase">Absent Count</p>
              <p className="text-2xl font-extrabold mt-1 text-rose-600">{summary?.absentCount ?? 0}</p>
            </div>
            <div className="p-2.5 bg-rose-500/10 rounded-xl text-rose-600"><XCircle className="h-5 w-5" /></div>
          </CardContent>
        </Card>
      </div>

      {/* Active Session QR Scanner Panel */}
      <Card className="glass-card border-primary/30">
        <CardHeader className="py-3">
          <CardTitle className="text-sm font-bold text-primary flex items-center gap-2">
            <QrCode className="h-5 w-5 text-primary" /> Active Live Classroom Sessions
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-xs">
          {!activeSessions.length ? (
            <div className="p-6 text-center text-muted-foreground space-y-1 bg-muted/20 rounded-xl border border-border/30">
              <p className="font-semibold text-sm">No active attendance sessions in progress.</p>
              <p className="text-xs">When your instructor activates a class session, it will appear here for QR scanning.</p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {activeSessions.map((s: any) => (
                <div key={s.id} className="p-4 rounded-xl border border-primary/40 bg-primary/5 space-y-3">
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-foreground text-sm">{s.title}</span>
                      <Badge className="bg-emerald-600 text-white text-[10px]">LIVE ACTIVE</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {s.subject?.name || 'General Subject'} | {s.department?.name || 'All Departments'}
                    </p>
                  </div>

                  <div className="space-y-2 pt-2 border-t border-border/30">
                    <span className="text-[11px] font-semibold text-muted-foreground">Enter 16-Character Dynamic Token or Scan:</span>
                    <div className="flex gap-2">
                      <Input
                        placeholder="e.g. 4a8b9f12c3e4567d"
                        value={selectedSessionId === s.id ? scanToken : ''}
                        onChange={(e) => {
                          setSelectedSessionId(s.id);
                          setScanToken(e.target.value);
                        }}
                        className="glass-input text-xs font-mono"
                      />
                      <Button
                        size="sm"
                        className="glass-button bg-primary text-white flex-shrink-0"
                        disabled={scanMutation.isPending}
                        onClick={() => handleScanSubmit(s.id)}
                      >
                        {scanMutation.isPending && selectedSessionId === s.id ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Send className="h-3.5 w-3.5" />
                        )}
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Subject-Wise Breakdown Table */}
      <Card className="glass-card">
        <CardHeader className="py-3">
          <CardTitle className="text-sm font-bold flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-emerald-600" /> Subject-Wise Attendance Breakdown
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {!summary?.subjectBreakdown?.length ? (
            <p className="text-muted-foreground text-xs text-center py-6">No subject attendance history recorded yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-b border-border/50 text-xs">
                  <TableHead>Subject</TableHead>
                  <TableHead>Classes Conducted</TableHead>
                  <TableHead>Present</TableHead>
                  <TableHead>Absent</TableHead>
                  <TableHead>Attendance Percentage</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {summary.subjectBreakdown.map((sb, idx) => (
                  <TableRow key={idx} className="border-b border-border/40 text-xs">
                    <TableCell className="font-bold text-foreground">{sb.subjectName}</TableCell>
                    <TableCell>{sb.total}</TableCell>
                    <TableCell className="font-semibold text-emerald-600">{sb.present}</TableCell>
                    <TableCell className="font-semibold text-rose-600">{sb.absent ?? (sb.total - sb.present)}</TableCell>
                    <TableCell>
                      <div className="space-y-1 max-w-[200px]">
                        <div className="flex justify-between font-bold text-xs">
                          <span>{sb.percentage}%</span>
                          <span className={sb.percentage < 75 ? 'text-rose-500 font-bold' : 'text-emerald-600'}>
                            {sb.percentage < 75 ? 'LOW ATTENDANCE' : 'GOOD'}
                          </span>
                        </div>
                        <Progress value={sb.percentage} className="h-1.5" />
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Complete History Log */}
      <Card className="glass-card">
        <CardHeader className="py-3">
          <CardTitle className="text-sm font-bold flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-primary" /> Attendance Log History
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {!summary?.history?.length ? (
            <p className="text-muted-foreground text-xs text-center py-6">No historical records available.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-b border-border/50 text-xs">
                  <TableHead>Session Title</TableHead>
                  <TableHead>Subject</TableHead>
                  <TableHead>Session Date</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Marked At</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {summary.history.map((h) => (
                  <TableRow key={h.id} className="border-b border-border/40 text-xs">
                    <TableCell className="font-semibold text-foreground">{h.sessionTitle}</TableCell>
                    <TableCell>{h.subjectName}</TableCell>
                    <TableCell>{h.sessionDate ? new Date(h.sessionDate).toLocaleDateString() : 'N/A'}</TableCell>
                    <TableCell>
                      <Badge
                        variant={h.status === 'PRESENT' ? 'default' : h.status === 'LATE' ? 'secondary' : 'destructive'}
                        className={h.status === 'PRESENT' ? 'bg-emerald-600 text-xs' : 'text-xs'}
                      >
                        {h.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {h.markedAt ? new Date(h.markedAt).toLocaleString() : 'Auto-marked'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
