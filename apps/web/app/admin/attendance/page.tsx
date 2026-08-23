'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, Button, Input, Select, Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@examshield/ui';
import { Users, CheckCircle2, XCircle, Clock, Percent, Plus, RefreshCw, Download, Search, Filter, Layers, BookOpen, ShieldCheck, Loader2 } from 'lucide-react';
import { PageHeader } from '@/components/page-header';
import { useAuth } from '@clerk/nextjs';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { toast } from 'sonner';

interface Department {
  id: string;
  name: string;
}

interface Semester {
  id: string;
  name: string;
}

interface Section {
  id: string;
  name: string;
}

interface Subject {
  id: string;
  name: string;
}

interface SessionStats {
  id: string;
  title: string;
  subject_id: string;
  subject_name: string;
  department_id?: string | null;
  department_name: string;
  semester_id?: string | null;
  semester_name: string;
  section_id?: string | null;
  section_name: string;
  date: string;
  start_time: string;
  duration_minutes: number;
  status: string;
  created_at: string;
  total_students: number;
  present_count: number;
  absent_count: number;
  pending_count: number;
  attendance_percentage: number;
}

interface RosterStudent {
  id?: string | null;
  student_id: string;
  name: string;
  roll_number: string;
  batch: string;
  status: string;
  marked_at?: string | null;
}

interface SessionDetailResponse {
  session: SessionStats;
  records: RosterStudent[];
}

