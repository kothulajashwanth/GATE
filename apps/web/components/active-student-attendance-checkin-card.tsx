'use client';

import { useQuery } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { useAuth } from '@clerk/nextjs';
import { Card, CardContent, Button } from '@examshield/ui';
import { Clock, ShieldCheck, ArrowRight, Sparkles } from 'lucide-react';
import Link from 'next/link';

interface ActiveSessionData {
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

export function ActiveStudentAttendanceCheckinCard() {
  const api = useApiClient();
  const { isLoaded, isSignedIn } = useAuth();

  const { data: activeSession } = useQuery<ActiveSessionData | null>({
    queryKey: ['student', 'active-attendance', isLoaded, isSignedIn],
    queryFn: async () => {
      try {
        const res = await api.get<ActiveSessionData | null>('/attendance/student/active');
        return res;
      } catch {
        return null;
      }
    },
    enabled: isLoaded && isSignedIn,
    refetchInterval: 15000,
  });

  if (!activeSession || activeSession.already_submitted) {
    return null;
  }

  return (
    <Card className="glass-card border border-emerald-500/30 bg-gradient-to-r from-emerald-950/40 via-slate-900/80 to-teal-950/40 p-6 shadow-2xl relative overflow-hidden animate-in fade-in slide-in-from-top-4 duration-300">
      <div className="absolute top-0 right-0 p-4 opacity-10 text-emerald-400">
        <ShieldCheck className="h-32 w-32" />
      </div>
      <CardContent className="p-0 relative z-10 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-bold text-[10px] uppercase tracking-wider">
                <Sparkles className="h-3 w-3" /> ATTENDANCE REQUIRED
              </span>
              <span className="text-xs text-slate-400 flex items-center gap-1 font-mono">
                <Clock className="h-3 w-3" /> {activeSession.start_time} ({activeSession.duration_minutes}m)
              </span>
            </div>
            <h3 className="text-xl font-extrabold text-white tracking-tight">
              {activeSession.subject_name} Attendance is Now Open
            </h3>
            <p className="text-xs text-slate-300">
              Session: <strong className="text-white">{activeSession.title}</strong> · Please submit your attendance status before the session ends.
            </p>
          </div>

          <Button
            asChild
            size="lg"
            className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-lg cursor-pointer transition-all duration-150 active:scale-95 shrink-0"
          >
            <Link href="/student/attendance">
              Mark Attendance <ArrowRight className="h-4 w-4 ml-1.5" />
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
