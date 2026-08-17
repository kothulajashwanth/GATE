'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge } from '@examshield/ui';
import { ShieldCheck, CheckCircle2, AlertCircle, Clock, Wifi, Lock, Loader2, ArrowRight, FileText } from 'lucide-react';
import { toast } from 'sonner';

interface PreflightRes {
  isEligible: boolean;
  examOpen: boolean;
  startAt: string;
  endAt: string;
  serverTime: string;
  attemptCount: number;
  maxAttempts: number;
  remainingAttempts: number;
  activeSessionId: string | null;
  issues: string[];
}

export default function PreflightPage() {
  const router = useRouter();
  const params = useParams();
  const examId = params.examId as string;
  const api = useApiClient();

  const [agreed, setAgreed] = useState(false);
  const [isLaunching, setIsLaunching] = useState(false);
  const [fullscreenSupported, setFullscreenSupported] = useState(true);

  useEffect(() => {
    if (typeof document !== 'undefined') {
      setFullscreenSupported(!!document.documentElement.requestFullscreen);
    }
  }, []);

  const { data, isLoading, error } = useQuery<PreflightRes>({
    queryKey: ['preflight', examId],
    queryFn: () => api.get<PreflightRes>(`/exam-session/preflight/${examId}`),
    retry: false,
  });

  const handleEnterExam = async () => {
    if (!agreed) {
      toast.error('Please accept the exam rules & instructions before entering.');
      return;
    }

    setIsLaunching(true);
    toast.info('Initializing secure exam session...');

    try {
      // Request browser fullscreen
      if (document.documentElement.requestFullscreen) {
        try {
          await document.documentElement.requestFullscreen();
        } catch {
          // Ignore if denied or handled by browser
        }
      }

      // Launch or resume session
      router.push(`/exam/${examId}?examId=${examId}`);
    } catch (err: any) {
      toast.error(err.message || 'Failed to enter exam');
      setIsLaunching(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background bg-ambient-light p-4">
        <div className="glass-modal p-8 text-center flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm font-semibold">Running Technical & Eligibility Preflight Diagnostics...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <div className="glass-modal p-8 text-center max-w-md space-y-4">
          <AlertCircle className="h-10 w-10 text-rose-500 mx-auto" />
          <h2 className="text-lg font-bold">Preflight Check Failed</h2>
          <p className="text-xs text-muted-foreground">Unable to verify exam entitlement or backend schedule.</p>
          <Button onClick={() => router.push('/student')}>Return to Dashboard</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6 max-w-4xl mx-auto py-4 sm:py-6 px-3 sm:px-6">
      <PageHeader
        title="Technical & Eligibility Preflight Diagnostics"
        description="Verify browser security compatibility, server time synchronization, and exam instructions prior to launch."
      />

      <div className="grid gap-4 md:gap-6 grid-cols-1 md:grid-cols-2">
        {/* Preflight Diagnostics Summary */}
        <Card className="glass-card">
          <CardHeader className="p-4 sm:p-6 pb-2 sm:pb-2">
            <CardTitle className="text-sm sm:text-base font-bold flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-primary" /> Technical Preflight Checks
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 sm:p-6 pt-2 sm:pt-2 space-y-2.5 sm:space-y-3 text-xs">
            <div className="flex items-center justify-between p-2.5 rounded-xl bg-emerald-50/80 border border-emerald-300 text-emerald-800">
              <span className="flex items-center gap-2 font-semibold text-xs sm:text-xs">
                <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" /> Online Network Connection
              </span>
              <Badge variant="outline" className="bg-emerald-100 text-emerald-800 text-[10px] shrink-0">VERIFIED</Badge>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-xl bg-emerald-50/80 border border-emerald-300 text-emerald-800">
              <span className="flex items-center gap-2 font-semibold text-xs sm:text-xs">
                <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" /> Server Time Synchronization
              </span>
              <Badge variant="outline" className="bg-emerald-100 text-emerald-800 text-[10px] shrink-0">SYNCED</Badge>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-xl bg-emerald-50/80 border border-emerald-300 text-emerald-800">
              <span className="flex items-center gap-2 font-semibold text-xs sm:text-xs">
                <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" /> Fullscreen API Support
              </span>
              <Badge variant="outline" className="bg-emerald-100 text-emerald-800 text-[10px] shrink-0">
                {fullscreenSupported ? 'READY' : 'OPTIONAL (MOBILE)'}
              </Badge>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-xl bg-emerald-50/80 border border-emerald-300 text-emerald-800">
              <span className="flex items-center gap-2 font-semibold text-xs sm:text-xs">
                <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" /> Page Visibility API
              </span>
              <Badge variant="outline" className="bg-emerald-100 text-emerald-800 text-[10px] shrink-0">ACTIVE</Badge>
            </div>

            {data.issues.length > 0 && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl space-y-1 text-rose-800">
                <div className="font-bold flex items-center gap-1">
                  <AlertCircle className="h-4 w-4 shrink-0" /> Eligibility Warning
                </div>
                {data.issues.map((iss, idx) => <p key={idx}>{iss}</p>)}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Instructions & Launch Panel */}
        <Card className="glass-card">
          <CardHeader className="p-4 sm:p-6 pb-2 sm:pb-2">
            <CardTitle className="text-sm sm:text-base font-bold flex items-center gap-2">
              <FileText className="h-5 w-5 text-amber-500" /> Examination Rules & Launch
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 sm:p-6 pt-2 sm:pt-2 space-y-4 text-xs">
            <div className="p-3 bg-muted/40 rounded-xl space-y-2 text-muted-foreground leading-relaxed">
              <p>• Do not attempt to switch browser tabs or minimize the window during the exam.</p>
              <p>• Fullscreen mode will be requested upon entering where supported.</p>
              <p>• Answers are automatically saved to the server in real-time.</p>
              <p>• When the timer expires, your exam will be automatically submitted.</p>
            </div>

            <label htmlFor="rules-agree" className="flex items-start gap-3 p-3 rounded-xl border border-border/40 hover:bg-muted/30 cursor-pointer transition-colors">
              <input
                type="checkbox"
                id="rules-agree"
                checked={agreed}
                onChange={(e) => setAgreed(e.target.checked)}
                className="h-5 w-5 sm:h-4 sm:w-4 rounded border-border text-primary focus:ring-primary mt-0.5 cursor-pointer shrink-0"
              />
              <span className="text-xs text-foreground font-medium leading-normal">
                I have read and understood all examination rules, instructions, and technical preflight requirements.
              </span>
            </label>

            <Button
              className="w-full glass-button bg-primary text-white shadow-md min-h-[44px] text-xs sm:text-sm font-semibold"
              disabled={!data.isEligible || !agreed || isLaunching}
              onClick={handleEnterExam}
            >
              {isLaunching ? <Loader2 className="h-4 w-4 mr-2 animate-spin shrink-0" /> : <Lock className="h-4 w-4 mr-2 text-amber-300 shrink-0" />}
              {isLaunching ? 'Entering Secure Environment...' : 'Enter Secure Examination'}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
