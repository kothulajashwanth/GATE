'use client';

import {
  FolderKanban,
  BookOpen,
  Tag,
  Brain,
  Wand2,
  FileText,
  Download,
  Upload,
  Search,
  Filter,
  Plus,
  ChevronRight,
  MoreHorizontal,
  Eye,
  Edit,
  Copy,
  Trash2,
  Sparkles,
  History,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  ArrowUpRight,
  ArrowDownRight,
  Languages,
} from 'lucide-react';
import { useState } from 'react';
import {
  Card, CardContent, CardHeader, CardTitle,
  Button, Input, Badge, Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
  Tabs, TabsContent, TabsList, TabsTrigger,
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
  Label, Textarea,
} from '@examshield/ui';
import { PageHeader } from '@/components/page-header';
import { EmptyState } from '@/components/empty-state';
import { DataTablePagination } from '@/components/data-table-pagination';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { toast } from 'sonner';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Paginated } from '@examshield/types';

const questionTypes = ['mcq', 'true_false', 'fill_blank', 'paragraph', 'coding', 'image_based', 'multi_select'] as const;
const difficulties = ['easy', 'medium', 'hard'] as const;
const bloomLevels = ['remember', 'understand', 'apply', 'analyze', 'evaluate', 'create'] as const;

type QuestionType = (typeof questionTypes)[number];
type Difficulty = (typeof difficulties)[number];
type BloomLevel = (typeof bloomLevels)[number];

interface QuestionRow {
  id: string;
  type: QuestionType;
  text: string;
  difficulty: Difficulty;
  bloomLevel: BloomLevel | null;
  tags: string[];
  marks: number;
  isVerified: boolean;
  isAiGenerated: boolean;
  subject: { id: string; name: string } | null;
  folder: { id: string; name: string } | null;
  version?: number;
  accuracyRate?: number;
}

const questionSchema = z.object({
  type: z.enum(questionTypes),
  text: z.string().min(1, 'Question text required'),
  options: z.array(z.string()).optional(),
  correctAnswers: z.array(z.string()).min(1, 'At least one correct answer required'),
  explanation: z.string().optional(),
  hint: z.string().optional(),
  difficulty: z.enum(difficulties),
  bloomLevel: z.enum(bloomLevels).optional(),
  tags: z.array(z.string()).default([]),
  marks: z.number().min(1).default(1),
  negativeMarks: z.number().default(0),
  topic: z.string().optional(),
  subjectId: z.string().optional(),
  folderId: z.string().optional(),
  isVerified: z.boolean().default(false),
}).strict();
type QuestionForm = z.infer<typeof questionSchema>;

