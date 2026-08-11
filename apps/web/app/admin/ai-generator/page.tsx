'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import {
  Card, CardContent, CardHeader, CardTitle, Button, Badge, Input, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Label, Textarea,
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@examshield/ui';
import {
  Sparkles, Check, RefreshCw, Layers, BookOpen, Brain, Zap, CheckCircle2, ArrowRight, Loader2, AlertTriangle, Edit3, Trash2, ShieldCheck, FileText, CheckCheck, FileSpreadsheet
} from 'lucide-react';
import { toast } from 'sonner';

interface AIQuestionItem {
  type: str;
  text: str;
  options?: str[] | null;
  correct_answers: str[];
  explanation?: str | null;
  difficulty: str;
  bloom_level?: str | null;
  marks: number;
  negative_marks: number;
  topic?: str | null;
  subject_id?: str | null;
  is_duplicate?: boolean;
  status: str;
}

export default function AiGeneratorPage() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  const [prompt, setPrompt] = useState('Generate conceptual and problem-solving questions on Computer Networks and OSI Model.');
  const [subjectId, setSubjectId] = useState('');
  const [topic, setTopic] = useState('OSI Layer & TCP/IP');
  const [questionType, setQuestionType] = useState('mcq');
  const [count, setCount] = useState(5);
  const [difficulty, setDifficulty] = useState('medium');
  const [bloomLevel, setBloomLevel] = useState('apply');
  const [sourceFileId, setSourceFileId] = useState('');

  const [isGenerating, setIsGenerating] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [generatedList, setGeneratedList] = useState<AIQuestionItem[]>([]);

  // Edit Question State
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editQuestion, setEditQuestion] = useState<AIQuestionItem | null>(null);

  const { data: subjects = [] } = useQuery<{ id: string; name: string }[]>({
    queryKey: ['subjects'],
    queryFn: () => api.get<{ id: string; name: string }[]>('/question-bank/subjects'),
  });

  const { data: files = [] } = useQuery<{ id: string; originalName: string }[]>({
    queryKey: ['uploaded-files'],
    queryFn: () => api.get<{ id: string; originalName: string }[]>('/question-bank/files'),
  });

  // Call Real Backend AI Generator Endpoint
  const handleGenerate = async () => {
    if (!prompt.trim()) {
      toast.error('Please enter a generation prompt');
      return;
    }

    setIsGenerating(true);
    toast.info('Sending structured prompt to AI Provider...');

    try {
      const payload = {
        prompt,
        count,
        difficulty,
        question_type: questionType,
        topic,
        subject_id: subjectId || undefined,
        bloom_level: bloomLevel,
        source_file_id: sourceFileId || undefined,
      };

      const res = await api.post<AIQuestionItem[]>('/ai/generate-questions', payload);
      setGeneratedList(res);
      toast.success(`Generated ${res.length} structured questions with Bloom & Difficulty classifications!`);
    } catch (err: any) {
      toast.error(err.message || 'AI Question Generation failed');
    } finally {
      setIsGenerating(false);
    }
  };

  // Single Question Regeneration
  const handleRegenerateItem = async (index: number) => {
    const target = generatedList[index];
    if (!target) return;
    toast.info(`Regenerating question #${index + 1}...`);

    try {
      const res = await api.post<AIQuestionItem>('/ai/improve-question', {
        question: target,
        instruction: 'Improve distractors and question clarity',
      });
      const updated = [...generatedList];
      updated[index] = res;
      setGeneratedList(updated);
      toast.success('Question regenerated');
    } catch (err: any) {
      toast.error(err.message || 'Regeneration failed');
    }
  };

  // Single Question Removal
  const handleRemoveItem = (index: number) => {
    const updated = generatedList.filter((_, idx) => idx !== index);
    setGeneratedList(updated);
    toast.info('Question removed from review queue');
  };

  // Bulk Approve into PostgreSQL Question Bank
  const handleApproveAll = async () => {
    if (!generatedList.length) return;
    setIsApproving(true);
    toast.info('Saving approved AI questions into PostgreSQL Question Bank...');

    try {
      const payload = {
        questions: generatedList.map((q) => ({
          type: q.type,
          text: q.text,
          options: q.options || undefined,
          correctAnswers: q.correct_answers,
          explanation: q.explanation || undefined,
          difficulty: q.difficulty,
          bloomLevel: q.bloom_level || undefined,
          marks: q.marks,
          negativeMarks: q.negative_marks,
          topic: q.topic || topic,
          subjectId: q.subject_id || subjectId || undefined,
        })),
      };

      const res = await api.post<{ approved_count: number }>('/ai/questions/approve', payload);
      toast.success(`Approved ${res.approved_count} AI questions into PostgreSQL Question Bank!`);
      setGeneratedList([]);
      queryClient.invalidateQueries({ queryKey: ['questions'] });
    } catch (err: any) {
      toast.error(err.message || 'Approval failed');
    } finally {
      setIsApproving(false);
    }
  };

  // Save Edit Question
  const handleSaveEdit = () => {
    if (editingIndex === null || !editQuestion) return;
    const updated = [...generatedList];
    updated[editingIndex] = editQuestion;
    setGeneratedList(updated);
    setEditingIndex(null);
    setEditQuestion(null);
    toast.success('Question updated in review queue');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Question Generator & Quality Review"
        description="Prompt-driven AI question generation, Bloom's taxonomy classification, difficulty tuning, duplicate detection, and human approval workflow."
      />

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left Generation Controls Panel */}
        <Card className="glass-card lg:col-span-5 border border-white/20 dark:border-white/10">
          <CardHeader>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <Brain className="h-5 w-5 text-primary" /> Generation Parameters
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-xs">
            <div className="space-y-2">
              <Label>Generation Prompt / Instructions *</Label>
              <Textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Enter prompt instructions for AI question authoring..."
                rows={3}
                className="glass-input"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Subject</Label>
                <Select value={subjectId} onValueChange={setSubjectId}>
                  <SelectTrigger className="glass-input"><SelectValue placeholder="Select Subject" /></SelectTrigger>
                  <SelectContent className="glass-modal">
                    <SelectItem value="none">General / Unassigned</SelectItem>
                    {subjects.map((s) => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Topic / Subtopic</Label>
                <Input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Topic name" className="glass-input" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Question Type</Label>
                <Select value={questionType} onValueChange={setQuestionType}>
                  <SelectTrigger className="glass-input"><SelectValue /></SelectTrigger>
                  <SelectContent className="glass-modal">
                    <SelectItem value="mcq">MCQ (Single Choice)</SelectItem>
                    <SelectItem value="multi_select">Multi Select</SelectItem>
                    <SelectItem value="true_false">True / False</SelectItem>
                    <SelectItem value="fill_blank">Fill in the Blank</SelectItem>
                    <SelectItem value="paragraph">Paragraph / Descriptive</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Question Count</Label>
                <Input
                  type="number"
                  value={count}
                  onChange={(e) => setCount(Math.max(1, Math.min(20, parseInt(e.target.value) || 1)))}
                  className="glass-input"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Target Difficulty</Label>
                <Select value={difficulty} onValueChange={setDifficulty}>
                  <SelectTrigger className="glass-input"><SelectValue /></SelectTrigger>
                  <SelectContent className="glass-modal">
                    <SelectItem value="easy">Easy</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="hard">Hard</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Bloom's Taxonomy Level</Label>
                <Select value={bloomLevel} onValueChange={setBloomLevel}>
                  <SelectTrigger className="glass-input"><SelectValue /></SelectTrigger>
                  <SelectContent className="glass-modal">
                    <SelectItem value="remember">1. Remember (Recall)</SelectItem>
                    <SelectItem value="understand">2. Understand (Explain)</SelectItem>
                    <SelectItem value="apply">3. Apply (Execute)</SelectItem>
                    <SelectItem value="analyze">4. Analyze (Differentiate)</SelectItem>
                    <SelectItem value="evaluate">5. Evaluate (Judge)</SelectItem>
                    <SelectItem value="create">6. Create (Design)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Source Document Grounding (Optional)</Label>
              <Select value={sourceFileId} onValueChange={setSourceFileId}>
                <SelectTrigger className="glass-input"><SelectValue placeholder="No Document Grounding" /></SelectTrigger>
                <SelectContent className="glass-modal">
                  <SelectItem value="none">No Document Grounding</SelectItem>
                  {files.map((f) => <SelectItem key={f.id} value={f.id}>{f.originalName}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>

            <Button
              className="w-full glass-button bg-primary text-white shadow-md mt-2"
              disabled={isGenerating}
              onClick={handleGenerate}
            >
              {isGenerating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2 text-amber-300" />}
              {isGenerating ? 'Generating Questions...' : 'Generate Questions with AI'}
            </Button>
          </CardContent>
        </Card>

        {/* Right Generated Review Queue Panel */}
        <Card className="glass-card lg:col-span-7 border border-white/20 dark:border-white/10">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <Layers className="h-5 w-5 text-amber-500" /> Review Queue ({generatedList.length})
            </CardTitle>
            {generatedList.length > 0 && (
              <Button
                size="sm"
                className="glass-button bg-emerald-600 hover:bg-emerald-700 text-white"
                disabled={isApproving}
                onClick={handleApproveAll}
              >
                {isApproving ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <CheckCheck className="h-4 w-4 mr-1" />}
                Approve & Save All to DB
              </Button>
            )}
          </CardHeader>

          <CardContent className="space-y-4">
            {isGenerating ? (
              <div className="p-12 text-center text-xs text-muted-foreground flex flex-col items-center justify-center gap-3">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p>Generating structured questions with Bloom's taxonomy & checking PostgreSQL catalog for duplicates...</p>
              </div>
            ) : !generatedList.length ? (
              <div className="p-12 text-center text-xs text-muted-foreground flex flex-col items-center justify-center gap-3">
                <BookOpen className="h-10 w-10 text-muted-foreground/40" />
                <p>No questions in review queue. Configure parameters on the left and click "Generate Questions with AI".</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
                {generatedList.map((q, idx) => (
                  <Card key={idx} className="glass-card p-4 text-xs space-y-2 relative border border-white/20 dark:border-white/10">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-bold text-foreground">#{idx + 1}</span>
                        <Badge variant="outline" className="uppercase text-[10px]">{q.type}</Badge>
                        <Badge variant="secondary" className="uppercase text-[10px]">{q.difficulty}</Badge>
                        <Badge variant="outline" className="text-[10px] bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300">
                          Bloom: {q.bloom_level || 'apply'}
                        </Badge>
                        {q.is_duplicate && (
                          <Badge variant="destructive" className="flex items-center gap-1 text-[10px]">
                            <AlertTriangle className="h-3 w-3" /> Duplicate Warning
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        <Button size="sm" variant="ghost" onClick={() => { setEditingIndex(idx); setEditQuestion({ ...q }); }}>
                          <Edit3 className="h-3.5 w-3.5 mr-1" /> Edit
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => handleRegenerateItem(idx)}>
                          <RefreshCw className="h-3.5 w-3.5 mr-1" /> Regenerate
                        </Button>
                        <Button size="sm" variant="ghost" className="text-destructive hover:bg-rose-50" onClick={() => handleRemoveItem(idx)}>
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>

                    <p className="font-semibold text-sm text-foreground">{q.text}</p>

                    {q.options && q.options.length > 0 && (
                      <div className="grid grid-cols-2 gap-2 pt-1 pl-2">
                        {q.options.map((opt, oIdx) => {
                          const letter = String.fromCharCode(65 + oIdx);
                          const isCorrect = q.correct_answers.includes(letter) || q.correct_answers.includes(opt);
                          return (
                            <div key={oIdx} className={`p-2 rounded-lg border text-xs ${isCorrect ? 'bg-emerald-50/80 border-emerald-300 font-bold text-emerald-800' : 'bg-muted/40'}`}>
                              <span className="font-bold mr-1">{letter}.</span> {opt}
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {q.explanation && (
                      <p className="text-[11px] text-muted-foreground italic border-t border-border/40 pt-1">
                        <strong>Explanation:</strong> {q.explanation}
                      </p>
                    )}
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Edit Question Dialog */}
      {editQuestion && (
        <Dialog open={editingIndex !== null} onOpenChange={(b) => { if (!b) setEditingIndex(null); }}>
          <DialogContent className="glass-modal max-h-[90vh] overflow-y-auto max-w-xl">
            <DialogHeader>
              <DialogTitle>Edit AI Generated Question #{editingIndex! + 1}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 text-xs">
              <div className="space-y-1">
                <Label>Question Text</Label>
                <Textarea value={editQuestion.text} onChange={(e) => setEditQuestion({ ...editQuestion, text: e.target.value })} rows={3} className="glass-input" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label>Difficulty</Label>
                  <Select value={editQuestion.difficulty} onValueChange={(v) => setEditQuestion({ ...editQuestion, difficulty: v })}>
                    <SelectTrigger className="glass-input"><SelectValue /></SelectTrigger>
                    <SelectContent className="glass-modal">
                      <SelectItem value="easy">Easy</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="hard">Hard</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label>Bloom Level</Label>
                  <Select value={editQuestion.bloom_level || 'understand'} onValueChange={(v) => setEditQuestion({ ...editQuestion, bloom_level: v })}>
                    <SelectTrigger className="glass-input"><SelectValue /></SelectTrigger>
                    <SelectContent className="glass-modal">
                      <SelectItem value="remember">Remember</SelectItem>
                      <SelectItem value="understand">Understand</SelectItem>
                      <SelectItem value="apply">Apply</SelectItem>
                      <SelectItem value="analyze">Analyze</SelectItem>
                      <SelectItem value="evaluate">Evaluate</SelectItem>
                      <SelectItem value="create">Create</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setEditingIndex(null)}>Cancel</Button>
              <Button onClick={handleSaveEdit}>Save Changes</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
