'use client';

import { useState } from 'react';
import {
  BookOpen, Search, Filter, Plus, MoreHorizontal, Eye, Edit, Trash2, History,
  CheckCircle2, AlertCircle, FileText, Loader2, Sparkles, FolderKanban
} from 'lucide-react';
import {
  Card, CardContent, Button, Input, Badge, Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Label, Textarea
} from '@examshield/ui';
import { PageHeader } from '@/components/page-header';
import { EmptyState } from '@/components/empty-state';
import { DataTablePagination } from '@/components/data-table-pagination';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { toast } from 'sonner';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import type { Paginated } from '@examshield/types';

interface QuestionVersionItem {
  version: number;
  changeSummary?: str;
  createdAt: string;
}

interface QuestionRow {
  id: string;
  type: string;
  text: string;
  options: string[] | null;
  correctAnswers: string[];
  explanation: string | null;
  difficulty: string;
  bloomLevel: string | null;
  marks: number;
  topic: string | null;
  subjectId: string | null;
  isVerified: boolean;
  isAiGenerated: boolean;
  version: number;
  versions?: QuestionVersionItem[];
  createdAt: string;
}

const questionSchema = z.object({
  type: z.string(),
  text: z.string().min(1, 'Question text required'),
  options: z.array(z.string()).optional(),
  correctAnswers: z.array(z.string()).min(1, 'At least one correct answer required'),
  explanation: z.string().optional(),
  difficulty: z.string(),
  marks: z.number().min(1).default(1),
  topic: z.string().optional(),
  subjectId: z.string().optional(),
  isVerified: z.boolean().default(true),
});
type QuestionForm = z.infer<typeof questionSchema>;