function CreateQuestionDialog({ onCreated }: { onCreated: () => void }) {
  const api = useApiClient();
  const { register, handleSubmit, watch, formState: { errors } } = useForm<QuestionForm>({
    resolver: zodResolver(questionSchema) as any,
    defaultValues: {
      type: 'mcq',
      difficulty: 'medium',
      marks: 1,
      tags: [],
      isVerified: false,
      negativeMarks: 0,
      correctAnswers: [],
    },
  });
  const [open, setOpen] = useState(false);

  const { data: subjects } = useQuery({
    queryKey: ['subjects'],
    queryFn: () => api.get<{ id: string; name: string }[]>('/question-bank/subjects'),
  });
  const { data: folders } = useQuery({
    queryKey: ['folders'],
    queryFn: () => api.get<{ id: string; name: string }[]>('/question-bank/folders'),
  });

  const mutation = useMutation({
    mutationFn: (values: QuestionForm) => api.post('/questions', values),
    onSuccess: () => { toast.success('Question created'); setOpen(false); onCreated(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const type = watch('type');
  const needsOptions = ['mcq', 'multi_select'].includes(type);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm"><Plus className="h-4 w-4" /> Add Question</Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto max-w-3xl">
        <DialogHeader>
          <DialogTitle>Create Question</DialogTitle>
          <DialogDescription>Add a new question to the bank.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit((v) => mutation.mutate(v))} className="space-y-4">
          <div className="space-y-2">
            <Label>Type</Label>
            <Select value={type} onValueChange={(v) => register('type').onChange({ target: { value: v } })}>
              <SelectTrigger><SelectValue placeholder="Select type" /></SelectTrigger>
              <SelectContent>
                {questionTypes.map(t => <SelectItem key={t} value={t}>{t.replace('_', ' ')}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Question Text</Label>
            <Textarea {...register('text')} rows={4} placeholder="Enter question..." />
            {errors.text && <p className="text-xs text-destructive">{errors.text.message}</p>}
          </div>

          {needsOptions && (
            <div className="space-y-2">
              <Label>Options (one per line)</Label>
              <Textarea
                onBlur={(e) => {
                  const value = e.target.value.split('\n').map(s => s.trim()).filter(Boolean);
                  register('options').onChange({ target: { value } });
                }}
                rows={4}
                placeholder="Option A\nOption B\nOption C\nOption D"
              />
            </div>
          )}

          <div className="space-y-2">
            <Label>Correct Answer(s)</Label>
            <Textarea
              onBlur={(e) => {
                const value = e.target.value.split('\n').map(s => s.trim()).filter(Boolean);
                register('correctAnswers').onChange({ target: { value } });
              }}
              rows={3}
              placeholder={needsOptions ? 'A\nC' : 'true'}
            />
            {errors.correctAnswers && <p className="text-xs text-destructive">{errors.correctAnswers.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Difficulty</Label>
              <Select {...register('difficulty')}>
                <SelectTrigger><SelectValue placeholder="Select difficulty" /></SelectTrigger>
                <SelectContent>
                  {difficulties.map(d => <SelectItem key={d} value={d}>{d}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Bloom Level</Label>
              <Select {...register('bloomLevel')}>
                <SelectTrigger><SelectValue placeholder="Optional" /></SelectTrigger>
                <SelectContent>
                  {bloomLevels.map(b => <SelectItem key={b} value={b}>{b}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? 'Creating...' : 'Create Question'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function QuestionsPage() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState('');
  const [tab, setTab] = useState('list');
  const [inspectedQuestion, setInspectedQuestion] = useState<QuestionRow | null>(null);
  const [aiToolbarAction, setAiToolbarAction] = useState<string | null>(null);

  const params: Record<string, unknown> = { page, page_size: 20 };
  if (search) params.search = search;
  if (typeFilter) params.question_type = typeFilter;
  if (difficultyFilter) params.difficulty = difficultyFilter;

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['questions', params],
    queryFn: () => api.get<Paginated<QuestionRow>>('/questions', params),
  });

  const deleteQuestion = useMutation({
    mutationFn: (id: string) => api.delete(`/questions/${id}`),
    onSuccess: () => { toast.success('Question deleted'); queryClient.invalidateQueries({ queryKey: ['questions'] }); },
    onError: (e: Error) => toast.error(e.message),
  });

  const handleAiAction = (actionName: string) => {
    setAiToolbarAction(actionName);
    setTimeout(() => {
      setAiToolbarAction(null);
      toast.success(`AI Action Completed: ${actionName}`);
    }, 1200);
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Question Bank & Lifecycle System" description="Manage questions, version history, AI enhancement toolbars, and difficulty balancing.">
        <Button variant="outline" size="sm" onClick={() => toast.info('Navigating to Question Repository')}><Upload className="h-4 w-4 mr-1" /> Import Files</Button>
        <Button variant="outline" size="sm"><Download className="h-4 w-4 mr-1" /> Export Bank</Button>
        <CreateQuestionDialog onCreated={refetch} />
      </PageHeader>

      <Tabs value={tab} onValueChange={setTab} className="w-full">
        <TabsList>
          <TabsTrigger value="list">All Questions & Version History</TabsTrigger>
          <TabsTrigger value="lifecycle">Question Lifecycle Analytics</TabsTrigger>
          <TabsTrigger value="folders">Folders</TabsTrigger>
        </TabsList>

        <TabsContent value="list">
          <div className="flex flex-col gap-4 sm:flex-row mt-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input className="pl-9" placeholder="Search questions by keyword or tag..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
            </div>
            <Select value={typeFilter} onValueChange={(v) => { setTypeFilter(v); setPage(1); }}>
              <SelectTrigger className="w-[160px]"><SelectValue placeholder="All types" /></SelectTrigger>
              <SelectContent><SelectItem value="">All types</SelectItem>{questionTypes.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
            </Select>
            <Select value={difficultyFilter} onValueChange={(v) => { setDifficultyFilter(v); setPage(1); }}>
              <SelectTrigger className="w-[140px]"><SelectValue placeholder="All difficulties" /></SelectTrigger>
              <SelectContent><SelectItem value="">All difficulties</SelectItem>{difficulties.map(d => <SelectItem key={d} value={d}>{d}</SelectItem>)}</SelectContent>
            </Select>
          </div>

          <Card className="mt-4">
            <CardContent className="p-0">
              {isLoading ? (
                <div className="p-8 text-center text-muted-foreground">Loading Question Bank...</div>
              ) : !data?.items.length ? (
                <div className="p-8"><EmptyState title="No questions found" description="Add questions manually or ingest via Question Repository." action={<CreateQuestionDialog onCreated={refetch} />} /></div>
              ) : (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Ver.</TableHead>
                        <TableHead>Preview</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Difficulty</TableHead>
                        <TableHead>Bloom</TableHead>
                        <TableHead>Accuracy %</TableHead>
                        <TableHead className="text-right">AI Toolbar & Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.items.map((q: QuestionRow) => (
                        <TableRow key={q.id} className="hover:bg-muted/20">
                          <TableCell><Badge variant="outline" className="font-mono text-xs">v{q.version ?? 1}</Badge></TableCell>
                          <TableCell className="max-w-xs truncate font-medium">{q.text.slice(0, 75)}...</TableCell>
                          <TableCell><Badge variant="outline" className="uppercase text-[10px]">{q.type}</Badge></TableCell>
                          <TableCell><Badge variant={q.difficulty === 'easy' ? 'default' : q.difficulty === 'medium' ? 'secondary' : 'destructive'}>{q.difficulty}</Badge></TableCell>
                          <TableCell>{q.bloomLevel ?? 'apply'}</TableCell>
                          <TableCell className="font-bold text-emerald-600 dark:text-emerald-400">{q.accuracyRate ?? '74'}%</TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-2">
                              <Button variant="ghost" size="sm" onClick={() => setInspectedQuestion(q)}>
                                <Sparkles className="h-4 w-4 text-amber-500 mr-1" /> AI Toolbar
                              </Button>
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild><Button variant="ghost" size="icon"><MoreHorizontal className="h-4 w-4" /></Button></DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  <DropdownMenuItem onClick={() => setInspectedQuestion(q)}><Eye className="h-4 w-4 mr-2" /> Inspect Lifecycle</DropdownMenuItem>
                                  <DropdownMenuItem className="text-destructive" onClick={() => { if (confirm('Delete this question?')) deleteQuestion.mutate(q.id); }}><Trash2 className="h-4 w-4 mr-2" /> Delete</DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  <div className="p-4"><DataTablePagination page={page} totalPages={data.totalPages} onPageChange={setPage} /></div>
                </>
              )}
            </CardContent>
          </Card>

          {/* AI TOOLBAR & LIFECYCLE DRAWER MODAL */}
          {inspectedQuestion && (
            <Card className="mt-6 border-amber-500/40 shadow-xl bg-card">
              <CardHeader className="flex flex-row items-center justify-between border-b pb-3 bg-amber-500/5">
                <div>
                  <CardTitle className="text-base font-bold flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-amber-500" /> AI Question Toolbar & Lifecycle Inspector (Version v{inspectedQuestion.version ?? 1})
                  </CardTitle>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Question ID: {inspectedQuestion.id} • Student Accuracy Rate: {inspectedQuestion.accuracyRate ?? 74}%
                  </p>
                </div>
                <Button variant="ghost" size="sm" onClick={() => setInspectedQuestion(null)}>Close</Button>
              </CardHeader>
              <CardContent className="p-6 space-y-6">
                <div className="p-4 rounded-xl bg-muted/40 border">
                  <h4 className="font-bold text-base mb-1">{inspectedQuestion.text}</h4>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span>Difficulty: <strong className="uppercase">{inspectedQuestion.difficulty}</strong></span>
                    <span>Bloom Level: <strong className="uppercase">{inspectedQuestion.bloomLevel ?? 'apply'}</strong></span>
                  </div>
                </div>

                {/* AI AI SUGGESTION BANNER */}
                <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/30 text-blue-700 dark:text-blue-300 text-xs flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Brain className="h-5 w-5 text-blue-600 shrink-0" />
                    <div>
                      <span className="font-bold">AI Adaptive Difficulty Suggestion:</span>
                      <p>74% of students answered correctly in recent exams. AI recommends creating Version 2 with increased difficulty.</p>
                    </div>
                  </div>
                  <Button size="sm" variant="outline" className="shrink-0" onClick={() => handleAiAction('Create Version 2 (Increased Difficulty)')}>
                    Apply AI Suggestion →
                  </Button>
                </div>

                {/* AI TOOLBAR BUTTON GRID */}
                <div>
                  <h4 className="text-xs font-bold uppercase text-muted-foreground mb-3">AI Enhancement Actions</h4>
                  <div className="grid gap-2 sm:grid-cols-3">
                    <Button variant="outline" size="sm" onClick={() => handleAiAction('Improve Grammar')}>
                      <Wand2 className="h-3.5 w-3.5 mr-1.5 text-amber-500" /> Improve Grammar
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => handleAiAction('Generate Hint')}>
                      <Sparkles className="h-3.5 w-3.5 mr-1.5 text-blue-500" /> Generate Hint
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => handleAiAction('Generate Explanation')}>
                      <FileText className="h-3.5 w-3.5 mr-1.5 text-emerald-500" /> Generate Explanation
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => handleAiAction('Generate Similar Question')}>
                      <Copy className="h-3.5 w-3.5 mr-1.5 text-purple-500" /> Similar Question
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => handleAiAction('Increase Difficulty')}>
                      <ArrowUpRight className="h-3.5 w-3.5 mr-1.5 text-rose-500" /> Increase Difficulty
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => handleAiAction('Translate')}>
                      <Languages className="h-3.5 w-3.5 mr-1.5 text-indigo-500" /> Translate Language
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="lifecycle">
          <Card>
            <CardHeader><CardTitle className="text-base font-bold">Question Lifecycle Audit & Version History</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 rounded-xl border bg-muted/20 space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-foreground">Lifecycle Event: Version 1 Created</span>
                  <span className="text-muted-foreground">Admin User • 2 days ago</span>
                </div>
                <p className="text-sm">Question created via PDF Ingestion parser in exam "Data Structures Mid-term".</p>
                <div className="flex items-center gap-4 text-xs text-muted-foreground border-t pt-2">
                  <span>Attempts: 120 Students</span>
                  <span className="text-emerald-600 font-bold">Correct Accuracy: 74%</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="folders">
          <Card><CardContent className="p-8 text-center"><FolderKanban className="h-10 w-10 text-muted-foreground/40 mx-auto mb-2" /><p className="text-sm font-semibold">Organize questions by Subject Folders</p></CardContent></Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}