export default function AdminAttendancePage() {
  const api = useApiClient();
  const { isLoaded, isSignedIn } = useAuth();
  const queryClient = useQueryClient();

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);

  // Form states for Create Session
  const [deptId, setDeptId] = useState<string>('');
  const [semId, setSemId] = useState<string>('');
  const [secId, setSecId] = useState<string>('');
  const [subjectId, setSubjectId] = useState<string>('');
  const [sessionDate, setSessionDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [startTime, setStartTime] = useState<string>('09:00');
  const [duration, setDuration] = useState<number>(60);

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  // Fetch Metadata for Create Session modal
  const { data: depts } = useQuery<Department[]>({
    queryKey: ['academic', 'departments'],
    queryFn: async () => {
      try {
        const res = await api.get<any>('/academic/departments');
        return Array.isArray(res) ? res : res.items || [];
      } catch {
        return [];
      }
    },
    enabled: isLoaded && isSignedIn,
  });

  const { data: sems } = useQuery<Semester[]>({
    queryKey: ['academic', 'semesters'],
    queryFn: async () => {
      try {
        const res = await api.get<any>('/academic/semesters');
        return Array.isArray(res) ? res : res.items || [];
      } catch {
        return [];
      }
    },
    enabled: isLoaded && isSignedIn,
  });

  const { data: secs } = useQuery<Section[]>({
    queryKey: ['academic', 'sections'],
    queryFn: async () => {
      try {
        const res = await api.get<any>('/academic/sections');
        return Array.isArray(res) ? res : res.items || [];
      } catch {
        return [];
      }
    },
    enabled: isLoaded && isSignedIn,
  });

  const { data: subjects } = useQuery<Subject[]>({
    queryKey: ['questions', 'subjects'],
    queryFn: async () => {
      try {
        const res = await api.get<any>('/questions/subjects');
        return Array.isArray(res) ? res : res.items || [];
      } catch {
        return [];
      }
    },
    enabled: isLoaded && isSignedIn,
  });

  // Fetch list of attendance sessions
  const { data: sessions, isLoading: loadingSessions, refetch: refetchSessions } = useQuery<SessionStats[]>({
    queryKey: ['admin', 'attendance-sessions', isLoaded, isSignedIn],
    queryFn: () => api.get<SessionStats[]>('/attendance/sessions'),
    enabled: isLoaded && isSignedIn,
  });

  const activeSessionId = selectedSessionId || (sessions && sessions.length > 0 ? sessions[0].id : null);

  // Fetch detail for selected session
  const { data: sessionDetail, isLoading: loadingDetail, refetch: refetchDetail } = useQuery<SessionDetailResponse | null>({
    queryKey: ['admin', 'attendance-session-detail', activeSessionId],
    queryFn: () => (activeSessionId ? api.get<SessionDetailResponse>(`/attendance/sessions/${activeSessionId}`) : null),
    enabled: !!activeSessionId,
    refetchInterval: 10000,
  });

  // Create Session Mutation
  const createMutation = useMutation({
    mutationFn: async () => {
      if (!subjectId) {
        throw new Error('Please select a subject');
      }
      return api.post<SessionStats>('/attendance/sessions', {
        subject_id: subjectId,
        department_id: deptId || undefined,
        semester_id: semId || undefined,
        section_id: secId || undefined,
        date: sessionDate,
        start_time: startTime,
        duration_minutes: duration,
        status: 'ACTIVE',
      });
    },
    onSuccess: (newSess) => {
      toast.success('Attendance session created successfully');
      setCreateModalOpen(false);
      setSelectedSessionId(newSess.id);
      queryClient.invalidateQueries({ queryKey: ['admin', 'attendance-sessions'] });
    },
    onError: (err: any) => {
      toast.error(err?.message || 'Failed to create attendance session');
    },
  });

  // End Session Mutation
  const endSessionMutation = useMutation({
    mutationFn: async (id: string) => {
      return api.post(`/attendance/sessions/${id}/close`, {});
    },
    onSuccess: () => {
      toast.success('Attendance session closed. Unsubmitted students auto-marked ABSENT.');
      queryClient.invalidateQueries({ queryKey: ['admin', 'attendance-sessions'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'attendance-session-detail'] });
    },
    onError: (err: any) => {
      toast.error(err?.message || 'Failed to close session');
    },
  });

  // CSV Export handler
  const handleExportCSV = async () => {
    if (!activeSessionId) return;
    try {
      const fullUrl = `${process.env.NEXT_PUBLIC_API_URL || 'https://gate-ds9h.onrender.com'}/api/v1/attendance/sessions/${activeSessionId}/export`;
      window.open(fullUrl, '_blank');
      toast.success('Exporting attendance CSV...');
    } catch {
      toast.error('Failed to export CSV');
    }
  };

  const currentStats = sessionDetail?.session || (sessions && sessions.length > 0 ? sessions[0] : null);
  const currentRoster = sessionDetail?.records || [];

  const filteredRoster = currentRoster.filter((st) => {
    const matchesSearch =
      st.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      st.roll_number.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === 'ALL' ? true : st.status.toUpperCase() === statusFilter.toUpperCase();
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Admin Attendance Portal"
        description="Create real-time attendance check-in sessions, view student rosters, monitor present/absent counts, and export attendance records."
        action={
          <Button
            size="sm"
            onClick={() => setCreateModalOpen(true)}
            className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs cursor-pointer shadow-lg transition-all duration-150"
          >
            <Plus className="h-4 w-4 mr-1.5" /> Create Session
          </Button>
        }
      />

      {/* Sessions Overview Cards & Selection */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card className="glass-card md:col-span-1">
          <CardContent className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-foreground">Select Session</span>
              <Button
                size="sm"
                variant="ghost"
                className="h-7 px-2 text-xs"
                onClick={() => {
                  refetchSessions();
                  refetchDetail();
                  toast.success('Attendance data refreshed');
                }}
              >
                <RefreshCw className="h-3.5 w-3.5" />
              </Button>
            </div>
            {loadingSessions ? (
              <div className="p-4 text-center text-xs text-muted-foreground">Loading sessions...</div>
            ) : !sessions?.length ? (
              <div className="p-4 text-center space-y-2">
                <p className="text-xs text-muted-foreground">No sessions created yet.</p>
                <Button size="sm" onClick={() => setCreateModalOpen(true)} className="w-full text-xs">
                  Create First Session
                </Button>
              </div>
            ) : (
              <div className="space-y-1.5 max-h-[220px] overflow-y-auto pr-1">
                {sessions.map((sess) => (
                  <button
                    key={sess.id}
                    onClick={() => setSelectedSessionId(sess.id)}
                    className={`w-full text-left p-2.5 rounded-xl border text-xs transition-all ${
                      (selectedSessionId || sessions[0].id) === sess.id
                        ? 'border-primary bg-primary/10 font-bold text-foreground'
                        : 'border-border/40 hover:bg-white/10 dark:hover:bg-slate-800/40 text-muted-foreground'
                    }`}
                  >
                    <div className="truncate font-semibold text-foreground">{sess.subject_name}</div>
                    <div className="text-[10px] text-muted-foreground flex justify-between mt-0.5">
                      <span>{sess.date}</span>
                      <span className={sess.status === 'ACTIVE' ? 'text-emerald-500 font-bold' : ''}>
                        {sess.status}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Live Attendance Stat Counters */}
        <div className="md:col-span-4 grid gap-4 sm:grid-cols-4">
          <Card className="glass-card">
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[11px] font-semibold text-muted-foreground uppercase">Total Students</p>
                  <p className="text-2xl font-extrabold mt-1 text-foreground">{currentStats?.total_students ?? 0}</p>
                </div>
                <div className="p-2.5 bg-blue-500/10 rounded-xl text-blue-500">
                  <Users className="h-5 w-5" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="glass-card">
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 uppercase">Present</p>
                  <p className="text-2xl font-extrabold mt-1 text-emerald-600 dark:text-emerald-400">{currentStats?.present_count ?? 0}</p>
                </div>
                <div className="p-2.5 bg-emerald-500/10 rounded-xl text-emerald-500">
                  <CheckCircle2 className="h-5 w-5" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="glass-card">
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[11px] font-semibold text-rose-600 dark:text-rose-400 uppercase">Absent</p>
                  <p className="text-2xl font-extrabold mt-1 text-rose-600 dark:text-rose-400">{currentStats?.absent_count ?? 0}</p>
                </div>
                <div className="p-2.5 bg-rose-500/10 rounded-xl text-rose-500">
                  <XCircle className="h-5 w-5" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="glass-card">
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[11px] font-semibold text-amber-500 uppercase">Attendance %</p>
                  <p className="text-2xl font-extrabold mt-1 text-amber-500">{currentStats?.attendance_percentage ?? 0}%</p>
                </div>
                <div className="p-2.5 bg-amber-500/10 rounded-xl text-amber-500">
                  <Percent className="h-5 w-5" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Roster & Controls Section */}
      <Card className="glass-card">
        <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3">
          <CardTitle className="text-base font-bold flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-primary" /> Session Roster & Attendance Statuses
          </CardTitle>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                refetchDetail();
                toast.success('Roster refreshed');
              }}
              className="glass-button text-xs"
            >
              <RefreshCw className="h-3.5 w-3.5 mr-1" /> Refresh
            </Button>

            {currentStats?.status === 'ACTIVE' && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => endSessionMutation.mutate(currentStats.id)}
                disabled={endSessionMutation.isPending}
                className="border-rose-500/30 text-rose-400 hover:bg-rose-950/20 text-xs"
              >
                End Session
              </Button>
            )}

            <Button
              size="sm"
              variant="outline"
              onClick={handleExportCSV}
              className="glass-button text-xs"
            >
              <Download className="h-3.5 w-3.5 mr-1" /> Export CSV
            </Button>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Search & Status Filters */}
          <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
            <div className="relative w-full sm:w-72">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search student or roll number..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 text-xs glass-input"
              />
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <span className="text-xs text-muted-foreground font-semibold">Filter:</span>
              {['ALL', 'PRESENT', 'ABSENT', 'PENDING'].map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-3 py-1 rounded-full text-[11px] font-bold transition-all ${
                    statusFilter === st
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'bg-muted/40 hover:bg-muted text-muted-foreground'
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>
          </div>

          {/* Roster Table */}
          {loadingDetail ? (
            <div className="p-8 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-primary" /> Loading student roster...
            </div>
          ) : !filteredRoster.length ? (
            <div className="p-8 text-center text-xs text-muted-foreground">
              No student attendance records match current filters.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-border/60 text-muted-foreground font-semibold">
                    <th className="p-2.5">Roll Number</th>
                    <th className="p-2.5">Student Name</th>
                    <th className="p-2.5">Batch</th>
                    <th className="p-2.5">Status</th>
                    <th className="p-2.5">Marked At</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30">
                  {filteredRoster.map((st) => (
                    <tr key={st.student_id} className="hover:bg-white/20 dark:hover:bg-slate-800/20">
                      <td className="p-2.5 font-mono text-muted-foreground">{st.roll_number}</td>
                      <td className="p-2.5 font-bold text-foreground">{st.name}</td>
                      <td className="p-2.5 text-muted-foreground">{st.batch}</td>
                      <td className="p-2.5">
                        {st.status === 'PRESENT' || st.status === 'LATE' ? (
                          <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-bold text-[10px]">PRESENT</span>
                        ) : st.status === 'ABSENT' ? (
                          <span className="px-2.5 py-0.5 rounded-full bg-rose-500/20 text-rose-400 font-bold text-[10px]">ABSENT</span>
                        ) : (
                          <span className="px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-400 font-bold text-[10px]">PENDING</span>
                        )}
                      </td>
                      <td className="p-2.5 text-muted-foreground font-mono text-[11px]">
                        {st.marked_at ? new Date(st.marked_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Attendance Session Modal */}
      <Dialog open={createModalOpen} onOpenChange={setCreateModalOpen}>
        <DialogContent className="sm:max-w-md bg-slate-900 border-slate-800 text-white space-y-4">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold flex items-center gap-2">
              <Plus className="h-5 w-5 text-emerald-500" /> Create Attendance Session
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-3 text-xs">
            <div>
              <label className="block text-slate-300 font-semibold mb-1">Subject *</label>
              <select
                value={subjectId}
                onChange={(e) => setSubjectId(e.target.value)}
                className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-white text-xs"
              >
                <option value="">Select Subject...</option>
                {subjects?.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Department</label>
                <select
                  value={deptId}
                  onChange={(e) => setDeptId(e.target.value)}
                  className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-white text-xs"
                >
                  <option value="">All Depts</option>
                  {depts?.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Semester</label>
                <select
                  value={semId}
                  onChange={(e) => setSemId(e.target.value)}
                  className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-white text-xs"
                >
                  <option value="">All Semesters</option>
                  {sems?.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Section</label>
                <select
                  value={secId}
                  onChange={(e) => setSecId(e.target.value)}
                  className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-white text-xs"
                >
                  <option value="">All Sections</option>
                  {secs?.map((sc) => (
                    <option key={sc.id} value={sc.id}>
                      {sc.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Date</label>
                <Input
                  type="date"
                  value={sessionDate}
                  onChange={(e) => setSessionDate(e.target.value)}
                  className="bg-slate-950 border-slate-800 text-white text-xs"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Start Time</label>
                <Input
                  type="text"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  placeholder="09:00"
                  className="bg-slate-950 border-slate-800 text-white text-xs"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Duration (m)</label>
                <Input
                  type="number"
                  value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))}
                  className="bg-slate-950 border-slate-800 text-white text-xs"
                />
              </div>
            </div>
          </div>

          <DialogFooter className="gap-2 pt-2">
            <Button
              variant="outline"
              onClick={() => setCreateModalOpen(false)}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending || !subjectId}
              className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs"
            >
              {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
              Create Session
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