function CreateQuestionDialog({ onCreated }: { onCreated: () => void }) {
  const api = useApiClient();
  const [open, setOpen] = useState(false);
  const [optA, setOptA] = useState('');
  const [optB, setOptB] = useState('');
  const [optC, setOptC] = useState('');
  const [optD, setOptD] = useState('');
  const [correctAns, setCorrectAns] = useState('A');

  const { register, handleSubmit, control, reset, formState: { errors } } = useForm<QuestionForm>({
    resolver: zodResolver(questionSchema),
    defaultValues: {
      type: 'mcq',
      difficulty: 'medium',
      marks: 1,
      isVerified: true,
      correctAnswers: ['A'],
    },
  });

  const { data: subjects } = useQuery<{ id: string; name: string }[]>({
    queryKey: ['subjects'],
    queryFn: () => api.get<{ id: string; name: string }[]>('/question-bank/subjects'),
  });

  const mutation = useMutation({
    mutationFn: (values: QuestionForm) => {
      const payload = {
        ...values,
        options: [optA, optB, optC, optD].filter(Boolean),
        correctAnswers: [correctAns],
      };
      return api.post('/questions', payload);
    },
    onSuccess: () => {
      toast.success('Question added to database');
      setOpen(false);
      reset();
      onCreated();
    },
    onError: (e: Error) => toast.error(e.message || 'Failed to create question'),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" className="glass-button"><Plus className="h-4 w-4 mr-1" /> Add Question</Button>
      </DialogTrigger>
      <DialogContent className="glass-modal max-h-[90vh] overflow-y-auto max-w-xl">
        <DialogHeader>
          <DialogTitle>Add New Question</DialogTitle>
          <DialogDescription>Create a single question record in PostgreSQL Question Bank.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit((v) => mutation.mutate(v))} className="space-y-4 text-xs">
          <div className="space-y-2">
            <Label>Question Text *</Label>
            <Textarea {...register('text')} placeholder="Enter full question text..." rows={3} className="glass-input" />
            {errors.text && <p className="text-destructive">{errors.text.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Question Type</Label>
              <Controller
                name="type"
                control={control}
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger className="glass-input"><SelectValue /></SelectTrigger>
                    <SelectContent className="glass-modal">
                      <SelectItem value="mcq">MCQ (Single Choice)</SelectItem>
                      <SelectItem value="multi_select">Multi Select</SelectItem>
                      <SelectItem value="true_false">True / False</SelectItem>
                      <SelectItem value="fill_blank">Fill in the Blank</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
            <div className="space-y-2">
              <Label>Difficulty</Label>
              <Controller
                name="difficulty"
                control={control}
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger className="glass-input"><SelectValue /></SelectTrigger>
                    <SelectContent className="glass-modal">
                      <SelectItem value="easy">Easy</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="hard">Hard</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div><Label>Option A</Label><Input value={optA} onChange={(e) => setOptA(e.target.value)} placeholder="Option A text" className="glass-input" /></div>
            <div><Label>Option B</Label><Input value={optB} onChange={(e) => setOptB(e.target.value)} placeholder="Option B text" className="glass-input" /></div>
            <div><Label>Option C</Label><Input value={optC} onChange={(e) => setOptC(e.target.value)} placeholder="Option C text" className="glass-input" /></div>
            <div><Label>Option D</Label><Input value={optD} onChange={(e) => setOptD(e.target.value)} placeholder="Option D text" className="glass-input" /></div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Correct Option</Label>
              <Select value={correctAns} onValueChange={setCorrectAns}>
                <SelectTrigger className="glass-input"><SelectValue /></SelectTrigger>
                <SelectContent className="glass-modal">
                  <SelectItem value="A">Option A</SelectItem>
                  <SelectItem value="B">Option B</SelectItem>
                  <SelectItem value="C">Option C</SelectItem>
                  <SelectItem value="D">Option D</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Marks</Label>
              <Input type="number" {...register('marks', { valueAsNumber: true })} defaultValue={1} className="glass-input" />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Explanation / Solution</Label>
            <Textarea {...register('explanation')} placeholder="Optional solution explanation..." rows={2} className="glass-input" />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
              {mutation.isPending ? 'Saving...' : 'Save Question'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function QuestionBankPage() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [diffFilter, setDiffFilter] = useState('');
  const [subjectFilter, setSubjectFilter] = useState('');

  const [viewQuestion, setViewQuestion] = useState<QuestionRow | null>(null);

  const params: Record<string, unknown> = { page, page_size: 20 };
  if (search) params.search = search;
  if (typeFilter && typeFilter !== 'all') params.question_type = typeFilter;
  if (diffFilter && diffFilter !== 'all') params.difficulty = diffFilter;
  if (subjectFilter && subjectFilter !== 'all') params.subject_id = subjectFilter;

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['questions', params],
    queryFn: () => api.get<Paginated<QuestionRow>>('/questions', params),
  });

  const { data: subjects } = useQuery<{ id: string; name: string }[]>({
    queryKey: ['subjects'],
    queryFn: () => api.get<{ id: string; name: string }[]>('/question-bank/subjects'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/questions/${id}`),
    onSuccess: () => {
      toast.success('Question deleted from Question Bank');
      queryClient.invalidateQueries({ queryKey: ['questions'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Question Bank Directory" description="Search, filter, edit, view question history, and manage exam repository questions.">
        <CreateQuestionDialog onCreated={refetch} />
      </PageHeader>

      <div className="flex flex-col gap-4 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9 glass-input"
            placeholder="Search by question text or keyword..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
        <Select value={typeFilter} onValueChange={(v) => { setTypeFilter(v); setPage(1); }}>
          <SelectTrigger className="w-[160px] glass-input"><SelectValue placeholder="All Question Types" /></SelectTrigger>
          <SelectContent className="glass-modal">
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="mcq">MCQ</SelectItem>
            <SelectItem value="true_false">True / False</SelectItem>
            <SelectItem value="fill_blank">Fill in Blank</SelectItem>
            <SelectItem value="paragraph">Paragraph</SelectItem>
          </SelectContent>
        </Select>
        <Select value={diffFilter} onValueChange={(v) => { setDiffFilter(v); setPage(1); }}>
          <SelectTrigger className="w-[140px] glass-input"><SelectValue placeholder="All Difficulties" /></SelectTrigger>
          <SelectContent className="glass-modal">
            <SelectItem value="all">All Difficulties</SelectItem>
            <SelectItem value="easy">Easy</SelectItem>
            <SelectItem value="medium">Medium</SelectItem>
            <SelectItem value="hard">Hard</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Card className="glass-card">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-muted-foreground flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-primary" /> Loading questions from PostgreSQL...
            </div>
          ) : !data?.items.length ? (
            <div className="p-8">
              <EmptyState
                title="No questions found in Question Bank"
                description="Click 'Add Question' or upload question files in the Question Repository."
                action={<CreateQuestionDialog onCreated={refetch} />}
              />
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow className="border-b border-border/50">
                    <TableHead>Question Text</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Difficulty</TableHead>
                    <TableHead>Marks</TableHead>
                    <TableHead>Version</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((q) => (
                    <TableRow key={q.id} className="border-b border-border/40 hover:bg-white/30 dark:hover:bg-slate-800/30">
                      <TableCell className="max-w-md font-medium text-xs">
                        <div className="line-clamp-2">{q.text}</div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="uppercase text-[10px]">{q.type}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="uppercase text-[10px]">{q.difficulty}</Badge>
                      </TableCell>
                      <TableCell className="font-semibold text-xs">{q.marks}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="font-mono text-[10px]">v{q.version || 1}</Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon"><MoreHorizontal className="h-4 w-4" /></Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="glass-modal">
                            <DropdownMenuItem onClick={() => setViewQuestion(q)}>
                              <Eye className="h-4 w-4 mr-2" /> View & History
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              className="text-destructive"
                              onClick={() => {
                                if (confirm("Are you sure you want to delete this question?")) {
                                  deleteMutation.mutate(q.id);
                                }
                              }}
                            >
                              <Trash2 className="h-4 w-4 mr-2" /> Delete Question
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="p-4">
                <DataTablePagination page={page} totalPages={data.totalPages} onPageChange={setPage} />
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* View Question Detail & Version History Dialog */}
      {viewQuestion && (
        <Dialog open={!!viewQuestion} onOpenChange={(b) => { if (!b) setViewQuestion(null); }}>
          <DialogContent className="glass-modal max-h-[90vh] overflow-y-auto max-w-xl">
            <DialogHeader>
              <DialogTitle className="flex items-center justify-between">
                <span>Question Detail</span>
                <Badge variant="outline">Version {viewQuestion.version || 1}</Badge>
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4 text-xs">
              <div className="p-3 bg-muted/50 rounded-xl space-y-1">
                <div className="font-semibold text-sm text-foreground">{viewQuestion.text}</div>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <span>Type: <strong className="uppercase">{viewQuestion.type}</strong></span> |
                  <span>Difficulty: <strong className="uppercase">{viewQuestion.difficulty}</strong></span> |
                  <span>Marks: <strong>{viewQuestion.marks}</strong></span>
                </div>
              </div>

              {viewQuestion.options && viewQuestion.options.length > 0 && (
                <div className="space-y-2">
                  <Label className="font-semibold">Options</Label>
                  <div className="grid grid-cols-2 gap-2">
                    {viewQuestion.options.map((opt, idx) => {
                      const letter = String.fromCharCode(65 + idx);
                      const isCorrect = viewQuestion.correctAnswers.includes(letter) || viewQuestion.correctAnswers.includes(opt);
                      return (
                        <div key={idx} className={`p-2 rounded-lg border ${isCorrect ? 'bg-emerald-50/80 border-emerald-300 text-emerald-800 font-bold' : 'bg-muted/40'}`}>
                          {letter}. {opt}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {viewQuestion.explanation && (
                <div className="p-3 bg-blue-50/60 border border-blue-200 rounded-xl text-blue-800">
                  <strong>Explanation:</strong> {viewQuestion.explanation}
                </div>
              )}

              {/* Version History Log */}
              <div className="space-y-2 pt-2 border-t border-border/50">
                <h4 className="font-semibold flex items-center gap-1">
                  <History className="h-4 w-4 text-primary" /> Question Version History
                </h4>
                <div className="space-y-2 max-h-36 overflow-y-auto">
                  {viewQuestion.versions?.length ? (
                    viewQuestion.versions.map((ver, idx) => (
                      <div key={idx} className="p-2.5 border border-border/40 rounded-xl text-xs flex justify-between items-center bg-muted/20">
                        <div>
                          <div className="font-bold">Version {ver.version}</div>
                          <div className="text-muted-foreground">{ver.changeSummary || 'Updated profile'}</div>
                        </div>
                        <div className="text-[10px] text-muted-foreground">
                          {new Date(ver.createdAt).toLocaleDateString()}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-muted-foreground italic">Version 1 (Initial creation)</div>
                  )}
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setViewQuestion(null)}>Close</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}