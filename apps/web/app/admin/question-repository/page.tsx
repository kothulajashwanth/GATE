'use client';

import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import {
  Card, CardContent, CardHeader, CardTitle, Button, Badge, Input,
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Label, Textarea,
} from '@examshield/ui';
import {
  UploadCloud, FileText, CheckCircle2, Clock, AlertTriangle, Eye, Plus, FileCode,
  Loader2, Edit3, Trash2, Check, AlertCircle, FileSpreadsheet, Layers, BookOpen
} from 'lucide-react';
import { toast } from 'sonner';

interface UploadedFileItem {
  id: string;
  fileName: string;
  originalName: string;
  fileType: 'pdf' | 'docx' | 'txt' | 'xlsx';
  fileSize: string;
  status: string;
  questionsFound: number;
  ocrUsed: boolean;
  createdAt: string;
}

interface ParsedQuestionItem {
  number: string;
  text: string;
  question_type: string;
  options: string[];
  correct_answers: string[];
  marks: number;
  difficulty: string;
  explanation?: string;
  subject_code?: str;
  topic_name?: str;
  status: string;
  is_duplicate?: boolean;
  duplicate_of_id?: string;
}

interface ProcessResult {
  file_id: string;
  status: string;
  total: number;
  valid_count: number;
  review_count: number;
  failed_count: number;
  ocr_required: boolean;
  questions: ParsedQuestionItem[];
  failed_questions: { row: number; raw_data: string; reason: string }[];
}

