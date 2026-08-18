'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import {
  Card, CardContent, CardHeader, CardTitle, Button, Badge, Input, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Label, Textarea,
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from '@examshield/ui';
import {
  Users, CheckCircle2, XCircle, AlertTriangle, QrCode, Plus, Search, Download, RefreshCw, Loader2, Play, Lock, Eye, Edit, Clock, ShieldCheck, Percent, FileSpreadsheet
} from 'lucide-react';
import { toast } from 'sonner';
import type { Paginated } from '@examshield/types';

interface SummaryData {
  overallPercentage: number;
  totalStudents: number;
  totalPresentCount: number;
  totalAbsentCount: number;
  lowAttendanceCount: number;
  lowThreshold: number;
  lowAttendanceStudents: {
    studentId: string;
    rollNumber: string;
    name: string;
    department: string;
    totalSessions: number;
    presentSessions: number;
    absentSessions: number;
    percentage: number;
  }[];
  recentSessions: any[];
}

interface AttendanceRecordRow {
  id: string;
  studentId: string;
  studentRoll: string;
  studentName: string;
  departmentName: string;
  subjectName: string;
  sessionDate: string;
  status: 'PRESENT' | 'ABSENT' | 'LATE';
  verificationMethod: string;
  markedAt: string;
  notes?: string;
}

