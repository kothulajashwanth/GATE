'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge } from '@examshield/ui';
import { ShieldCheck, CheckCircle2, XCircle, Clock, Calendar, Award, BookOpen, Loader2 } from 'lucide-react';
import { PageHeader } from '@/components/page-header';
import { useAuth } from '@clerk/nextjs';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { toast } from 'sonner';

interface ActiveSession {
  id: string;
  title: string;
  subject_id: string;
  subject_name: string;
  date: string;
  start_time: string;
  duration_minutes: number;
  status: string;
  already_submitted: boolean;
  submitted_status?: string | null;
}

interface SubjectStat {
  subject_id: string;
  subject_name: string;
  total_sessions: number;
  present_count: number;
  absent_count: number;
  percentage: number;
}

interface AttendanceHistoryRecord {
  id: string;
  session_id: string;
  subject_name: string;
  date: string;
  status: string;
  marked_at: string;
}

interface AttendanceHistoryResponse {
  total_sessions: number;
  present_count: number;
  absent_count: number;
  overall_percentage: number;
  subject_stats: SubjectStat[];
  records: AttendanceHistoryRecord[];
}

export default function StudentAttendancePage() {
  const api = useApiClient();
  const { isLoaded, isSignedIn } = useAuth();
  const queryClient = useQueryClient();
  const [submittingStatus, setSubmittingStatus] = useState<'PRESENT' | 'ABSENT' | null>(null);

  const { data: activeSession, isLoading: loadingActive } = useQuery<ActiveSession | null>({
    queryKey: ['student', 'active-attendance', isLoaded, isSignedIn],
    queryFn: async () => {
      try {
        const res = await api.get<ActiveSession | null>('/attendance/student/active');
        return res;
      } catch {
        return null;
      }
    },
    enabled: isLoaded && isSignedIn,
    refetchInterval: 10000,
  });

  const { data: historyData, isLoading: loadingHistory } = useQuery<AttendanceHistoryResponse>({
    queryKey: ['student', 'attendance-history', isLoaded, isSignedIn],
    queryFn: () => api.get<AttendanceHistoryResponse>('/attendance/student/records'),
    enabled: isLoaded && isSignedIn,
  });

  const submitMutation = useMutation({
    mutationFn: async (statusVal: 'PRESENT' | 'ABSENT') => {
      if (!activeSession) return;
      setSubmittingStatus(statusVal);
      return api.post('/attendance/student/submit', {
        session_id: activeSession.id,
        status: statusVal,
      });
    },
    onSuccess: () => {
      toast.success('Attendance marked successfully.');
      queryClient.invalidateQueries({ queryKey: ['student', 'active-attendance'] });
      queryClient.invalidateQueries({ queryKey: ['student', 'attendance-history'] });
    },
    onError: (err: any) => {
      toast.error(err?.message || 'Failed to submit attendance');
    },
    onSettled: () => {
      setSubmittingStatus(null);
    },
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Student Attendance Portal"
        description="View real-time active attendance sessions, submit your check-in, and track overall and subject-wise attendance history."
      />

      {/* Active Attendance Check-In Section */}
      {loadingActive ? (
        <Card className="glass-card">
          <CardContent className="p-6 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-primary" /> Checking for active attendance sessions...
          </CardContent>
        </Card>
      ) : activeSession ? (
        <Card className="glass-card border-2 border-emerald-500/40 bg-gradient-to-r from-emerald-950/40 via-slate-900/90 to-teal-950/40 p-6 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10 text-emerald-400">
            <ShieldCheck className="h-40 w-40" />
          </div>
          <CardContent className="p-0 relative z-10 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-4">
              <div>
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 font-extrabold text-[10px] uppercase tracking-wider mb-2">
                  <ShieldCheck className="h-3.5 w-3.5" /> ACTIVE ATTENDANCE SESSION
                </span>
                <h2 className="text-2xl font-extrabold text-white tracking-tight">
                  {activeSession.subject_name}
                </h2>
                <p className="text-xs text-slate-300 mt-1">
                  Session: <span className="font-semibold text-white">{activeSession.title}</span> · Date: {activeSession.date} · Time: {activeSession.start_time} ({activeSession.duration_minutes} mins)
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/30 text-xs px-3 py-1 font-bold">
                  Status: ACTIVE
                </Badge>
              </div>
            </div>

            {activeSession.already_submitted ? (
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-center space-y-1">
                <p className="text-sm font-bold text-emerald-400 flex items-center justify-center gap-2">
                  <CheckCircle2 className="h-4 w-4" /> Attendance already submitted.
                </p>
                <p className="text-xs text-slate-400">
                  Your response (<span className="font-bold text-white uppercase">{activeSession.submitted_status}</span>) has been saved in the database.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-xs text-slate-300 font-medium">
                  Select your attendance status for this session:
                </p>
                <div className="flex flex-wrap gap-3">
                  <Button
                    size="lg"
                    disabled={submitMutation.isPending}
                    onClick={() => submitMutation.mutate('PRESENT')}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-lg cursor-pointer transition-all duration-150 active:scale-95 flex items-center gap-2"
                  >
                    {submittingStatus === 'PRESENT' ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <CheckCircle2 className="h-4 w-4" />
                    )}
                    Mark PRESENT
                  </Button>

                  <Button
                    size="lg"
                    variant="outline"
                    disabled={submitMutation.isPending}
                    onClick={() => submitMutation.mutate('ABSENT')}
                    className="border-rose-500/40 bg-rose-950/20 text-rose-300 hover:bg-rose-900/40 font-bold text-xs cursor-pointer transition-all duration-150 active:scale-95 flex items-center gap-2"
                  >
                    {submittingStatus === 'ABSENT' ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <XCircle className="h-4 w-4" />
                    )}
                    Mark ABSENT
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card className="glass-card p-6 text-center text-xs text-muted-foreground">
          No active attendance sessions currently open for your batch.
        </Card>
      )}

      {/* Summary Statistics */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="glass-card">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-muted-foreground uppercase">Overall Attendance</p>
                <p className="text-3xl font-extrabold mt-1 text-foreground">
                  {historyData?.overall_percentage ?? 0}%
                </p>
              </div>
              <div className="p-3 bg-primary/10 rounded-2xl text-primary">
                <Award className="h-6 w-6" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-muted-foreground uppercase">Total Sessions</p>
                <p className="text-3xl font-extrabold mt-1 text-foreground">
                  {historyData?.total_sessions ?? 0}
                </p>
              </div>
              <div className="p-3 bg-blue-500/10 rounded-2xl text-blue-500">
                <Clock className="h-6 w-6" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 uppercase">Sessions Present</p>
                <p className="text-3xl font-extrabold mt-1 text-emerald-600 dark:text-emerald-400">
                  {historyData?.present_count ?? 0}
                </p>
              </div>
              <div className="p-3 bg-emerald-500/10 rounded-2xl text-emerald-500">
                <CheckCircle2 className="h-6 w-6" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-rose-600 dark:text-rose-400 uppercase">Sessions Absent</p>
                <p className="text-3xl font-extrabold mt-1 text-rose-600 dark:text-rose-400">
                  {historyData?.absent_count ?? 0}
                </p>
              </div>
              <div className="p-3 bg-rose-500/10 rounded-2xl text-rose-500">
                <XCircle className="h-6 w-6" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Subject-Wise Attendance Breakdown & History Table */}
      <div className="grid gap-6 md:grid-cols-3">
        <Card className="glass-card md:col-span-1">
          <CardHeader>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <BookOpen className="h-5 w-5 text-primary" /> Subject Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {loadingHistory ? (
              <div className="p-4 text-center text-xs text-muted-foreground">Loading subject breakdown...</div>
            ) : !historyData?.subject_stats?.length ? (
              <div className="p-4 text-center text-xs text-muted-foreground">No subject records available.</div>
            ) : (
              historyData.subject_stats.map((s) => (
                <div key={s.subject_id} className="p-3 rounded-xl border border-border/40 bg-white/30 dark:bg-slate-800/30 space-y-1.5 text-xs">
                  <div className="flex justify-between items-center font-semibold text-foreground">
                    <span>{s.subject_name}</span>
                    <span className="font-bold text-primary">{s.percentage}%</span>
                  </div>
                  <div className="w-full bg-slate-200 dark:bg-slate-700 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-emerald-500 h-full transition-all duration-300"
                      style={{ width: `${Math.min(100, Math.max(0, s.percentage))}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[11px] text-muted-foreground pt-0.5">
                    <span>Present: {s.present_count} / {s.total_sessions}</span>
                    <span>Absent: {s.absent_count}</span>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="glass-card md:col-span-2">
          <CardHeader>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <Calendar className="h-5 w-5 text-primary" /> Attendance Records History
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loadingHistory ? (
              <div className="p-4 text-center text-xs text-muted-foreground">Loading history...</div>
            ) : !historyData?.records?.length ? (
              <div className="p-6 text-center text-xs text-muted-foreground">No attendance history records found.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-border/60 text-muted-foreground font-semibold">
                      <th className="p-2.5">Date</th>
                      <th className="p-2.5">Subject</th>
                      <th className="p-2.5">Status</th>
                      <th className="p-2.5">Marked At</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/30">
                    {historyData.records.map((r) => (
                      <tr key={r.id} className="hover:bg-white/20 dark:hover:bg-slate-800/20">
                        <td className="p-2.5 font-medium">{r.date}</td>
                        <td className="p-2.5 font-bold text-foreground">{r.subject_name}</td>
                        <td className="p-2.5">
                          {r.status === 'PRESENT' || r.status === 'LATE' ? (
                            <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-bold text-[10px]">PRESENT</span>
                          ) : (
                            <span className="px-2.5 py-0.5 rounded-full bg-rose-500/20 text-rose-400 font-bold text-[10px]">ABSENT</span>
                          )}
                        </td>
                        <td className="p-2.5 text-muted-foreground font-mono text-[11px]">
                          {new Date(r.marked_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
