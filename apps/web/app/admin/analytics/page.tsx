'use client';

import { useState } from 'react';
import {
  Card, CardContent, CardHeader, CardTitle,
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Button,
} from '@examshield/ui';
import { useQuery } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts';
import { downloadBlob } from '@examshield/utils';
import { Paginated } from '@examshield/types';

const COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16'];

interface ExamAnalytics {
  scoreStats: { count: number; avgPercentage: number; minPercentage: number; maxPercentage: number; stdPercentage: number };
  scoreDistribution: { range: string; count: number }[];
  timeStats: { avgTimeSeconds: number; minTimeSeconds: number; maxTimeSeconds: number };
  questionAnalysis: { questionId: string; text: string; type: string; totalAttempts: number; answered: number; correct: number; accuracy: number; avgMarks: number }[];
  departmentBreakdown: { department: string; count: number; avgPercentage: number }[];
  semesterBreakdown: { semester: string; count: number; avgPercentage: number }[];
}

export default function AnalyticsPage() {
  const api = useApiClient();
  const [selectedExam, setSelectedExam] = useState('');

  const { data: exams } = useQuery({
    queryKey: ['exams'],
    queryFn: () => api.get<Paginated<{ id: string; title: string }>>('/exams', { page_size: 100 }),
  });

  const { data: analytics, isLoading } = useQuery<ExamAnalytics>({
    queryKey: ['analytics', selectedExam],
    queryFn: () => api.get(`/analytics/exam/${selectedExam}/analytics`),
    enabled: !!selectedExam,
  });

  const handleDownload = async (format: string) => {
    if (!selectedExam) return;
    const blob = await api.raw.download(`/analytics/exam/${selectedExam}/report?format=${format}`);
    downloadBlob(blob, `exam-report-${selectedExam.slice(0, 8)}.${format === 'excel' ? 'xlsx' : format}`);
  };

  const passRate = analytics
    ? analytics.scoreDistribution
        .filter(d => d.range.startsWith('4') || d.range.startsWith('5') || d.range.startsWith('6') || d.range.startsWith('7') || d.range.startsWith('8') || d.range.startsWith('9') || d.range.startsWith('10'))
        .reduce((sum, d) => sum + d.count, 0)
    : 0;

  return (
    <div className="space-y-6">
      <PageHeader title="Analytics" description="Performance insights across exams, departments, and semesters">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" disabled={!selectedExam} onClick={() => handleDownload('pdf')}>PDF</Button>
          <Button variant="outline" size="sm" disabled={!selectedExam} onClick={() => handleDownload('excel')}>Excel</Button>
          <Button variant="outline" size="sm" disabled={!selectedExam} onClick={() => handleDownload('csv')}>CSV</Button>
        </div>
      </PageHeader>

      <div className="flex items-center gap-3">
        <Select value={selectedExam} onValueChange={setSelectedExam}>
          <SelectTrigger className="w-[300px]"><SelectValue placeholder="Select exam" /></SelectTrigger>
          <SelectContent>
            {exams?.items?.map((e) => <SelectItem key={e.id} value={e.id}>{e.title}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {!selectedExam ? (
        <Card><CardContent className="p-12 text-center text-muted-foreground">
          Select an exam to view analytics.
        </CardContent></Card>
      ) : isLoading ? (
        <Card><CardContent className="p-12 text-center text-muted-foreground">Loading...</CardContent></Card>
      ) : analytics ? (
        <div className="space-y-6">
          {/* Summary stats */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            {[
              { label: 'Students', value: analytics.scoreStats.count },
              { label: 'Average', value: `${analytics.scoreStats.avgPercentage}%` },
              { label: 'Highest', value: `${analytics.scoreStats.maxPercentage}%` },
              { label: 'Lowest', value: `${analytics.scoreStats.minPercentage}%` },
              { label: 'Passing Rate', value: `${Math.round((passRate / Math.max(analytics.scoreStats.count, 1)) * 100)}%` },
            ].map((s) => (
              <Card key={s.label}><CardContent className="p-4">
                <p className="text-sm text-muted-foreground">{s.label}</p>
                <p className="text-2xl font-bold mt-1">{s.value}</p>
              </CardContent></Card>
            ))}
          </div>

          {/* Score distribution */}
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>Score Distribution</CardTitle></CardHeader>
              <CardContent className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={analytics.scoreDistribution}>
                    <XAxis dataKey="range" />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Department breakdown */}
            <Card>
              <CardHeader><CardTitle>Department Performance</CardTitle></CardHeader>
              <CardContent className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={analytics.departmentBreakdown}
                      dataKey="avgPercentage"
                      nameKey="department"
                      outerRadius={80}
                      label={(entry) => entry.department}
                    >
                      {analytics.departmentBreakdown.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Semester breakdown */}
          <Card>
            <CardHeader><CardTitle>Semester Performance</CardTitle></CardHeader>
            <CardContent className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={analytics.semesterBreakdown}>
                  <XAxis dataKey="semester" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="avgPercentage" fill="#22c55e" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Question analysis */}
          <Card>
            <CardHeader><CardTitle>Question Analysis</CardTitle></CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-muted-foreground">
                      <th className="text-left p-3">Question</th>
                      <th className="text-left p-3">Type</th>
                      <th className="text-right p-3">Attempts</th>
                      <th className="text-right p-3">Accuracy</th>
                      <th className="text-right p-3">Avg Marks</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analytics.questionAnalysis.map((q) => (
                      <tr key={q.questionId} className="border-b last:border-0 hover:bg-muted/50">
                        <td className="p-3 max-w-[300px] truncate">{q.text}</td>
                        <td className="p-3">{q.type}</td>
                        <td className="p-3 text-right">{q.totalAttempts}</td>
                        <td className="p-3 text-right">{q.accuracy}%</td>
                        <td className="p-3 text-right">{q.avgMarks}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </div>
  );
}