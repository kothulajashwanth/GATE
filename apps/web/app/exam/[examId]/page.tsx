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

  // --- fetch or start session ---
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
      setSession(sessionData);
      setDeadline(sessionData.deadlineAt);
      setWarnings(sessionData.warningCount);
      // pre-fill answers from session if any (resume)
      const existingAnswers: Record<string, string[]> = {};
      sessionData.questions.forEach(q => {
        if (q.isAnswered) {
          // would need actual answer data; for now just mark answered
        }
      });
    }
  }, [sessionData]);

  // --- lifecycle helpers (defined before effects that use them) ---
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
      // silent — auto-save retries next tick
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

  // --- timer ---
  useEffect(() => {
    if (!deadline) return;
    const end = new Date(deadline).getTime();
    const tick = () => {
      const now = Date.now();
      const remaining = Math.max(0, end - now);
      setTimeRemaining(remaining);
      if (remaining <= 0) {
        autoSubmit();
      }
    };
    tick();
    timerRef.current = setInterval(tick, 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [deadline, autoSubmit]);

  // --- auto-save every 10s ---
  useEffect(() => {
    if (!session) return;
    autoSaveRef.current = setInterval(() => {
      saveAnswer();
    }, 10000);
    return () => {
      if (autoSaveRef.current) clearInterval(autoSaveRef.current);
    };
  }, [session, saveAnswer]);

  // --- heartbeat every 5s ---
  useEffect(() => {
    if (!session) return;
    heartbeatRef.current = setInterval(async () => {
      try {
        const res = await api.post<{ status: string; warningCount: number }>(
          `/exam-session/${session.sessionId}/heartbeat`,
          { warningCount: warnings },
        );
        if (res.status === 'terminated') {
          handleTerminated();
        }
        setWarnings(res.warningCount);
      } catch {
        // ignore
      }
    }, 5000);
    return () => {
      if (heartbeatRef.current) clearInterval(heartbeatRef.current);
    };
  }, [session, warnings, handleTerminated]);

  // --- security mode: fullscreen enforcement ---
  useEffect(() => {
    if (!session?.securityMode) return;

    const enterFullscreen = async () => {
      try {
        if (document.documentElement.requestFullscreen) {
          await document.documentElement.requestFullscreen();
          setIsFullscreen(true);
        }
      } catch {
        toast.error('Fullscreen required for this exam. Please allow it.');
      }
    };

    const onFullscreenChange = () => {
      const fs = document.fullscreenElement === document.documentElement;
      setIsFullscreen(fs);
      if (!fs && session?.securityMode) {
        // user exited fullscreen
        recordViolation('fullscreen_exit', 'Exited fullscreen mode');
        enterFullscreen();
      }
    };

    const onVisibilityChange = () => {
      if (document.hidden && session?.securityMode) {
        recordViolation('visibility_change', 'Tab hidden or minimized');
      }
    };

    const onBlur = () => {
      if (session?.securityMode) {
        recordViolation('window_blur', 'Window lost focus');
      }
    };

    const onKeyDown = (e: KeyboardEvent) => {
      if (session?.securityMode) {
        // Block dangerous shortcuts
        const blocked = [
          e.key === 'F12',
          e.ctrlKey && e.shiftKey && ['I', 'J', 'C'].includes(e.key), // DevTools
          e.ctrlKey && e.key === 'u', // View source
          e.ctrlKey && e.key === 's', // Save page
          e.ctrlKey && e.key === 'p', // Print
          e.metaKey && e.key === 'Option', // Mac dev tools
        ];
        if (blocked.some(b => b)) {
          e.preventDefault();
          recordViolation('keyboard_shortcut', `Blocked shortcut: ${e.key}`);
        }
      }
    };

    const onCopy = (e: ClipboardEvent) => {
      if (session?.securityMode) {
        e.preventDefault();
        recordViolation('copy', 'Copy blocked');
      }
    };

    const onPaste = (e: ClipboardEvent) => {
      if (session?.securityMode) {
        e.preventDefault();
        recordViolation('paste', 'Paste blocked');
      }
    };

    const onSelectStart = (e: Event) => {
      if (session?.securityMode) {
        e.preventDefault();
        recordViolation('text_selection', 'Text selection blocked');
      }
    };

    const onContextMenu = (e: MouseEvent) => {
      if (session?.securityMode) {
        e.preventDefault();
        recordViolation('right_click', 'Context menu blocked');
      }
    };

    enterFullscreen();
    document.addEventListener('fullscreenchange', onFullscreenChange);
    document.addEventListener('visibilitychange', onVisibilityChange);
    window.addEventListener('blur', onBlur);
    window.addEventListener('keydown', onKeyDown, true);
    document.addEventListener('copy', onCopy);
    document.addEventListener('paste', onPaste);
    document.addEventListener('selectstart', onSelectStart);
    document.addEventListener('contextmenu', onContextMenu);

    return () => {
      document.removeEventListener('fullscreenchange', onFullscreenChange);
      document.removeEventListener('visibilitychange', onVisibilityChange);
      window.removeEventListener('blur', onBlur);
      window.removeEventListener('keydown', onKeyDown, true);
      document.removeEventListener('copy', onCopy);
      document.removeEventListener('paste', onPaste);
      document.removeEventListener('selectstart', onSelectStart);
      document.removeEventListener('contextmenu', onContextMenu);
      if (document.fullscreenElement === document.documentElement) {
        document.exitFullscreen().catch(() => {});
      }
    };
  }, [session, warnings, recordViolation]);

  const currentQuestion = session?.questions[currentIndex];
  const progress = session ? ((currentIndex + 1) / session.questions.length) * 100 : 0;

  const navigate = (delta: number) => {
    if (!session) return;
    const next = currentIndex + delta;
    if (next >= 0 && next < session.questions.length) {
      setCurrentIndex(next);
    }
  };

  const handleAnswerChange = (answer: string[]) => {
    setAnswers(prev => ({ ...prev, [currentQuestion?.id ?? '']: answer }));
  };

  const handleSubmit = async () => {
    if (!session) return;
    setIsSubmitting(true);
    try {
      await saveAnswer(); // final save
      await api.post(`/exam-session/${session.sessionId}/submit`);
      toast.success('Exam submitted');
      clearIntervals();
      router.push('/student/exams/completed');
    } catch (e) {
      toast.error('Submit failed');
      setIsSubmitting(false);
    }
  };

  if (isLoading || !session) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center text-center p-4">
        <AlertTriangle className="h-12 w-12 text-destructive mx-auto mb-4" />
        <h1 className="text-2xl font-bold">Failed to load exam</h1>
        <p className="text-muted-foreground mt-2">{error.message}</p>
        <Button onClick={() => router.push('/student')} className="mt-4">Go back</Button>
      </div>
    );
  }

  const answeredCount = session.questions.filter(q => answers[q.id]?.length).length;

  return (
    <div className="min-h-screen bg-background">
      {/* Top bar */}
      <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
        <div className="flex items-center justify-between px-4 py-2">
          <div className="flex items-center gap-4">
            <ShieldCheck className="h-5 w-5 text-primary" />
            <div>
              <h1 className="font-semibold truncate max-w-xs">{session.examTitle}</h1>
              <p className="text-xs text-muted-foreground">{answeredCount} / {session.questions.length} answered</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Timer */}
            <div className={cn('flex items-center gap-2 px-3 py-1 rounded-lg font-mono text-lg', timeRemaining < 5 * 60 * 1000 ? 'text-destructive animate-pulse' : '')}>
              <Clock className="h-5 w-5" />
              {formatDuration(timeRemaining / 1000)}
            </div>

            {/* Warnings */}
            <div className="flex items-center gap-2">
              <Shield className={cn('h-5 w-5', warnings > 0 ? 'text-destructive' : 'text-muted-foreground')} />
              <Badge variant={warnings > 0 ? 'destructive' : 'success'}>
                Warnings: {warnings} / {session.maxWarnings}
              </Badge>
            </div>

            {/* Security status */}
            {session.securityMode && (
              <Badge variant="outline" className={cn(isFullscreen ? 'text-emerald-600 border-emerald-600' : 'text-amber-600 border-amber-600')}>
                {isFullscreen ? '🔒 Secured' : '⚠️ Enter Fullscreen'}
              </Badge>
            )}
          </div>
        </div>
        <Progress value={progress} className="h-1 mt-2" />
      </header>

      {/* Main exam area */}
      <main className="p-4 max-w-4xl mx-auto">
        {/* Question palette (bottom on mobile, side on desktop) */}
        <Tabs defaultValue="question" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="question">Question {currentIndex + 1}</TabsTrigger>
            <TabsTrigger value="palette">Palette ({answeredCount}/{session.questions.length})</TabsTrigger>
          </TabsList>

          <TabsContent value="question" className="mt-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-lg">
                  <Badge variant="outline" className="mr-2">{currentQuestion?.type?.replace('_', ' ').toUpperCase()}</Badge>
                  <Badge variant={currentQuestion?.isAnswered ? 'success' : 'outline'} className="mr-2">
                    {currentQuestion?.marks} marks
                  </Badge>
                  {currentQuestion?.negativeMarks && currentQuestion.negativeMarks > 0 && (
                    <Badge variant="destructive">-{currentQuestion.negativeMarks} per wrong</Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {currentQuestion?.imageUrl && (
                  <div className="rounded-lg overflow-hidden border">
                    <img src={currentQuestion.imageUrl} alt="Question" className="w-full h-auto max-h-64 object-contain" />
                  </div>
                )}

                <div className="prose max-w-none">
                  <p className="text-lg">{currentQuestion?.text}</p>
                </div>

                {currentQuestion?.type === 'mcq' || currentQuestion?.type === 'multi_select' ? (
                  <div className="space-y-2">
                    {currentQuestion.options?.map((opt, i) => (
                      <label
                        key={i}
                        className={cn(
                          'flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors',
                          answers[currentQuestion.id]?.includes(opt)
                            ? 'bg-primary/10 border-primary'
                            : 'hover:bg-accent'
                        )}
                      >
                        <input
                          type={currentQuestion.type === 'multi_select' ? 'checkbox' : 'radio'}
                          name={`q-${currentQuestion.id}`}
                          checked={answers[currentQuestion.id]?.includes(opt) ?? false}
                          onChange={(e) => {
                            if (currentQuestion.type === 'multi_select') {
                              const current = answers[currentQuestion.id] ?? [];
                              handleAnswerChange(
                                e.target.checked
                                  ? [...current, opt]
                                  : current.filter(a => a !== opt)
                              );
                            } else {
                              handleAnswerChange([opt]);
                            }
                          }}
                          className="h-4 w-4 text-primary"
                        />
                        <span className="text-sm">{opt}</span>
                      </label>
                    ))}
                  </div>
                ) : currentQuestion?.type === 'true_false' ? (
                  <div className="space-y-2">
                    {['True', 'False'].map((opt) => (
                      <label
                        key={opt}
                        className={cn(
                          'flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors',
                          answers[currentQuestion.id]?.includes(opt)
                            ? 'bg-primary/10 border-primary'
                            : 'hover:bg-accent'
                        )}
                      >
                        <input
                          type="radio"
                          name={`q-${currentQuestion.id}`}
                          checked={answers[currentQuestion.id]?.includes(opt) ?? false}
                          onChange={(e) => handleAnswerChange(e.target.checked ? [opt] : [])}
                          className="h-4 w-4 text-primary"
                        />
                        <span className="text-sm">{opt}</span>
                      </label>
                    ))}
                  </div>
                ) : currentQuestion?.type === 'fill_blank' ? (
                  <div>
                    <Input
                      placeholder="Type your answer..."
                      value={answers[currentQuestion.id]?.[0] ?? ''}
                      onChange={(e) => handleAnswerChange([e.target.value])}
                      className="w-full"
                    />
                  </div>
                ) : currentQuestion?.type === 'paragraph' ? (
                  <div>
                    <Textarea
                      placeholder="Write your answer..."
                      value={answers[currentQuestion.id]?.[0] ?? ''}
                      onChange={(e) => handleAnswerChange([e.target.value])}
                      className="w-full min-h-[150px]"
                      rows={8}
                    />
                  </div>
                ) : currentQuestion?.type === 'coding' ? (
                  <div>
                    <Textarea
                      placeholder="Write your code..."
                      value={answers[currentQuestion.id]?.[0] ?? ''}
                      onChange={(e) => handleAnswerChange([e.target.value])}
                      className="w-full min-h-[300px] font-mono text-sm"
                      rows={20}
                      spellCheck={false}
                    />
                  </div>
                ) : (
                  <div className="text-muted-foreground">Question type not fully implemented yet</div>
                )}
              </CardContent>
            </Card>

            {/* Navigation */}
            <div className="flex items-center justify-between mt-4">
              <Button variant="outline" onClick={() => navigate(-1)} disabled={currentIndex === 0}>
                <ChevronLeft className="h-4 w-4 mr-2" /> Previous
              </Button>
              <div className="flex gap-2">
                {session.questions.map((q, i) => (
                  <Button
                    key={q.id}
                    variant={i === currentIndex ? 'default' : answers[q.id]?.length ? 'outline' : 'outline'}
                    size="icon"
                    className={cn(
                      'h-8 w-8',
                      i === currentIndex ? 'bg-primary text-primary-foreground' :
                      answers[q.id]?.length ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200' :
                      ''
                    )}
                    onClick={() => setCurrentIndex(i)}
                  >
                    {i + 1}
                  </Button>
                ))}
              </div>
              <Button variant="outline" onClick={() => navigate(1)} disabled={currentIndex === session.questions.length - 1}>
                Next <ChevronRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="palette" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle>Question Palette</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-6 gap-2 sm:grid-cols-8 lg:grid-cols-10">
                  {session.questions.map((q, i) => (
                    <Button
                      key={q.id}
                      variant={
                        i === currentIndex ? 'default' :
                        answers[q.id]?.length ? 'outline' : 'outline'
                      }
                      className={cn(
                        'h-10 aspect-square text-xs',
                        i === currentIndex ? 'bg-primary text-primary-foreground' :
                        answers[q.id]?.length ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200' :
                        ''
                      )}
                      onClick={() => setCurrentIndex(i)}
                    >
                      {i + 1}
                    </Button>
                  ))}
                </div>
                <div className="flex items-center gap-4 mt-4 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <span className="w-3 h-3 rounded bg-primary" />
                    Current
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-3 h-3 rounded bg-emerald-500" />
                    Answered
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-3 h-3 rounded border" />
                    Unanswered
                  </span>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* Submit confirmation */}
      <Dialog open={showSubmitConfirm} onOpenChange={setShowSubmitConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Submit Exam?</DialogTitle>
            <DialogDescription>
              You have answered {answeredCount} of {session.questions.length} questions.
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSubmitConfirm(false)}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={isSubmitting}>
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Submit Exam
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Termination dialog */}
      {session?.status === 'terminated' && (
        <Dialog open onOpenChange={() => router.push('/student')}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Exam Terminated</DialogTitle>
              <DialogDescription>
                You exceeded the maximum security warnings. This attempt is locked permanently.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button onClick={() => router.push('/student')}>OK</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Submit confirm trigger */}
      <Button
        className="fixed bottom-4 right-4 z-50"
        onClick={() => setShowSubmitConfirm(true)}
        disabled={isSubmitting}
        size="lg"
      >
        <Send className="h-5 w-5 mr-2" />
        Submit Exam
      </Button>
      </div>
    );
  }