export default function QuestionRepositoryPage() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isUploading, setIsUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<UploadedFileItem | null>(null);
  const [previewData, setPreviewData] = useState<ProcessResult | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);

  // Edit Question Modal State
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editQuestion, setEditQuestion] = useState<ParsedQuestionItem | null>(null);

  const { data: files = [], refetch } = useQuery<UploadedFileItem[]>({
    queryKey: ['question-repository-files'],
    queryFn: () => api.get<UploadedFileItem[]>('/question-bank/files'),
  });

  const { data: subjects = [] } = useQuery<{ id: string; name: string; code: string }[]>({
    queryKey: ['subjects'],
    queryFn: () => api.get<{ id: string; name: string; code: string }[]>('/question-bank/subjects'),
  });

  // Real OS File Manager Picker Upload
  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    toast.info(`Uploading document: ${file.name}...`);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const uf = await api.post<UploadedFileItem>('/question-bank/files', formData);
      toast.success(`Uploaded ${file.name} successfully!`);
      refetch();

      // Trigger automatic extraction processing
      handleProcessFile(uf.id, uf);
    } catch (err: any) {
      toast.error(err.message || 'File upload failed');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Process Document Extraction & Open Preview
  const handleProcessFile = async (fileId: string, fileItem?: UploadedFileItem) => {
    setIsProcessing(true);
    if (fileItem) setSelectedFile(fileItem);
    toast.info('Extracting questions, options, and checking duplicates...');

    try {
      const res = await api.post<ProcessResult>(`/question-bank/files/${fileId}/process`);
      setPreviewData(res);
      setIsPreviewOpen(true);
      refetch();
    } catch (err: any) {
      toast.error(err.message || 'Processing failed');
    } finally {
      setIsProcessing(false);
    }
  };

  // Confirm Import into PostgreSQL
  const handleConfirmImport = async () => {
    if (!previewData || !selectedFile) return;
    setIsConfirming(true);
    try {
      const res = await api.post<{ imported_count: number }>(`/question-bank/import/${previewData.file_id}/confirm`, {
        questions: previewData.questions,
      });
      toast.success(`Successfully imported ${res.imported_count} questions into PostgreSQL Question Bank!`);
      setIsPreviewOpen(false);
      setPreviewData(null);
      refetch();
    } catch (err: any) {
      toast.error(err.message || 'Import confirmation failed');
    } finally {
      setIsConfirming(false);
    }
  };

  // Update Edited Question in Local Preview Array
  const handleSaveEditedQuestion = () => {
    if (editingIndex === null || !editQuestion || !previewData) return;
    const updatedQs = [...previewData.questions];
    updatedQs[editingIndex] = editQuestion;
    setPreviewData({ ...previewData, questions: updatedQs });
    setEditingIndex(null);
    setEditQuestion(null);
    toast.success('Question updated in preview list');
  };

  // Remove Question from Preview List
  const handleRemovePreviewQuestion = (index: number) => {
    if (!previewData) return;
    const updatedQs = previewData.questions.filter((_, idx) => idx !== index);
    setPreviewData({ ...previewData, questions: updatedQs, total: previewData.total - 1 });
    toast.info('Question removed from import preview');
  };

  return (
    <div className="space-y-6">
      {/* Hidden Real OS File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelected}
        accept=".pdf,.docx,.txt,.xlsx,.xls"
        className="hidden"
      />

      <PageHeader
        title="Question Repository & Document Pipeline"
        description="Upload question documents (PDF, DOCX, TXT, XLSX), parse questions, review validation errors, and confirm import."
      >
        <Button size="sm" disabled={isUploading} onClick={() => fileInputRef.current?.click()} className="glass-button">
          {isUploading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <UploadCloud className="h-4 w-4 mr-1" />}
          Upload Question Document
        </Button>
      </PageHeader>

      {/* Uploaded Files Table */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Layers className="h-5 w-5 text-primary" /> Repository Upload History
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {!files.length ? (
            <div className="p-8 text-center text-muted-foreground flex flex-col items-center justify-center gap-2">
              <FileText className="h-8 w-8 text-muted-foreground/50" />
              <p>No uploaded question files yet. Click "Upload Question Document" to select a file.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-b border-border/50">
                  <TableHead>File Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Questions Extracted</TableHead>
                  <TableHead>Upload Date</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {files.map((file) => (
                  <TableRow key={file.id} className="border-b border-border/40 hover:bg-white/30 dark:hover:bg-slate-800/30">
                    <TableCell className="font-medium flex items-center gap-2">
                      <FileText className="h-4 w-4 text-blue-500 flex-shrink-0" />
                      {file.originalName}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="uppercase text-[10px]">
                        {file.fileType}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">{file.fileSize}</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          file.status === 'completed'
                            ? 'default'
                            : file.status === 'parsed'
                            ? 'secondary'
                            : file.status === 'review_required'
                            ? 'warning'
                            : 'destructive'
                        }
                      >
                        {file.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-semibold text-xs">{file.questionsFound}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(file.createdAt).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={isProcessing}
                        onClick={() => handleProcessFile(file.id, file)}
                        className="glass-button"
                      >
                        <Eye className="h-3.5 w-3.5 mr-1" />
                        Preview & Review
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Interactive Import Validation & Preview Modal */}
      <Dialog open={isPreviewOpen} onOpenChange={setIsPreviewOpen}>
        <DialogContent className="glass-modal max-h-[90vh] overflow-y-auto max-w-4xl">
          <DialogHeader>
            <DialogTitle>Question Extraction Preview & Review</DialogTitle>
            <DialogDescription>
              Review extracted questions, edit choices, resolve warnings, and confirm save to PostgreSQL.
            </DialogDescription>
          </DialogHeader>

          {isProcessing ? (
            <div className="p-8 text-center flex flex-col items-center justify-center gap-2">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">Extracting text and running question validation engine...</p>
            </div>
          ) : previewData ? (
            <div className="space-y-6">
              {/* Summary Stats */}
              <div className="grid grid-cols-4 gap-4 text-center">
                <div className="p-3 bg-muted/50 rounded-xl">
                  <div className="text-xl font-bold">{previewData.total}</div>
                  <div className="text-xs text-muted-foreground">Total Parsed</div>
                </div>
                <div className="p-3 bg-emerald-50/80 text-emerald-800 rounded-xl">
                  <div className="text-xl font-bold">{previewData.valid_count}</div>
                  <div className="text-xs">Valid</div>
                </div>
                <div className="p-3 bg-amber-50/80 text-amber-800 rounded-xl">
                  <div className="text-xl font-bold">{previewData.review_count}</div>
                  <div className="text-xs">Review Required</div>
                </div>
                <div className="p-3 bg-rose-50/80 text-rose-800 rounded-xl">
                  <div className="text-xl font-bold">{previewData.failed_count}</div>
                  <div className="text-xs">Failed Rows</div>
                </div>
              </div>

              {/* Failed Questions Warnings */}
              {previewData.failed_questions.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-rose-600 flex items-center gap-1">
                    <AlertCircle className="h-4 w-4" /> Unparseable Block Log ({previewData.failed_questions.length})
                  </h4>
                  <div className="max-h-32 overflow-y-auto border border-rose-200 rounded-xl p-3 bg-rose-50/50 space-y-1">
                    {previewData.failed_questions.map((fq, idx) => (
                      <div key={idx} className="text-xs text-rose-800 font-mono">
                        Row {fq.row}: {fq.reason}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Parsed Questions List */}
              <div className="space-y-4">
                <h4 className="text-sm font-semibold flex items-center gap-1">
                  <BookOpen className="h-4 w-4 text-primary" /> Extracted Questions ({previewData.questions.length})
                </h4>
                <div className="space-y-3">
                  {previewData.questions.map((q, idx) => (
                    <Card key={idx} className="glass-card p-4 text-xs relative space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-foreground">#{idx + 1}</span>
                          <Badge variant="outline" className="uppercase text-[10px]">{q.question_type}</Badge>
                          <Badge variant="secondary" className="uppercase text-[10px]">{q.difficulty}</Badge>
                          <Badge variant="outline">{q.marks} Marks</Badge>
                          {q.is_duplicate && (
                            <Badge variant="warning" className="flex items-center gap-1">
                              <AlertTriangle className="h-3 w-3" /> Duplicate Detected
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => { setEditingIndex(idx); setEditQuestion({ ...q }); }}
                          >
                            <Edit3 className="h-3.5 w-3.5 mr-1" /> Edit
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-destructive hover:bg-rose-50"
                            onClick={() => handleRemovePreviewQuestion(idx)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </div>

                      <p className="font-medium text-sm text-foreground">{q.text}</p>

                      {q.options && q.options.length > 0 && (
                        <div className="grid grid-cols-2 gap-2 pt-1 pl-2">
                          {q.options.map((opt, oIdx) => {
                            const letter = String.fromCharCode(65 + oIdx);
                            const isAns = q.correct_answers.includes(letter) || q.correct_answers.includes(opt);
                            return (
                              <div
                                key={oIdx}
                                className={`p-2 rounded-lg border text-xs ${
                                  isAns ? 'bg-emerald-50/80 border-emerald-300 font-semibold text-emerald-800' : 'bg-muted/40'
                                }`}
                              >
                                <span className="font-bold mr-1">{letter}.</span> {opt}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </Card>
                  ))}
                </div>
              </div>
            </div>
          ) : null}

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsPreviewOpen(false)}>Cancel</Button>
            <Button
              onClick={handleConfirmImport}
              disabled={isConfirming || !previewData || !previewData.questions.length}
            >
              {isConfirming ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Check className="h-4 w-4 mr-2" />}
              Confirm & Save {previewData?.questions.length ?? 0} Questions to DB
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Extracted Question Modal */}
      {editQuestion && (
        <Dialog open={editingIndex !== null} onOpenChange={(b) => { if (!b) setEditingIndex(null); }}>
          <DialogContent className="glass-modal max-h-[90vh] overflow-y-auto max-w-xl">
            <DialogHeader>
              <DialogTitle>Edit Extracted Question #{editingIndex! + 1}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 text-xs">
              <div className="space-y-1">
                <Label>Question Text</Label>
                <Textarea
                  value={editQuestion.text}
                  onChange={(e) => setEditQuestion({ ...editQuestion, text: e.target.value })}
                  rows={3}
                  className="glass-input"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label>Question Type</Label>
                  <Select
                    value={editQuestion.question_type}
                    onValueChange={(v) => setEditQuestion({ ...editQuestion, question_type: v })}
                  >
                    <SelectTrigger className="glass-input"><SelectValue /></SelectTrigger>
                    <SelectContent className="glass-modal">
                      <SelectItem value="mcq">MCQ (Single Choice)</SelectItem>
                      <SelectItem value="multi_select">Multi Select</SelectItem>
                      <SelectItem value="true_false">True / False</SelectItem>
                      <SelectItem value="fill_blank">Fill in the Blank</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label>Difficulty</Label>
                  <Select
                    value={editQuestion.difficulty}
                    onValueChange={(v) => setEditQuestion({ ...editQuestion, difficulty: v })}
                  >
                    <SelectTrigger className="glass-input"><SelectValue /></SelectTrigger>
                    <SelectContent className="glass-modal">
                      <SelectItem value="easy">Easy</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="hard">Hard</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Options Editing */}
              {editQuestion.options && editQuestion.options.length > 0 && (
                <div className="space-y-2">
                  <Label>Options</Label>
                  {editQuestion.options.map((opt, oIdx) => (
                    <div key={oIdx} className="flex items-center gap-2">
                      <span className="font-bold w-4">{String.fromCharCode(65 + oIdx)}.</span>
                      <Input
                        value={opt}
                        onChange={(e) => {
                          const newOpts = [...editQuestion.options];
                          newOpts[oIdx] = e.target.value;
                          setEditQuestion({ ...editQuestion, options: newOpts });
                        }}
                        className="glass-input"
                      />
                    </div>
                  ))}
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label>Correct Answer (A, B, C, D)</Label>
                  <Input
                    value={editQuestion.correct_answers.join(', ')}
                    onChange={(e) => setEditQuestion({ ...editQuestion, correct_answers: [e.target.value.toUpperCase()] })}
                    className="glass-input"
                  />
                </div>
                <div className="space-y-1">
                  <Label>Marks</Label>
                  <Input
                    type="number"
                    value={editQuestion.marks}
                    onChange={(e) => setEditQuestion({ ...editQuestion, marks: parseInt(e.target.value) || 1 })}
                    className="glass-input"
                  />
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setEditingIndex(null)}>Cancel</Button>
              <Button onClick={handleSaveEditedQuestion}>Save Changes</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
