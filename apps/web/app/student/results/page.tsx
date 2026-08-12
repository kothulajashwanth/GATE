'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import {
  Card, CardContent, CardHeader, CardTitle, Button, Badge,
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Progress
} from '@examshield/ui';
import {
  Award, Trophy, CheckCircle2, XCircle, Eye, ArrowRight, Loader2, FileText, Check, AlertCircle, Percent
} from 'lucide-react';
import { EmptyState } from '@/components/empty-state';
import { formatDateTime } from '@examshield/utils';

interface ResultRow {
  id: string;
  examId: string;
  examTitle: string | null;
  totalMarks: number;
  obtainedMarks: number;
  percentage: number;
  rank: number | null;
  isPassed: boolean | null;
  status: string;
  publishedAt: string | null;
  questionAnalysis: any[];
}

export default function StudentResultsPage() {
  const api = useApiClient();
  const [selectedResult, setSelectedResult] = useState<ResultRow | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['student-results'],
    queryFn: () => api.get<{ items: ResultRow[]; total: number }>('/results/me'),
  });

  const results = data?.items || [];
  const passedCount = results.filter((r) => r.isPassed === true).length;
  const avgPercentage = results.length
    ? Math.round(results.reduce((acc, r) => acc + (r.percentage || 0), 0) / results.length)
    : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="My Published Examination Results"
        description="View authoritative server-evaluated scores, percentages, rank standings, and detailed question breakdowns for published exams."
      />

      {/* Metric Overview */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground uppercase font-semibold">Exams Evaluated</p>
              <p className="text-2xl font-extrabold mt-1 text-primary">{results.length}</p>
            </div>
            <div className="p-2.5 bg-primary/10 rounded-xl text-primary"><Award className="h-5 w-5" /></div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground uppercase font-semibold">Exams Passed</p>
              <p className="text-2xl font-extrabold mt-1 text-emerald-600">{passedCount}</p>
            </div>
            <div className="p-2.5 bg-emerald-500/10 rounded-xl text-emerald-600"><CheckCircle2 className="h-5 w-5" /></div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground uppercase font-semibold">Average Percentage</p>
              <p className="text-2xl font-extrabold mt-1 text-amber-500">{avgPercentage}%</p>
            </div>
            <div className="p-2.5 bg-amber-500/10 rounded-xl text-amber-500"><Percent className="h-5 w-5" /></div>
          </CardContent>
        </Card>
      </div>

      {/* Published Results Table */}
      <Card className="glass-card">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-primary" /> Fetching published results...
            </div>
          ) : !results.length ? (
            <div className="p-8">
              <EmptyState
                title="No published results available"
                description="Your examination scores will appear here once published by your course administrator."
              />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-b border-border/50">
                  <TableHead>Examination</TableHead>
                  <TableHead>Marks Obtained</TableHead>
                  <TableHead>Percentage</TableHead>
                  <TableHead>Rank</TableHead>
                  <TableHead>Result Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {results.map((r) => (
                  <TableRow key={r.id} className="border-b border-border/40 hover:bg-white/30 dark:hover:bg-slate-800/30">
                    <TableCell className="font-bold text-xs">
                      <div>{r.examTitle || 'Examination'}</div>
                      <div className="text-[10px] text-muted-foreground font-mono">ID: #{r.id.slice(0, 8)}</div>
                    </TableCell>
                    <TableCell className="text-xs font-semibold">{r.obtainedMarks} / {r.totalMarks}</TableCell>
                    <TableCell className="text-xs font-semibold">{r.percentage}%</TableCell>
                    <TableCell className="text-xs font-bold text-amber-600">
                      {r.rank ? `#${r.rank}` : 'N/A'}
                    </TableCell>
                    <TableCell>
                      <Badge variant={r.isPassed ? 'default' : 'destructive'} className={r.isPassed ? 'bg-emerald-600 text-xs' : 'text-xs'}>
                        {r.isPassed ? 'PASSED' : 'FAILED'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button size="sm" variant="ghost" onClick={() => setSelectedResult(r)}>
                        <Eye className="h-3.5 w-3.5 mr-1" /> View Breakdown
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Detailed Result Modal */}
      {selectedResult && (
        <Dialog open={!!selectedResult} onOpenChange={(b) => { if (!b) setSelectedResult(null); }}>
          <DialogContent className="glass-modal max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Trophy className="h-5 w-5 text-amber-500" /> Score Breakdown Report
              </DialogTitle>
              <DialogDescription>{selectedResult.examTitle}</DialogDescription>
            </DialogHeader>

            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-muted/40 rounded-xl space-y-1">
                  <div className="text-muted-foreground">Score</div>
                  <div className="text-lg font-bold text-foreground">{selectedResult.obtainedMarks} / {selectedResult.totalMarks} Marks</div>
                </div>
                <div className="p-3 bg-muted/40 rounded-xl space-y-1">
                  <div className="text-muted-foreground">Percentage</div>
                  <div className="text-lg font-bold text-emerald-600">{selectedResult.percentage}%</div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs font-semibold">
                  <span>Score Progress</span>
                  <span>{selectedResult.percentage}%</span>
                </div>
                <Progress value={selectedResult.percentage} className="h-2" />
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setSelectedResult(null)}>Close</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
