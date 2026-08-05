import { FolderKanban, BookOpen, Tag, Brain, Wand2, FileText, Download, Upload, Search, Filter, Plus, ChevronRight, MoreHorizontal, Eye, Edit, Copy, Trash2 } from 'lucide-react';
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
  marks: z.number().default(1).min(1),
  negativeMarks: z.number().default(0),
  topic: z.string().optional(),
  subjectId: z.string().optional(),
  folderId: z.string().optional(),
  isVerified: z.boolean().default(false),
});
type QuestionForm = z.infer<typeof questionSchema>;

function CreateQuestionDialog({ onCreated }: { onCreated: () => void }) {
  const api = useApiClient();
  const { register, handleSubmit, watch, formState: { errors } } = useForm<QuestionForm>({
    resolver: zodResolver(questionSchema),
    defaultValues: { type: 'mcq', difficulty: 'medium', marks: 1, tags: [], isVerified: false },
  });
  const [open, setOpen] = useState(false);

  const { data: subjects } = useQuery({ queryKey: ['subjects'], queryFn: () => api.get('/subjects') });
  const { data: folders } = useQuery({ queryKey: ['folders'], queryFn: () => api.get('/question-bank-folders') });

  const mutation = useMutation({
    mutationFn: (values: QuestionForm) => api.post('/questions', values),
    onSuccess: () => { toast.success('Question created'); setOpen(false); onCreated(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const type = watch('type');
  const needsOptions = ['mcq', 'multi_select'].includes(type);
  const options = watch('options');

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
                {...register('options', { valueAsArray: (v) => v.split('\n').map(s => s.trim()).filter(Boolean) })}
                rows={4}
                placeholder="Option A\nOption B\nOption C\nOption D"
              />
            </div>
          )}

          <div className="space-y-2">
            <Label>Correct Answer(s)</Label>
            <Textarea
              {...register('correctAnswers', { valueAsArray: (v) => v.split('\n').map(s => s.trim()).filter(Boolean) })}
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
            <div className="space-y-2">
              <Label>Marks</Label>
              <Input type="number" {...register('marks', { valueAsNumber: true })} min="1" />
            </div>
            <div className="space-y-2">
              <Label>Subject</Label>
              <Select {...register('subjectId')}>
                <SelectTrigger><SelectValue placeholder="Optional" /></SelectTrigger>
                <SelectContent>
                  {subjects?.map(s => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Folder</Label>
              <Select {...register('folderId')}>
                <SelectTrigger><SelectValue placeholder="Optional" /></SelectTrigger>
                <SelectContent>
                  {folders?.map(f => <SelectItem key={f.id} value={f.id}>{f.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Tags (comma-separated)</Label>
            <Input {...register('tags', { valueAsArray: (v) => v.split(',').map(s => s.trim()).filter(Boolean) })} placeholder="arrays, sorting, easy" />
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

  const params: Record<string, unknown> = { page, page_size: 20 };
  if (search) params.search = search;
  if (typeFilter) params.question_type = typeFilter;
  if (difficultyFilter) params.difficulty = difficultyFilter;

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['questions', params],
    queryFn: () => api.get('/questions', params),
  });

  const deleteQuestion = useMutation({
    mutationFn: (id: string) => api.delete(`/questions/${id}`),
    onSuccess: () => { toast.success('Question deleted'); queryClient.invalidateQueries({ queryKey: ['questions'] }); },
    onError: (e: Error) => toast.error(e.message),
  });

  const handleImport = async () => {
    toast.info('Import coming soon...');
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Question Bank" description="Manage questions, folders, and AI-powered generation">
        <Button variant="outline" size="sm" onClick={handleImport}><Upload className="h-4 w-4" /> Import</Button>
        <Button variant="outline" size="sm"><Download className="h-4 w-4" /> Export</Button>
        <CreateQuestionDialog onCreated={refetch} />
      </PageHeader>

      <Tabs value={tab} onValueChange={setTab} className="w-full">
        <TabsList>
          <TabsTrigger value="list">All Questions</TabsTrigger>
          <TabsTrigger value="folders">Folders</TabsTrigger>
          <TabsTrigger value="subjects">Subjects</TabsTrigger>
        </TabsList>

        <TabsContent value="list">
          <div className="flex flex-col gap-4 sm:flex-row mt-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input className="pl-9" placeholder="Search questions..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} onKeyDown={(e) => { if (e.key === 'Enter') refetch(); }} />
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

          <Card>
            <CardContent className="p-0">
              {isLoading ? (
                <div className="p-8 text-center text-muted-foreground">Loading...</div>
              ) : !data?.items.length ? (
                <div className="p-8"><EmptyState title="No questions" description="Add questions manually or import from file." action={<CreateQuestionDialog onCreated={refetch} />} /></div>
              ) : (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Preview</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Difficulty</TableHead>
                        <TableHead>Bloom</TableHead>
                        <TableHead>Subject</TableHead>
                        <TableHead>Tags</TableHead>
                        <TableHead>Marks</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.items.map((q: QuestionRow) => (
                        <TableRow key={q.id}>
                          <TableCell className="max-w-xs truncate">{q.text.slice(0, 80)}...</TableCell>
                          <TableCell><Badge variant="outline">{q.type}</Badge></TableCell>
                          <TableCell><Badge variant={q.difficulty === 'easy' ? 'success' : q.difficulty === 'medium' ? 'warning' : 'destructive'}>{q.difficulty}</Badge></TableCell>
                          <TableCell>{q.bloomLevel ?? '—'}</TableCell>
                          <TableCell>{q.subject?.name ?? '—'}</TableCell>
                          <TableCell className="max-w-[200px] truncate">{q.tags.join(', ') || '—'}</TableCell>
                          <TableCell>{q.marks}</TableCell>
                          <TableCell className="text-right">
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild><Button variant="ghost" size="icon"><MoreHorizontal className="h-4 w-4" /></Button></DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem><Eye className="h-4 w-4 mr-2" /> View</DropdownMenuItem>
                                <DropdownMenuItem><Edit className="h-4 w-4 mr-2" /> Edit</DropdownMenuItem>
                                <DropdownMenuItem><Copy className="h-4 w-4 mr-2" /> Duplicate</DropdownMenuItem>
                                <DropdownMenuItem className="text-destructive" onClick={() => { if (confirm('Delete this question?')) deleteQuestion.mutate(q.id); }}><Trash2 className="h-4 w-4 mr-2" /> Delete</DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
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
        </TabsContent>

        <TabsContent value="folders">
          <Card><CardContent className="p-8 text-center">
            <FolderKanban className="h-12 w-12 mx-auto text-muted-foreground/50 mb-3" />
            <h3 className="text-lg font-semibold">Folder Management</h3>
            <p className="text-muted-foreground mt-1">Create and organize question folders coming soon.</p>
          </CardContent></Card>
        </TabsContent>

        <TabsContent value="subjects">
          <Card><CardContent className="p-8 text-center">
            <BookOpen className="h-12 w-12 mx-auto text-muted-foreground/50 mb-3" />
            <h3 className="text-lg font-semibold">Subject Management</h3>
            <p className="text-muted-foreground mt-1">Define subjects, codes, and department mappings.</p>
          </CardContent></Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}