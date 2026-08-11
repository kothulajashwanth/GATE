'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import {
  Card, CardContent, CardHeader, CardTitle, Button, Badge, Input, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Label,
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@examshield/ui';
import { Layers, Sparkles, CheckCircle2, AlertCircle, Loader2, ArrowRight, BookOpen, ShieldCheck, FileCheck } from 'lucide-react';
import { toast } from 'sonner';

interface BlueprintRuleItem {
  subject_id?: string;
  topic?: string;
  question_type?: string;
  difficulty?: string;
  bloom_level?: string;
  count: number;
  marks: number;
}

interface AvailabilityRes {
  total_requested: number;
  total_available: number;
  total_gap: int;
  rules_availability: {
    rule_index: number;
    topic: string;
    difficulty: string;
    bloom_level: string;
    requested: number;
    available: number;
    gap: number;
  }[];
}

export default function ExamBlueprintPage() {
  const api = useApiClient();

  const [examId, setExamId] = useState('');
  const [topic, setTopic] = useState('Data Structures & Algorithms');
  const [easyCount, setEasyCount] = useState(5);
  const [medCount, setMedCount] = useState(10);
  const [hardCount, setHardCount] = useState(5);

  const [checking, setChecking] = useState(false);
  const [filling, setFilling] = useState(false);
  const [assembling, setAssembling] = useState(false);

  const [availability, setAvailability] = useState<AvailabilityRes | null>(null);

  const { data: exams = [] } = useQuery<{ id: string; title: string }[]>({
    queryKey: ['admin', 'exams-list'],
    queryFn: async () => {
      const res = await api.get<{ items: { id: string; title: string }[] }>('/exams', { page_size: 50 });
      return res.items || [];
    },
  });

  const getRules = (): BlueprintRuleItem[] => [
    { topic, difficulty: 'easy', bloom_level: 'understand', count: easyCount, marks: 1 },
    { topic, difficulty: 'medium', bloom_level: 'apply', count: medCount, marks: 2 },
    { topic, difficulty: 'hard', bloom_level: 'analyze', count: hardCount, marks: 4 },
  ];

  // Step 1: Check Availability in PostgreSQL Question Bank
  const handleCheckAvailability = async () => {
    setChecking(true);
    toast.info('Checking Question Bank catalog availability...');
    try {
      const res = await api.post<AvailabilityRes>('/ai/blueprints/check-availability', {
        exam_id: examId || undefined,
        rules: getRules(),
      });
      setAvailability(res);
      toast.success(`Found ${res.total_available} matching questions (${res.total_gap} gap missing)`);
    } catch (err: any) {
      toast.error(err.message || 'Availability check failed');
    } finally {
      setChecking(false);
    }
  };

  // Step 2: Fill Gaps with AI
  const handleFillGaps = async () => {
    if (!availability || availability.total_gap <= 0) return;
    setFilling(true);
    toast.info(`Generating ${availability.total_gap} missing questions using AI...`);
    try {
      const res = await api.post<{ generated_count: number }>('/ai/blueprints/fill-gaps', {
        exam_id: examId || undefined,
        rules: getRules(),
      });
      toast.success(`Generated ${res.generated_count} missing questions using AI! Re-checking availability...`);
      handleCheckAvailability();
    } catch (err: any) {
      toast.error(err.message || 'AI Gap Filling failed');
    } finally {
      setFilling(false);
    }
  };

  // Step 3: Final Exam Assembly into PostgreSQL
  const handleAssembleExam = async () => {
    if (!examId) {
      toast.error('Please select an Exam target');
      return;
    }
    setAssembling(true);
    toast.info('Assembling blueprint questions into Exam...');
    try {
      const res = await api.post<{ assembled_count: number }>('/ai/blueprints/assemble-exam', {
        exam_id: examId,
        rules: getRules(),
      });
      toast.success(`Successfully assembled ${res.assembled_count} questions into Exam!`);
    } catch (err: any) {
      toast.error(err.message || 'Assembly failed');
    } finally {
      setAssembling(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Exam Blueprint Builder & AI Gap Filling"
        description="Define exam distribution rules, check Question Bank availability, fill missing gaps with AI, and assemble exams."
      />

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Blueprint Specifications Form */}
        <Card className="glass-card lg:col-span-5">
          <CardHeader>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <Layers className="h-5 w-5 text-primary" /> Blueprint Specifications
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-xs">
            <div className="space-y-2">
              <Label>Target Exam Schedule *</Label>
              <Select value={examId} onValueChange={setExamId}>
                <SelectTrigger className="glass-input"><SelectValue placeholder="Select Exam Schedule" /></SelectTrigger>
                <SelectContent className="glass-modal">
                  {exams.map((e) => <SelectItem key={e.id} value={e.id}>{e.title}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Topic / Subject Scope</Label>
              <Input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Topic scope" className="glass-input" />
            </div>

            <div className="space-y-3 pt-2 border-t border-border/40">
              <h4 className="font-semibold text-foreground">Difficulty & Bloom Distribution Rules</h4>

              <div className="grid grid-cols-3 gap-2 items-center">
                <span className="font-bold text-emerald-600">Easy (Remember)</span>
                <Input type="number" value={easyCount} onChange={(e) => setEasyCount(parseInt(e.target.value) || 0)} className="glass-input col-span-2" />
              </div>

              <div className="grid grid-cols-3 gap-2 items-center">
                <span className="font-bold text-amber-600">Medium (Apply)</span>
                <Input type="number" value={medCount} onChange={(e) => setMedCount(parseInt(e.target.value) || 0)} className="glass-input col-span-2" />
              </div>

              <div className="grid grid-cols-3 gap-2 items-center">
                <span className="font-bold text-rose-600">Hard (Analyze)</span>
                <Input type="number" value={hardCount} onChange={(e) => setHardCount(parseInt(e.target.value) || 0)} className="glass-input col-span-2" />
              </div>
            </div>

            <Button className="w-full glass-button" disabled={checking} onClick={handleCheckAvailability}>
              {checking ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <BookOpen className="h-4 w-4 mr-2 text-primary" />}
              Check Question Bank Availability
            </Button>
          </CardContent>
        </Card>

        {/* Availability & Assembly Results */}
        <Card className="glass-card lg:col-span-7">
          <CardHeader>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <FileCheck className="h-5 w-5 text-emerald-600" /> Availability & Gap Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6 text-xs">
            {!availability ? (
              <div className="p-12 text-center text-muted-foreground italic flex flex-col items-center gap-2">
                <Layers className="h-8 w-8 text-muted-foreground/40" />
                <p>Configure blueprint rules on the left and click "Check Question Bank Availability".</p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div className="p-3 bg-muted/50 rounded-xl">
                    <div className="text-xl font-bold">{availability.total_requested}</div>
                    <div className="text-[10px] text-muted-foreground">Total Required</div>
                  </div>
                  <div className="p-3 bg-emerald-50/80 text-emerald-800 rounded-xl">
                    <div className="text-xl font-bold">{availability.total_available}</div>
                    <div className="text-[10px]">Available in DB</div>
                  </div>
                  <div className="p-3 bg-amber-50/80 text-amber-800 rounded-xl">
                    <div className="text-xl font-bold">{availability.total_gap}</div>
                    <div className="text-[10px]">Missing Gaps</div>
                  </div>
                </div>

                <Table>
                  <TableHeader>
                    <TableRow className="border-b border-border/50">
                      <TableHead>Difficulty / Rule</TableHead>
                      <TableHead>Requested</TableHead>
                      <TableHead>Available</TableHead>
                      <TableHead>Gap</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {availability.rules_availability.map((r, idx) => (
                      <TableRow key={idx} className="border-b border-border/40">
                        <TableCell className="font-semibold uppercase">{r.difficulty} ({r.bloom_level})</TableCell>
                        <TableCell>{r.requested}</TableCell>
                        <TableCell className="text-emerald-600 font-bold">{r.available}</TableCell>
                        <TableCell className={r.gap > 0 ? 'text-amber-600 font-bold' : 'text-muted-foreground'}>
                          {r.gap > 0 ? `${r.gap} missing` : 'Satisfied'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                <div className="flex gap-4 pt-2">
                  {availability.total_gap > 0 ? (
                    <Button
                      className="flex-1 glass-button bg-amber-500 hover:bg-amber-600 text-white"
                      disabled={filling}
                      onClick={handleFillGaps}
                    >
                      {filling ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
                      Generate {availability.total_gap} Missing Questions with AI
                    </Button>
                  ) : null}

                  <Button
                    className="flex-1 glass-button bg-emerald-600 hover:bg-emerald-700 text-white"
                    disabled={assembling || availability.total_available === 0}
                    onClick={handleAssembleExam}
                  >
                    {assembling ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <CheckCircle2 className="h-4 w-4 mr-2" />}
                    Assemble Exam Questions into DB
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
