'use client';

import { useQuery } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle, Badge, Progress } from '@examshield/ui';
import { Award, Trophy, CheckCircle2, TrendingUp, Sparkles, BookOpen, AlertCircle, Loader2 } from 'lucide-react';

interface StudentAnalyticsRes {
  totalExamsCompleted: number;
  passedCount: number;
  avgPercentage: number;
  bestPercentage: number;
  passRate: number;
  performanceTrend: {
    examId: string;
    examTitle: string;
    percentage: number;
    obtainedMarks: number;
    totalMarks: number;
    isPassed: boolean;
    date: string;
  }[];
  subjectStrengths: { subject: string; accuracy: number }[];
  areasForImprovement: string[];
}

export default function StudentAnalyticsPage() {
  const api = useApiClient();

  const { data, isLoading } = useQuery<StudentAnalyticsRes>({
    queryKey: ['student-analytics-me'],
    queryFn: () => api.get<StudentAnalyticsRes>('/students/me/analytics'),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Personal Performance Intelligence & Analytics"
        description="Track score trends over time, identify subject strengths, and review areas for academic improvement."
      />

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground uppercase font-semibold">Exams Completed</p>
              <p className="text-2xl font-extrabold mt-1 text-primary">{data?.totalExamsCompleted || 0}</p>
            </div>
            <div className="p-2.5 bg-primary/10 rounded-xl text-primary"><BookOpen className="h-5 w-5" /></div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground uppercase font-semibold">Average Percentage</p>
              <p className="text-2xl font-extrabold mt-1 text-emerald-600">{data?.avgPercentage || 0}%</p>
            </div>
            <div className="p-2.5 bg-emerald-500/10 rounded-xl text-emerald-600"><Award className="h-5 w-5" /></div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground uppercase font-semibold">Best Score</p>
              <p className="text-2xl font-extrabold mt-1 text-amber-500">{data?.bestPercentage || 0}%</p>
            </div>
            <div className="p-2.5 bg-amber-500/10 rounded-xl text-amber-500"><Trophy className="h-5 w-5" /></div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground uppercase font-semibold">Personal Pass Rate</p>
              <p className="text-2xl font-extrabold mt-1 text-blue-600">{data?.passRate || 0}%</p>
            </div>
            <div className="p-2.5 bg-blue-500/10 rounded-xl text-blue-600"><CheckCircle2 className="h-5 w-5" /></div>
          </CardContent>
        </Card>
      </div>

      {/* Performance Trend & Strengths */}
      <div className="grid gap-6 lg:grid-cols-12">
        {/* Performance Trend Bar Timeline */}
        <Card className="glass-card lg:col-span-8">
          <CardHeader>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-primary" /> Examination Performance Trend Over Time
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-xs">
            {isLoading ? (
              <div className="p-6 text-center text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin mx-auto" /> Loading performance trend...</div>
            ) : !data?.performanceTrend.length ? (
              <div className="p-6 text-center text-muted-foreground">No completed exams found for trend analysis.</div>
            ) : (
              data.performanceTrend.map((t) => (
                <div key={t.examId} className="p-3 rounded-xl bg-muted/40 border border-border/40 space-y-1">
                  <div className="flex justify-between font-semibold text-foreground">
                    <span>{t.examTitle}</span>
                    <span className="text-emerald-600 font-bold">{t.percentage}%</span>
                  </div>
                  <Progress value={t.percentage} className="h-2" />
                  <div className="flex justify-between text-[10px] text-muted-foreground pt-1">
                    <span>{t.date}</span>
                    <span>{t.obtainedMarks} / {t.totalMarks} Marks ({t.isPassed ? 'PASSED' : 'FAILED'})</span>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Subject Strengths & Improvement Areas */}
        <div className="lg:col-span-4 space-y-6">
          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="text-sm font-bold flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-amber-500" /> Subject Strengths
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              {data?.subjectStrengths.map((s) => (
                <div key={s.subject} className="space-y-1">
                  <div className="flex justify-between">
                    <span className="font-semibold">{s.subject}</span>
                    <span className="font-bold text-emerald-600">{s.accuracy}%</span>
                  </div>
                  <Progress value={s.accuracy} className="h-1.5" />
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="text-sm font-bold flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-amber-500" /> Areas for Improvement
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-xs">
              {data?.areasForImprovement.map((area, idx) => (
                <div key={idx} className="p-2.5 rounded-xl bg-amber-50/80 border border-amber-200 text-amber-900 font-medium">
                  • {area}
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
