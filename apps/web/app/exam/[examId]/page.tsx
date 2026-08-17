'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import {
  Card, CardContent, CardHeader, CardTitle,
  Button, Badge, Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
  Progress, Separator, Tabs, TabsContent, TabsList, TabsTrigger, Input, Textarea,
} from '@examshield/ui';
import { AlertCircle, Clock, Shield, Wifi, Zap, ChevronLeft, ChevronRight, Save, Flag, Send, Check, X, Loader2, ShieldCheck, AlertTriangle, Info, Pause, Play } from 'lucide-react';
import { formatDuration, cn } from '@examshield/utils';
import { toast } from 'sonner';

interface QuestionView {
  id: string;
  type: string;
  text: string;
  options: string[] | null;
  imageUrl: string | null;
  marks: number;
  negativeMarks: number;
  isAnswered: boolean;
}

interface SessionView {
  sessionId: string;
  examId: string;
  examTitle: string;
  examInstructions: string | null;
  startedAt: string;
  deadlineAt: string;
  durationMinutes: number;
  warningCount: number;
  maxWarnings: number;
  status: string;
  questions: QuestionView[];
  questionMode: string;
  securityMode: boolean;
  negativeMarksEnabled: boolean;
  negativeMarksValue: number;
}

export default function ExamPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const api = useApiClient();
  const queryClient = useQueryClient();
  const examId = searchParams.get('examId');

  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string[]>>({});
  const [warnings, setWarnings] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showSubmitConfirm, setShowSubmitConfirm] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [deadline, setDeadline] = useState<string | null>(null);
  const [session, setSession] = useState<SessionView | null>(null);
  const [securityViolations, setSecurityViolations] = useState<string[]>([]);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatRef = useRef<NodeJS.Timeout | null>(null);
  const autoSaveRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch or start session
  const { data: sessionData, isLoading, error } = useQuery<SessionView>({
    queryKey: ['exam-session', examId],
    queryFn: async () => {
      if (!examId) throw new Error('No exam ID');
      const res = await api.post('/exam-session/start', { examId });
      return res as SessionView;
    },
    enabled: !!examId,
    retry: false,
  });

  useEffect(() => {
    if (sessionData) {
      queueMicrotask(() => {
        setSession(sessionData);
        setDeadline(sessionData.deadlineAt);
        setWarnings(sessionData.warningCount);
      });
    }
  }, [sessionData]);

  const clearIntervals = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (heartbeatRef.current) clearInterval(heartbeatRef.current);
    if (autoSaveRef.current) clearInterval(autoSaveRef.current);
  }, []);

  const handleTerminated = useCallback(() => {
    clearIntervals();
    toast.error('Exam terminated: maximum security warnings reached');
    router.push('/student');
  }, [clearIntervals, router]);

  const recordViolation = useCallback(
    async (type: string, reason: string) => {
      if (!session) return;
      try {
        const res = await api.post<{ warningCount: number; terminated: boolean }>(
          `/exam-session/${session.sessionId}/violation`,
          { violationType: type, reason },
        );
        setWarnings(res.warningCount);
        if (res.terminated) {
          handleTerminated();
        }
      } catch {
        // ignore
      }
    },
    [api, session, handleTerminated],
  );

  const saveAnswer = useCallback(async () => {
    if (!session) return;
    const q = session.questions[currentIndex];
    const ans = q ? answers[q.id] : undefined;
    if (!q || !ans?.length) return;
    try {
      await api.post(`/exam-session/${session.sessionId}/answer`, {
        questionId: q.id,
        answer: ans,
      });
    } catch {
      // retry
    }
  }, [api, session, answers, currentIndex]);

  const autoSubmit = useCallback(async () => {
    if (!session) return;
    try {
      for (const [qid, ans] of Object.entries(answers)) {
        await api.post(`/exam-session/${session.sessionId}/answer`, { questionId: qid, answer: ans });
      }
      await api.post(`/exam-session/${session.sessionId}/submit`);
      clearIntervals();
      toast.info('Time up — exam auto-submitted');
      router.push('/student/exams/completed');
    } catch {
      toast.error('Auto-submit failed. Contact invigilator.');
    }
  }, [api, session, answers, clearIntervals, router]);

  // Timer countdown
  useEffect(() => {
    if (!deadline) return;
    const updateTime = () => {
      const remaining = Math.max(0, Math.floor((new Date(deadline).getTime() - Date.now()) / 1000));
      setTimeRemaining(remaining);
      if (remaining <= 0) {
        autoSubmit();
      }
    };
    updateTime();
    timerRef.current = setInterval(updateTime, 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [deadline, autoSubmit]);

  // Heartbeat
  useEffect(() => {
    if (!session) return;
    heartbeatRef.current = setInterval(async () => {
      try {
        await api.post(`/exam-session/${session.sessionId}/heartbeat`);
      } catch {
        // silent
      }
    }, 30000);
    return () => {
      if (heartbeatRef.current) clearInterval(heartbeatRef.current);
    };
  }, [api, session]);

  // Tab switch & visibility detector
  useEffect(() => {
    if (!session?.securityMode) return;

    const handleVisibilityChange = () => {
      if (document.hidden) {
        setSecurityViolations((prev) => [...prev, 'Tab switched / window hidden']);
        recordViolation('TAB_SWITCH', 'Switched browser tab or minimized window');
      }
    };

    const handleBlur = () => {
      // On mobile/touch devices, blur triggers when touch inputs or soft keyboards open.
      // Only record focus loss if document is also hidden or non-touch desktop device.
      const isMobileTouch = typeof window !== 'undefined' && ('ontouchstart' in window || navigator.maxTouchPoints > 0);
      if (document.hidden || !isMobileTouch) {
        setSecurityViolations((prev) => [...prev, 'Window lost focus']);
        recordViolation('FOCUS_LOST', 'Window lost focus');
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('blur', handleBlur);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('blur', handleBlur);
    };
  }, [session, recordViolation]);

  const handleAnswerChange = (ans: string[]) => {
    if (!session) return;
    const q = session.questions[currentIndex];
    if (!q) return;
    setAnswers((prev) => ({ ...prev, [q.id]: ans }));
  };

  const navigate = (delta: number) => {
    if (!session) return;
    saveAnswer();
    const newIdx = currentIndex + delta;
    if (newIdx >= 0 && newIdx < session.questions.length) {
      setCurrentIndex(newIdx);
    }
  };

  const handleSubmit = async () => {
    if (!session) return;
    setIsSubmitting(true);
    try {
      await saveAnswer();
      await api.post(`/exam-session/${session.sessionId}/submit`);
      clearIntervals();
      toast.success('Exam submitted successfully');
      router.push('/student');
    } catch (e: any) {
      toast.error(e.message || 'Submission failed');
    } finally {
      setIsSubmitting(false);
      setShowSubmitConfirm(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background bg-ambient-light p-4">
        <div className="glass-modal p-8 text-center flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm font-semibold">Initializing Secure Liquid Glass Exam Environment...</p>
        </div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <div className="glass-modal p-8 text-center max-w-md space-y-4">
          <AlertCircle className="h-10 w-10 text-rose-500 mx-auto" />
          <h2 className="text-lg font-bold">Unable to Load Examination</h2>
          <p className="text-xs text-muted-foreground">The requested exam session is unavailable or expired.</p>
          <Button onClick={() => router.push('/student')}>Return to Dashboard</Button>
        </div>
      </div>
    );
  }

  const currentQuestion = session.questions[currentIndex];
  const answeredCount = Object.keys(answers).filter((k) => answers[k]?.length).length;

  return (
    <div className="min-h-screen bg-background bg-ambient-light flex flex-col selection:bg-none">
      {/* Top Restrained Glass Header */}
      <header className="sticky top-0 z-40 glass-navbar px-3 sm:px-6 py-2.5 sm:py-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <ShieldCheck className="h-5 w-5 sm:h-6 sm:w-6 text-primary shrink-0" />
          <div>
            <h1 className="text-xs sm:text-sm font-bold text-foreground line-clamp-1">{session.examTitle}</h1>
            <p className="text-[9px] sm:text-[10px] text-muted-foreground font-mono">Secure Proctoring Enabled</p>
          </div>
        </div>

        {/* Live Timer & Warnings */}
        <div className="flex items-center gap-2 sm:gap-4 ml-auto">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-600 dark:text-amber-400 font-mono font-bold text-xs sm:text-sm">
            <Clock className="h-3.5 w-3.5 sm:h-4 sm:w-4 shrink-0" />
            {formatDuration(timeRemaining)}
          </div>
          {session.maxWarnings > 0 && (
            <Badge variant={warnings > 0 ? 'destructive' : 'outline'} className="text-[10px] sm:text-xs py-0.5 px-2">
              Warnings: {warnings}/{session.maxWarnings}
            </Badge>
          )}
        </div>
      </header>

      {/* Main Restrained Exam Area */}
      <main className="flex-1 p-3 sm:p-6 max-w-4xl mx-auto w-full space-y-4 sm:space-y-6 pb-28">
        <Tabs defaultValue="question" className="w-full">
          <TabsList className="grid w-full grid-cols-2 glass-surface p-1">
            <TabsTrigger value="question" className="text-xs sm:text-sm">Question {currentIndex + 1}</TabsTrigger>
            <TabsTrigger value="palette" className="text-xs sm:text-sm">Palette ({answeredCount}/{session.questions.length})</TabsTrigger>
          </TabsList>

          <TabsContent value="question" className="mt-3 sm:mt-4 space-y-4">
            <Card className="glass-card p-1 sm:p-2">
              <CardHeader className="flex flex-row items-center justify-between pb-2 p-3 sm:p-6">
                <CardTitle className="text-xs sm:text-sm font-bold flex items-center gap-2">
                  <Badge variant="outline" className="uppercase text-[10px] sm:text-xs">{currentQuestion?.type?.replace('_', ' ')}</Badge>
                  <Badge variant="secondary" className="text-[10px] sm:text-xs">{currentQuestion?.marks} Marks</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-xs sm:text-xs p-3 sm:p-6 pt-0 sm:pt-0">
                <p className="text-sm sm:text-base font-semibold text-foreground leading-relaxed">{currentQuestion?.text}</p>

                {currentQuestion?.options && currentQuestion.options.length > 0 && (
                  <div className="space-y-2 pt-2">
                    {currentQuestion.options.map((opt, oIdx) => {
                      const letter = String.fromCharCode(65 + oIdx);
                      const isSelected = answers[currentQuestion.id]?.includes(opt) || answers[currentQuestion.id]?.includes(letter);
                      return (
                        <label
                          key={oIdx}
                          onClick={() => handleAnswerChange([opt])}
                          className={cn(
                            'flex items-center gap-3 p-3 sm:p-3.5 rounded-xl border cursor-pointer transition-all min-h-[44px]',
                            isSelected
                              ? 'bg-primary/15 border-primary text-foreground font-semibold shadow-sm'
                              : 'bg-muted/30 border-border/50 hover:bg-muted/60 text-foreground'
                          )}
                        >
                          <input
                            type="radio"
                            name={`q-${currentQuestion.id}`}
                            checked={isSelected}
                            onChange={() => {}}
                            className="h-4 w-4 text-primary shrink-0"
                          />
                          <span className="font-bold w-4 shrink-0">{letter}.</span>
                          <span className="text-xs sm:text-sm leading-snug">{opt}</span>
                        </label>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Navigation controls */}
            <div className="flex items-center justify-between pt-2">
              <Button
                variant="outline"
                onClick={() => navigate(-1)}
                disabled={currentIndex === 0}
                className="glass-button text-xs sm:text-sm min-h-[40px]"
              >
                <ChevronLeft className="h-4 w-4 mr-1 shrink-0" /> Previous
              </Button>
              <span className="text-xs text-muted-foreground font-mono">
                {currentIndex + 1} / {session.questions.length}
              </span>
              <Button
                variant="outline"
                onClick={() => navigate(1)}
                disabled={currentIndex === session.questions.length - 1}
                className="glass-button text-xs sm:text-sm min-h-[40px]"
              >
                Next <ChevronRight className="h-4 w-4 ml-1 shrink-0" />
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="palette" className="mt-3 sm:mt-4">
            <Card className="glass-card">
              <CardHeader className="p-4 sm:p-6">
                <CardTitle className="text-xs sm:text-sm font-bold">Question Palette Matrix</CardTitle>
              </CardHeader>
              <CardContent className="p-4 sm:p-6 pt-0 sm:pt-0 space-y-4">
                <div className="grid grid-cols-5 xs:grid-cols-6 sm:grid-cols-8 md:grid-cols-10 gap-2">
                  {session.questions.map((q, idx) => {
                    const isAns = (answers[q.id]?.length ?? 0) > 0;
                    return (
                      <Button
                        key={q.id}
                        variant={idx === currentIndex ? 'default' : isAns ? 'secondary' : 'outline'}
                        className={cn(
                          'h-9 w-full font-mono text-xs p-0',
                          idx === currentIndex ? 'bg-primary text-white font-bold' :
                          isAns ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-700 dark:text-emerald-300 font-bold' : ''
                        )}
                        onClick={() => setCurrentIndex(idx)}
                      >
                        {idx + 1}
                      </Button>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* Floating Submit Button */}
      <div className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-40">
        <Button
          size="lg"
          onClick={() => setShowSubmitConfirm(true)}
          className="glass-button bg-primary text-white shadow-lg text-xs sm:text-sm h-11 sm:h-12 px-4 sm:px-6"
        >
          <Send className="h-4 w-4 mr-2" /> Submit Examination
        </Button>
      </div>

      {/* Submit Confirm Dialog */}
      <Dialog open={showSubmitConfirm} onOpenChange={setShowSubmitConfirm}>
        <DialogContent className="glass-modal">
          <DialogHeader>
            <DialogTitle>Confirm Exam Submission?</DialogTitle>
            <DialogDescription>
              You have answered {answeredCount} of {session.questions.length} questions.
              Are you sure you want to finish your attempt?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSubmitConfirm(false)}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={isSubmitting}>
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Submit Final Answers
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}