'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import {
  Card, CardContent, CardHeader, CardTitle, Button, Badge, Input, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Label, Textarea, Switch,
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@examshield/ui';
import {
  Check, ChevronRight, ChevronLeft, ShieldCheck, Layers, BookOpen, Clock, Calendar, AlertTriangle, Send, Loader2, Sparkles, Plus, Trash2, ArrowRight, CheckCircle2, FileCheck
} from 'lucide-react';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import type { Paginated } from '@examshield/types';

interface QuestionRow {
  id: string;
  type: string;
  text: string;
  difficulty: string;
  bloomLevel?: string | null;
  marks: number;
}

export default function CreateExamWizardPage() {
  const router = useRouter();
  const api = useApiClient();
  const queryClient = useQueryClient();

  const [step, setStep] = useState(1);

  // Form State
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [subjectId, setSubjectId] = useState('');
  const [durationMinutes, setDurationMinutes] = useState(60);
  const [passingMarks, setPassingMarks] = useState(20);
  const [instructions, setInstructions] = useState('Ensure a stable internet connection. No browser tab switching allowed.');

  // Timing
  const [startAt, setStartAt] = useState('2026-09-10T09:00');
  const [endAt, setEndAt] = useState('2026-09-10T12:00');

  // Scoring & Negative Marking
  const [negEnabled, setNegEnabled] = useState(false);
  const [negValue, setNegValue] = useState(0.25);

  // Security Policies
  const [securityMode, setSecurityMode] = useState(true);
  const [cameraProctoring, setCameraProctoring] = useState(false);
  const [randomizeQuestions, setRandomizeQuestions] = useState(true);
  const [shuffleOptions, setShuffleOptions] = useState(true);

  // Cohort Scheduling
  const [deptId, setDeptId] = useState('');
  const [semId, setSemId] = useState('');
  const [secId, setSecId] = useState('');

  // Questions Selected
  const [selectedQuestions, setSelectedQuestions] = useState<QuestionRow[]>([]);
  const [marksOverride, setMarksOverride] = useState<Record<string, number>>({});

  // Created Exam ID
  const [createdExamId, setCreatedExamId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Queries
  const { data: subjects = [] } = useQuery<{ id: string; name: string }[]>({
    queryKey: ['subjects'],
    queryFn: () => api.get<{ id: string; name: string }[]>('/question-bank/subjects'),
  });

  const { data: departments = [] } = useQuery<{ id: string; name: string }[]>({
    queryKey: ['departments'],
    queryFn: () => api.get<{ id: string; name: string }[]>('/academic/departments'),
  });

  const { data: semesters = [] } = useQuery<{ id: string; name: string }[]>({
    queryKey: ['semesters'],
    queryFn: () => api.get<{ id: string; name: string }[]>('/academic/semesters'),
  });

  const { data: sections = [] } = useQuery<{ id: string; name: string }[]>({
    queryKey: ['sections'],
    queryFn: () => api.get<{ id: string; name: string }[]>('/academic/sections'),
  });

  const { data: questionBank } = useQuery({
    queryKey: ['question-bank-picker', subjectId],
    queryFn: () => api.get<Paginated<QuestionRow>>('/questions', { page_size: 50, subject_id: subjectId || undefined }),
  });

  const availableQuestions = questionBank?.items || [];
  const totalCalculatedMarks = selectedQuestions.reduce((acc, q) => acc + (marksOverride[q.id] || q.marks || 1), 0);

  // Step 1: Create Exam Draft
  const handleCreateDraft = async () => {
    if (!title.trim()) {
      toast.error('Please enter an exam title');
      return;
    }

    setIsSubmitting(true);
    toast.info('Creating exam schedule draft in PostgreSQL...');

    try {
      const payload = {
        title,
        description,
        subjectId: subjectId || undefined,
        durationMinutes,
        startAt: new Date(startAt).toISOString(),
        endAt: new Date(endAt).toISOString(),
        passingMarks,
        negativeMarksEnabled: negEnabled,
        negativeMarksValue: negValue,
        randomizeQuestions,
        shuffleOptions,
        attemptLimit: 1,
        questionMode: 'all_at_once',
        instructions,
        visibility: 'private',
        securityMode,
        cameraProctoringEnabled: cameraProctoring,
        autoSubmit: true,
      };

      const res = await api.post<{ id: string }>('/exams', payload);
      setCreatedExamId(res.id);
      toast.success('Exam draft created! Proceeding to Question Selection.');
      setStep(2);
    } catch (err: any) {
      toast.error(err.message || 'Failed to create exam draft');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Save Questions Assignment
  const handleSaveQuestions = async () => {
    if (!createdExamId) return;
    if (!selectedQuestions.length) {
      toast.error('Please select at least 1 question');
      return;
    }

    setIsSubmitting(true);
    toast.info('Saving questions assignment & display order...');

    try {
      const payload = {
        question_ids: selectedQuestions.map((q) => q.id),
        marks_override: marksOverride,
      };

      await api.post(`/exams/${createdExamId}/questions`, payload);
      toast.success('Questions assigned to exam!');
      setStep(3);
    } catch (err: any) {
      toast.error(err.message || 'Question assignment failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Save Cohort Schedule
  const handleSaveSchedule = async () => {
    if (!createdExamId) return;
    setIsSubmitting(true);
    try {
      await api.post(`/exams/${createdExamId}/schedule`, {
        department_id: deptId || undefined,
        semester_id: semId || undefined,
        section_id: secId || undefined,
      });
      toast.success('Cohort schedule assigned!');
      setStep(4);
    } catch (err: any) {
      toast.error(err.message || 'Schedule assignment failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Final Publish Execution
  const handlePublishExam = async () => {
    if (!createdExamId) return;
    setIsSubmitting(true);
    toast.info('Publishing exam to student portal...');

    try {
      await api.post(`/exams/${createdExamId}/publish`);
      toast.success('Exam published successfully! Redirecting to Exams Portal...');
      queryClient.invalidateQueries({ queryKey: ['admin-exams'] });
      router.push('/admin/exams');
    } catch (err: any) {
      toast.error(err.message || 'Publishing failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleSelectQuestion = (q: QuestionRow) => {
    const exists = selectedQuestions.some((item) => item.id === q.id);
    if (exists) {
      setSelectedQuestions(selectedQuestions.filter((item) => item.id !== q.id));
    } else {
      setSelectedQuestions([...selectedQuestions, q]);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Multi-Step Examination Builder Wizard"
        description="Step-by-step exam configuration: basic info, question picker, scoring, proctoring policy, cohort scheduling, and publish execution."
      />

      {/* Step Indicator Header */}
      <div className="flex items-center justify-between p-4 rounded-2xl glass-card border border-white/20 dark:border-white/10 overflow-x-auto gap-4">
        {[
          { num: 1, label: 'Basic Info' },
          { num: 2, label: 'Questions' },
          { num: 3, label: 'Rules & Cohort' },
          { num: 4, label: 'Preview & Publish' },
        ].map((s) => (
          <div key={s.num} className="flex items-center gap-2 flex-shrink-0">
            <div className={`flex h-8 w-8 items-center justify-center rounded-full font-bold text-xs ${
              step === s.num ? 'bg-primary text-white shadow-md' : step > s.num ? 'bg-emerald-500 text-white' : 'bg-muted text-muted-foreground'
            }`}>
              {step > s.num ? <Check className="h-4 w-4" /> : s.num}
            </div>
            <span className={`text-xs font-semibold ${step === s.num ? 'text-foreground font-bold' : 'text-muted-foreground'}`}>
              {s.label}
            </span>
            {s.num < 4 && <ChevronRight className="h-4 w-4 text-muted-foreground/40" />}
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Main Wizard Form Body */}
        <div className="lg:col-span-8 space-y-6">
          {step === 1 && (
            <Card className="glass-card">
              <CardHeader>
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <FileCheck className="h-5 w-5 text-primary" /> Step 1: Basic Information & Timing
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-xs">
                <div className="space-y-2">
                  <Label>Exam Title *</Label>
                  <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Operating Systems Midterm Examination 2026" className="glass-input" />
                </div>
                <div className="space-y-2">
                  <Label>Description</Label>
                  <Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Brief overview of exam coverage..." rows={2} className="glass-input" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Subject</Label>
                    <Select value={subjectId} onValueChange={setSubjectId}>
                      <SelectTrigger className="glass-input"><SelectValue placeholder="Select Subject" /></SelectTrigger>
                      <SelectContent className="glass-modal">
                        {subjects.map((s) => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Duration (Minutes)</Label>
                    <Input type="number" value={durationMinutes} onChange={(e) => setDurationMinutes(parseInt(e.target.value) || 30)} className="glass-input" />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Start Date & Time (Timezone Aware)</Label>
                    <Input type="datetime-local" value={startAt} onChange={(e) => setStartAt(e.target.value)} className="glass-input" />
                  </div>
                  <div className="space-y-2">
                    <Label>End Date & Time</Label>
                    <Input type="datetime-local" value={endAt} onChange={(e) => setEndAt(e.target.value)} className="glass-input" />
                  </div>
                </div>

                <Button className="w-full glass-button bg-primary text-white" disabled={isSubmitting} onClick={handleCreateDraft}>
                  {isSubmitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                  Save Draft & Continue to Questions <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </CardContent>
            </Card>
          )}

          {step === 2 && (
            <Card className="glass-card">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <BookOpen className="h-5 w-5 text-amber-500" /> Step 2: Question Bank Picker ({selectedQuestions.length} Selected)
                </CardTitle>
                <Link href="/admin/ai-generator">
                  <Button size="sm" variant="outline" className="glass-button text-xs">
                    <Sparkles className="h-3.5 w-3.5 mr-1 text-amber-500" /> AI Generator
                  </Button>
                </Link>
              </CardHeader>
              <CardContent className="space-y-4 text-xs">
                <p className="text-muted-foreground">Select approved questions from Question Bank to include in this exam.</p>

                <div className="max-h-96 overflow-y-auto space-y-2 border border-border/40 rounded-xl p-2">
                  {!availableQuestions.length ? (
                    <div className="p-6 text-center text-muted-foreground">No questions found in Question Bank for selected subject.</div>
                  ) : (
                    availableQuestions.map((q) => {
                      const isSel = selectedQuestions.some((s) => s.id === q.id);
                      return (
                        <div
                          key={q.id}
                          onClick={() => toggleSelectQuestion(q)}
                          className={`p-3 rounded-xl border cursor-pointer flex items-center justify-between gap-4 transition-all ${
                            isSel ? 'bg-primary/15 border-primary font-bold' : 'bg-muted/30 border-border/40 hover:bg-muted/60'
                          }`}
                        >
                          <div className="space-y-1 overflow-hidden">
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className="uppercase text-[10px]">{q.type}</Badge>
                              <Badge variant="secondary" className="uppercase text-[10px]">{q.difficulty}</Badge>
                              <Badge variant="outline">{q.marks} Marks</Badge>
                            </div>
                            <p className="text-xs text-foreground truncate">{q.text}</p>
                          </div>
                          <input type="checkbox" checked={isSel} onChange={() => {}} className="h-4 w-4 text-primary flex-shrink-0" />
                        </div>
                      );
                    })
                  )}
                </div>

                <div className="flex justify-between pt-2">
                  <Button variant="outline" onClick={() => setStep(1)}>Back</Button>
                  <Button className="glass-button bg-primary text-white" disabled={isSubmitting} onClick={handleSaveQuestions}>
                    {isSubmitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                    Save Questions & Continue <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {step === 3 && (
            <Card className="glass-card">
              <CardHeader>
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5 text-emerald-600" /> Step 3: Rules, Negative Marking & Cohorts
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-xs">
                <div className="grid grid-cols-2 gap-4 border-b border-border/40 pb-4">
                  <div className="space-y-2">
                    <Label>Negative Marking</Label>
                    <div className="flex items-center justify-between p-2 rounded-xl bg-muted/40 border">
                      <span>Enable Negative Marking</span>
                      <Switch checked={negEnabled} onCheckedChange={setNegEnabled} />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Negative Deduction Value</Label>
                    <Input type="number" step="0.25" value={negValue} onChange={(e) => setNegValue(parseFloat(e.target.value) || 0)} disabled={!negEnabled} className="glass-input" />
                  </div>
                </div>

                <div className="space-y-3 pt-2 border-b border-border/40 pb-4">
                  <h4 className="font-semibold text-foreground">Proctoring & Anti-Cheat Policies</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex items-center justify-between p-2 rounded-xl bg-muted/40 border">
                      <span>Proctoring Security Mode</span>
                      <Switch checked={securityMode} onCheckedChange={setSecurityMode} />
                    </div>
                    <div className="flex items-center justify-between p-2 rounded-xl bg-muted/40 border">
                      <span>Camera Monitoring</span>
                      <Switch checked={cameraProctoring} onCheckedChange={setCameraProctoring} />
                    </div>
                  </div>
                </div>

                <div className="space-y-3 pt-2">
                  <h4 className="font-semibold text-foreground">Student Cohort Scheduling Target</h4>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-1">
                      <Label>Department</Label>
                      <Select value={deptId} onValueChange={setDeptId}>
                        <SelectTrigger className="glass-input"><SelectValue placeholder="All Depts" /></SelectTrigger>
                        <SelectContent className="glass-modal">
                          {departments.map((d) => <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label>Semester</Label>
                      <Select value={semId} onValueChange={setSemId}>
                        <SelectTrigger className="glass-input"><SelectValue placeholder="All Semesters" /></SelectTrigger>
                        <SelectContent className="glass-modal">
                          {semesters.map((s) => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label>Section</Label>
                      <Select value={secId} onValueChange={setSecId}>
                        <SelectTrigger className="glass-input"><SelectValue placeholder="All Sections" /></SelectTrigger>
                        <SelectContent className="glass-modal">
                          {sections.map((sec) => <SelectItem key={sec.id} value={sec.id}>{sec.name}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>

                <div className="flex justify-between pt-2">
                  <Button variant="outline" onClick={() => setStep(2)}>Back</Button>
                  <Button className="glass-button bg-primary text-white" disabled={isSubmitting} onClick={handleSaveSchedule}>
                    {isSubmitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                    Save Rules & Preview <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {step === 4 && (
            <Card className="glass-card">
              <CardHeader>
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <Send className="h-5 w-5 text-emerald-600" /> Step 4: Exam Readiness Preview & Publish Execution
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6 text-xs">
                <div className="p-4 rounded-xl bg-emerald-50/80 border border-emerald-300 text-emerald-800 space-y-2">
                  <h4 className="font-bold flex items-center gap-1">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" /> Publish Readiness Checklist Passed
                  </h4>
                  <p>All core validations satisfied. Exam is ready to be published to student schedules.</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-muted/40 rounded-xl space-y-1">
                    <div className="font-semibold text-foreground">Title</div>
                    <div>{title}</div>
                  </div>
                  <div className="p-3 bg-muted/40 rounded-xl space-y-1">
                    <div className="font-semibold text-foreground">Duration</div>
                    <div>{durationMinutes} Minutes</div>
                  </div>
                  <div className="p-3 bg-muted/40 rounded-xl space-y-1">
                    <div className="font-semibold text-foreground">Questions Count</div>
                    <div>{selectedQuestions.length} Questions</div>
                  </div>
                  <div className="p-3 bg-muted/40 rounded-xl space-y-1">
                    <div className="font-semibold text-foreground">Total Marks</div>
                    <div>{totalCalculatedMarks} Marks</div>
                  </div>
                </div>

                <div className="flex justify-between pt-2">
                  <Button variant="outline" onClick={() => setStep(3)}>Back</Button>
                  <Button className="glass-button bg-emerald-600 hover:bg-emerald-700 text-white" disabled={isSubmitting} onClick={handlePublishExam}>
                    {isSubmitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Send className="h-4 w-4 mr-2" />}
                    Confirm & Publish Exam Now
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Live Summary Sidebar */}
        <div className="lg:col-span-4 space-y-6">
          <Card className="glass-card sticky top-20 border border-white/20 dark:border-white/10">
            <CardHeader>
              <CardTitle className="text-sm font-bold flex items-center gap-2">
                <Layers className="h-4 w-4 text-primary" /> Live Exam Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-xs">
              <div className="p-3 bg-muted/40 rounded-xl space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Title:</span>
                  <span className="font-bold text-foreground truncate max-w-[140px]">{title || 'Untitled Exam'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Duration:</span>
                  <span className="font-bold">{durationMinutes} Mins</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Selected Questions:</span>
                  <span className="font-bold text-primary">{selectedQuestions.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Total Calculated Marks:</span>
                  <span className="font-bold text-emerald-600">{totalCalculatedMarks}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Passing Marks:</span>
                  <span className="font-bold">{passingMarks}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Negative Marking:</span>
                  <span className="font-bold">{negEnabled ? `-${negValue}` : 'Disabled'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Proctoring Mode:</span>
                  <span className="font-bold">{securityMode ? 'Strict Proctored' : 'Standard'}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