export default function AdminAttendancePage() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [subjectFilter, setSubjectFilter] = useState('');
  const [deptFilter, setDeptFilter] = useState('');
  const [dateFilter, setDateFilter] = useState('');

  // Dialog States
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [activeQrSession, setActiveQrSession] = useState<any | null>(null);
  const [qrTokenData, setQrTokenData] = useState<{ token: string; expiresInSeconds: number } | null>(null);
  const [editingRecord, setEditingRecord] = useState<AttendanceRecordRow | null>(null);
  const [editStatus, setEditStatus] = useState<'PRESENT' | 'ABSENT' | 'LATE'>('PRESENT');
  const [editNotes, setEditNotes] = useState('');

  // Create Form State
  const [title, setTitle] = useState('');
  const [subjectId, setSubjectId] = useState('');
  const [departmentId, setDepartmentId] = useState('');
  const [semesterId, setSemesterId] = useState('');
  const [sectionId, setSectionId] = useState('');
  const [sessionDate, setSessionDate] = useState(new Date().toISOString().split('T')[0]);
  const [startTime, setStartTime] = useState(new Date().toISOString().substring(0, 16));
  const [endTime, setEndTime] = useState(new Date(Date.now() + 3600000).toISOString().substring(0, 16));
  const [durationMinutes, setDurationMinutes] = useState(60);

  // Queries
  const summaryParams: Record<string, unknown> = {};
  if (deptFilter && deptFilter !== 'all') summaryParams.department_id = deptFilter;
  if (dateFilter) summaryParams.date = dateFilter;

  const { data: summary, isLoading: loadingSummary, refetch: refetchSummary } = useQuery<SummaryData>({
    queryKey: ['attendance-summary', summaryParams],
    queryFn: () => api.get<SummaryData>('/attendance/summary', summaryParams),
  });

  const { data: subjects = [] } = useQuery<{ id: string; name: string; code: string }[]>({
    queryKey: ['subjects'],
    queryFn: () => api.get<{ id: string; name: string; code: string }[]>('/question-bank/subjects'),
  });

  const { data: departments = [] } = useQuery<{ id: string; name: string }[]>({
    queryKey: ['departments'],
    queryFn: () => api.get<{ id: string; name: string }[]>('/academic/departments'),
  });

  const recordParams: Record<string, unknown> = { page, page_size: 20 };
  if (search) recordParams.search = search;
  if (statusFilter && statusFilter !== 'all') recordParams.status_filter = statusFilter;
  if (subjectFilter && subjectFilter !== 'all') recordParams.subject_id = subjectFilter;
  if (deptFilter && deptFilter !== 'all') recordParams.department_id = deptFilter;
  if (dateFilter) recordParams.date = dateFilter;

  const { data: recordsData, isLoading: loadingRecords, refetch: refetchRecords } = useQuery({
    queryKey: ['attendance-records', recordParams],
    queryFn: () => api.get<Paginated<any>>('/attendance/records', recordParams),
  });

  const sessionParams: Record<string, unknown> = { page_size: 50 };
  if (deptFilter && deptFilter !== 'all') sessionParams.department_id = deptFilter;
  if (subjectFilter && subjectFilter !== 'all') sessionParams.subject_id = subjectFilter;
  if (dateFilter) sessionParams.date = dateFilter;

  const { data: sessionsData, refetch: refetchSessions } = useQuery({
    queryKey: ['attendance-sessions-list', sessionParams],
    queryFn: () => api.get<Paginated<any>>('/attendance/sessions', sessionParams),
  });

  // Auto-refresh active QR token countdown
  useEffect(() => {
    if (!activeQrSession) return;
    const fetchQr = async () => {
      try {
        const data = await api.get<any>(`/attendance/qr/${activeQrSession.id}`);
        setQrTokenData(data);
      } catch {
        // Fallback
      }
    };
    fetchQr();
    const timer = setInterval(fetchQr, 5000);
    return () => clearInterval(timer);
  }, [activeQrSession, api]);

  // Mutations
  const createMutation = useMutation({
    mutationFn: (payload: any) => api.post('/attendance/sessions', payload),
    onSuccess: () => {
      toast.success('Attendance session created!');
      setIsCreateOpen(false);
      setTitle('');
      setSubjectId('');
      setDepartmentId('');
      setSemesterId('');
      setSectionId('');
      refetchSessions();
      refetchSummary();
      queryClient.invalidateQueries({ queryKey: ['attendance-summary'] });
      queryClient.invalidateQueries({ queryKey: ['attendance-sessions-list'] });
    },
    onError: (e: Error) => toast.error(e.message || 'Failed to create session'),
  });

  const activateMutation = useMutation({
    mutationFn: (id: string) => api.post(`/attendance/sessions/${id}/activate`),
    onSuccess: (res: any) => {
      toast.success('Session activated! Displaying dynamic QR.');
      setActiveQrSession(res);
      refetchSessions();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const closeMutation = useMutation({
    mutationFn: (id: string) => api.post(`/attendance/sessions/${id}/close`),
    onSuccess: (res: any) => {
      toast.success(`Session closed! Auto-marked ${res.autoAbsentCount || 0} unrecorded student(s) as ABSENT.`);
      setActiveQrSession(null);
      refetchSummary();
      refetchRecords();
      refetchSessions();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const editMutation = useMutation({
    mutationFn: ({ id, status, notes }: { id: string; status: string; notes?: string }) =>
      api.patch(`/attendance/records/${id}`, { status, notes }),
    onSuccess: () => {
      toast.success('Attendance status updated with audit log entry');
      setEditingRecord(null);
      refetchRecords();
      refetchSummary();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const handleExportCsv = async () => {
    try {
      toast.info('Downloading attendance CSV report...');
      const params = new URLSearchParams();
      if (dateFilter) params.append('date', dateFilter);
      if (deptFilter && deptFilter !== 'all') params.append('department_id', deptFilter);
      if (subjectFilter && subjectFilter !== 'all') params.append('subject_id', subjectFilter);
      if (statusFilter && statusFilter !== 'all') params.append('status_filter', statusFilter);
      const url = `/api/v1/attendance/export?${params.toString()}`;
      window.open(url, '_blank');
    } catch {
      toast.error('Failed to export report');
    }
  };

  const records = recordsData?.items || [];
  const sessions = sessionsData?.items || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Attendance Management Dashboard"
        description="Create live class sessions, generate dynamic QR codes, track real-time scans, auto-mark absent students, and view low-attendance analytics."
      >
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleExportCsv} className="glass-button cursor-pointer">
            <Download className="h-4 w-4 mr-1.5" /> Export CSV
          </Button>
          <Button size="sm" onClick={() => setIsCreateOpen(true)} className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-md border border-primary/30 cursor-pointer text-xs font-semibold">
            <Plus className="h-4 w-4 mr-1.5" /> Create Session
          </Button>
        </div>
      </PageHeader>

      {/* Overview Stat Cards */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground font-semibold uppercase">Total Students</p>
              <p className="text-2xl font-extrabold mt-1 text-foreground">{summary?.totalStudents ?? 0}</p>
            </div>
            <div className="p-2.5 bg-primary/10 rounded-xl text-primary"><Users className="h-5 w-5" /></div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground font-semibold uppercase">Total Present</p>
              <p className="text-2xl font-extrabold mt-1 text-emerald-600">{summary?.totalPresentCount ?? 0}</p>
            </div>
            <div className="p-2.5 bg-emerald-500/10 rounded-xl text-emerald-600"><CheckCircle2 className="h-5 w-5" /></div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground font-semibold uppercase">Total Absent</p>
              <p className="text-2xl font-extrabold mt-1 text-rose-600">{summary?.totalAbsentCount ?? 0}</p>
            </div>
            <div className="p-2.5 bg-rose-500/10 rounded-xl text-rose-600"><XCircle className="h-5 w-5" /></div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground font-semibold uppercase">Overall Attendance</p>
              <p className="text-2xl font-extrabold mt-1 text-amber-500">{summary?.overallPercentage ?? 100}%</p>
            </div>
            <div className="p-2.5 bg-amber-500/10 rounded-xl text-amber-500"><Percent className="h-5 w-5" /></div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground font-semibold uppercase">Below {summary?.lowThreshold ?? 75}%</p>
              <p className="text-2xl font-extrabold mt-1 text-rose-500">{summary?.lowAttendanceCount ?? 0}</p>
            </div>
            <div className="p-2.5 bg-rose-500/10 rounded-xl text-rose-500"><AlertTriangle className="h-5 w-5" /></div>
          </CardContent>
        </Card>
      </div>

      {/* Active & Recent Sessions Header Section */}
      <Card className="glass-card">
        <CardHeader className="flex flex-row items-center justify-between py-3">
          <CardTitle className="text-sm font-bold flex items-center gap-2">
            <Clock className="h-4 w-4 text-primary" /> Attendance Sessions Overview
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="ghost" onClick={() => refetchSessions()} className="h-7 text-xs cursor-pointer">
              <RefreshCw className="h-3.5 w-3.5 mr-1" /> Refresh
            </Button>
            <Button size="sm" onClick={() => setIsCreateOpen(true)} className="h-7 text-xs bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm border border-primary/30 cursor-pointer font-semibold">
              <Plus className="h-3.5 w-3.5 mr-1" /> Create Session
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 text-xs pt-0">
          {!sessions.length ? (
            <div className="p-6 text-center space-y-3 bg-muted/10 rounded-xl border border-dashed border-border/60 flex flex-col items-center justify-center">
              <p className="text-muted-foreground text-xs font-medium">No attendance sessions created yet.</p>
              <Button
                size="sm"
                onClick={() => setIsCreateOpen(true)}
                className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-md border border-primary/30 cursor-pointer text-xs font-semibold px-4 py-2 transition-all flex items-center justify-center"
              >
                <Plus className="h-3.5 w-3.5 mr-1.5" /> Create First Session
              </Button>
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {sessions.map((s) => {
                const sSubject = s.subject?.name || 'General Subject';
                const sBatch = [s.department?.name, s.semester?.name, s.section?.name].filter(Boolean).join(' - ') || 'All Batches';
                const startFmt = s.startTime ? new Date(s.startTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
                const endFmt = s.endTime ? new Date(s.endTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
                return (
                  <div key={s.id} className="p-3.5 rounded-xl border border-border/40 bg-muted/20 space-y-2 flex flex-col justify-between shadow-xs">
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-foreground text-xs truncate max-w-[170px]">{s.title}</span>
                        <Badge variant={s.status === 'ACTIVE' ? 'default' : s.status === 'CLOSED' ? 'secondary' : 'outline'} className="text-[10px]">
                          {s.status}
                        </Badge>
                      </div>
                      <p className="text-[11px] text-muted-foreground font-medium">
                        {sSubject} | <span className="text-foreground/80">{sBatch}</span>
                      </p>
                      {startFmt && (
                        <p className="text-[10px] text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3 text-amber-500" /> {startFmt} {endFmt ? `– ${endFmt}` : ''}
                        </p>
                      )}
                      <div className="grid grid-cols-3 gap-1 pt-1.5 text-[10px] text-center border-t border-border/20">
                        <div className="bg-emerald-500/10 p-1 rounded font-bold text-emerald-600">
                          Present: {s.presentCount ?? 0}
                        </div>
                        <div className="bg-rose-500/10 p-1 rounded font-bold text-rose-600">
                          Absent: {s.absentCount ?? 0}
                        </div>
                        <div className="bg-amber-500/10 p-1 rounded font-bold text-amber-500">
                          {s.percentage ?? 100}%
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 pt-2 border-t border-border/30">
                      {s.status === 'DRAFT' && (
                        <Button size="sm" variant="outline" className="h-7 text-xs w-full glass-button" onClick={() => activateMutation.mutate(s.id)}>
                          <Play className="h-3 w-3 mr-1 text-emerald-600" /> Activate & Display QR
                        </Button>
                      )}
                      {s.status === 'ACTIVE' && (
                        <>
                          <Button size="sm" className="h-7 text-xs flex-1 glass-button bg-primary text-white" onClick={() => setActiveQrSession(s)}>
                            <QrCode className="h-3 w-3 mr-1" /> Display QR
                          </Button>
                          <Button size="sm" variant="destructive" className="h-7 text-xs flex-1" onClick={() => closeMutation.mutate(s.id)}>
                            <Lock className="h-3 w-3 mr-1" /> End Session
                          </Button>
                        </>
                      )}
                      {s.status === 'CLOSED' && (
                        <Badge variant="outline" className="w-full justify-center text-[10px] py-1 bg-muted/40 text-muted-foreground font-semibold">
                          Session Ended (Auto-Absent Complete)
                        </Badge>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Main Attendance Records Table */}
      <Card className="glass-card">
        <CardHeader className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 py-4">
          <CardTitle className="text-sm font-bold flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-600" /> Student Attendance Records Directory
          </CardTitle>

          {/* Toolbar */}
          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-48">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search roll number or name..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                className="pl-8 h-8 glass-input text-xs"
              />
            </div>
            <Input
              type="date"
              value={dateFilter}
              onChange={(e) => { setDateFilter(e.target.value); setPage(1); }}
              className="h-8 w-36 glass-input text-xs"
            />
            <Select value={deptFilter} onValueChange={(v) => { setDeptFilter(v); setPage(1); }}>
              <SelectTrigger className="h-8 w-32 glass-input text-xs"><SelectValue placeholder="Batch / Dept" /></SelectTrigger>
              <SelectContent className="glass-modal">
                <SelectItem value="all">All Batches</SelectItem>
                {departments.map((d) => <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1); }}>
              <SelectTrigger className="h-8 w-28 glass-input text-xs"><SelectValue placeholder="Status" /></SelectTrigger>
              <SelectContent className="glass-modal">
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="PRESENT">PRESENT</SelectItem>
                <SelectItem value="ABSENT">ABSENT</SelectItem>
                <SelectItem value="LATE">LATE</SelectItem>
              </SelectContent>
            </Select>
            <Select value={subjectFilter} onValueChange={(v) => { setSubjectFilter(v); setPage(1); }}>
              <SelectTrigger className="h-8 w-32 glass-input text-xs"><SelectValue placeholder="Subject" /></SelectTrigger>
              <SelectContent className="glass-modal">
                <SelectItem value="all">All Subjects</SelectItem>
                {subjects.map((s) => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loadingRecords ? (
            <div className="p-8 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-primary" /> Loading attendance records...
            </div>
          ) : !records.length ? (
            <div className="p-8 text-center text-xs text-muted-foreground">
              No attendance records match your search or filter parameters.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-b border-border/50 text-xs">
                  <TableHead>Roll Number</TableHead>
                  <TableHead>Student Name</TableHead>
                  <TableHead>Batch / Cohort</TableHead>
                  <TableHead>Subject / Session</TableHead>
                  <TableHead>Session Date</TableHead>
                  <TableHead>Verification</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {records.map((r: any) => (
                  <TableRow key={r.id} className="border-b border-border/40 text-xs hover:bg-muted/30">
                    <TableCell className="font-mono font-bold">{r.studentRoll}</TableCell>
                    <TableCell className="font-semibold text-foreground">{r.studentName}</TableCell>
                    <TableCell><Badge variant="outline" className="text-[10px] font-mono">{r.batch || r.departmentName}</Badge></TableCell>
                    <TableCell className="max-w-[160px] truncate">{r.subjectName}</TableCell>
                    <TableCell>{r.sessionDate ? new Date(r.sessionDate).toLocaleDateString() : 'N/A'}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-[10px] font-mono uppercase">
                        {r.verificationMethod}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={r.status === 'PRESENT' ? 'default' : r.status === 'LATE' ? 'secondary' : 'destructive'}
                        className={r.status === 'PRESENT' ? 'bg-emerald-600 text-xs' : 'text-xs'}
                      >
                        {r.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 px-2 text-xs"
                        onClick={() => {
                          setEditingRecord(r);
                          setEditStatus(r.status);
                          setEditNotes(r.notes || '');
                        }}
                      >
                        <Edit className="h-3.5 w-3.5 mr-1" /> Override
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Low Attendance Warning Panel */}
      {summary?.lowAttendanceStudents && summary.lowAttendanceStudents.length > 0 && (
        <Card className="glass-card border-rose-500/30">
          <CardHeader className="py-3">
            <CardTitle className="text-sm font-bold text-rose-600 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-rose-500" /> Low Attendance Alert (&lt; 75%)
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="border-b border-border/50 text-xs">
                  <TableHead>Roll Number</TableHead>
                  <TableHead>Student Name</TableHead>
                  <TableHead>Department</TableHead>
                  <TableHead>Present / Total</TableHead>
                  <TableHead>Attendance Percentage</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {summary.lowAttendanceStudents.map((st) => (
                  <TableRow key={st.studentId} className="border-b border-border/30 text-xs bg-rose-50/20 dark:bg-rose-950/20">
                    <TableCell className="font-mono font-bold text-rose-600">{st.rollNumber}</TableCell>
                    <TableCell className="font-semibold text-foreground">{st.name}</TableCell>
                    <TableCell>{st.department}</TableCell>
                    <TableCell>{st.presentSessions} / {st.totalSessions}</TableCell>
                    <TableCell className="font-bold text-rose-600">{st.percentage}%</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Create Session Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="glass-modal max-w-md">
          <DialogHeader>
            <DialogTitle>Create Attendance Session</DialogTitle>
            <DialogDescription>Setup a new class or lecture session for live student QR attendance tracking.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 text-xs">
            <div className="space-y-1">
              <Label>Session Title *</Label>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Operating Systems Lecture 12"
                className="glass-input"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>Subject</Label>
                <Select value={subjectId} onValueChange={setSubjectId}>
                  <SelectTrigger className="glass-input text-xs"><SelectValue placeholder="Select Subject" /></SelectTrigger>
                  <SelectContent className="glass-modal">
                    {subjects.map((s) => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1">
                <Label>Department</Label>
                <Select value={departmentId} onValueChange={setDepartmentId}>
                  <SelectTrigger className="glass-input text-xs"><SelectValue placeholder="All Depts" /></SelectTrigger>
                  <SelectContent className="glass-modal">
                    {departments.map((d) => <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1">
                <Label>Date *</Label>
                <Input type="date" value={sessionDate} onChange={(e) => setSessionDate(e.target.value)} className="glass-input text-xs" />
              </div>
              <div className="space-y-1">
                <Label>Start Time *</Label>
                <Input type="datetime-local" value={startTime} onChange={(e) => setStartTime(e.target.value)} className="glass-input text-xs" />
              </div>
              <div className="space-y-1">
                <Label>End Time *</Label>
                <Input type="datetime-local" value={endTime} onChange={(e) => setEndTime(e.target.value)} className="glass-input text-xs" />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>Cancel</Button>
            <Button
              type="button"
              className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-md border border-primary/30 cursor-pointer text-xs font-semibold"
              disabled={createMutation.isPending}
              onClick={() => {
                let duration = 60;
                if (startTime && endTime) {
                  const diff = Math.max(15, Math.floor((new Date(endTime).getTime() - new Date(startTime).getTime()) / 60000));
                  if (!isNaN(diff) && diff > 0) duration = diff;
                }
                createMutation.mutate({
                  title: title.trim() || 'Class Attendance Session',
                  subjectId: subjectId || undefined,
                  departmentId: departmentId || undefined,
                  semesterId: semesterId || undefined,
                  sectionId: sectionId || undefined,
                  sessionDate,
                  startTime,
                  durationMinutes: duration,
                });
              }}
            >
              {createMutation.isPending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
              Create Session
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dynamic Live QR Modal */}
      {activeQrSession && (
        <Dialog open={!!activeQrSession} onOpenChange={(open) => { if (!open) setActiveQrSession(null); }}>
          <DialogContent className="glass-modal max-w-md text-center space-y-4">
            <DialogHeader>
              <DialogTitle className="flex items-center justify-center gap-2">
                <QrCode className="h-5 w-5 text-primary" /> Live Dynamic Attendance QR Code
              </DialogTitle>
              <DialogDescription>{activeQrSession.title}</DialogDescription>
            </DialogHeader>

            <div className="p-6 bg-white rounded-2xl border shadow-inner space-y-3 flex flex-col items-center justify-center">
              {/* Dynamic Simulated QR Presentation */}
              <div className="w-52 h-52 bg-slate-900 rounded-xl p-4 flex flex-col items-center justify-center text-white space-y-2 relative overflow-hidden">
                <QrCode className="w-28 h-28 text-white animate-pulse" />
                <span className="font-mono text-xs text-amber-400 font-bold tracking-widest">
                  TOKEN: {qrTokenData?.token || 'GENERATING...'}
                </span>
                <span className="text-[10px] text-slate-400">Rotates every 30s</span>
              </div>

              <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
                <Clock className="h-4 w-4 text-amber-500 animate-spin" /> Token Expires In:{' '}
                <span className="font-bold text-foreground font-mono">{qrTokenData?.expiresInSeconds ?? 30}s</span>
              </div>
            </div>

            <p className="text-xs text-muted-foreground">
              Students scan this dynamic QR code using the GATE IGNITE student portal to mark attendance automatically.
            </p>

            <DialogFooter className="sm:justify-between gap-2">
              <Button variant="outline" onClick={() => setActiveQrSession(null)}>Hide Modal</Button>
              <Button
                variant="destructive"
                onClick={() => closeMutation.mutate(activeQrSession.id)}
                disabled={closeMutation.isPending}
              >
                {closeMutation.isPending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Lock className="h-4 w-4 mr-2" />}
                Close Session & Auto-Absent
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Edit Record Override Dialog */}
      {editingRecord && (
        <Dialog open={!!editingRecord} onOpenChange={(open) => { if (!open) setEditingRecord(null); }}>
          <DialogContent className="glass-modal max-w-sm">
            <DialogHeader>
              <DialogTitle>Override Attendance Status</DialogTitle>
              <DialogDescription>{editingRecord.studentName} ({editingRecord.studentRoll})</DialogDescription>
            </DialogHeader>

            <div className="space-y-3 text-xs">
              <div className="space-y-1">
                <Label>Attendance Status</Label>
                <Select value={editStatus} onValueChange={(v: any) => setEditStatus(v)}>
                  <SelectTrigger className="glass-input"><SelectValue /></SelectTrigger>
                  <SelectContent className="glass-modal">
                    <SelectItem value="PRESENT">PRESENT</SelectItem>
                    <SelectItem value="ABSENT">ABSENT</SelectItem>
                    <SelectItem value="LATE">LATE</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1">
                <Label>Audit Note / Rationale</Label>
                <Textarea
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  placeholder="e.g. Medical leave approved by HOD"
                  rows={2}
                  className="glass-input"
                />
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setEditingRecord(null)}>Cancel</Button>
              <Button
                className="glass-button bg-primary text-white"
                disabled={editMutation.isPending}
                onClick={() => editMutation.mutate({ id: editingRecord.id, status: editStatus, notes: editNotes })}
              >
                {editMutation.isPending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                Save Override
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
