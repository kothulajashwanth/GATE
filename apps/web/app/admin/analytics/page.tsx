'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import {
  Card, CardContent, CardHeader, CardTitle, Button, Badge, Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Progress
} from '@examshield/ui';
import {
  BarChart3, Users, FileQuestion, Award, ShieldAlert, Download, Calendar, Loader2, CheckCircle2, AlertTriangle, Activity
} from 'lucide-react';
import { toast } from 'sonner';

interface OverviewRes {
  totalStudents: number;
  totalExams: number;
  totalAttempts: number;
  totalResults: number;
  passedCount: number;
  failedCount: number;
  passRate: number;
  avgPercentage: number;
  scoreDistribution: { range: string; count: number }[];
  totalViolations: number;
}

interface DeptRes {
  id: string;
  name: string;
  studentCount: number;
  attemptsCount: number;
  avgPercentage: number;
  passRate: number;
}

export default function AdminAnalyticsPage() {
  const api = useApiClient();
  const [days, setDays] = useState(30);

  const { data: overview, isLoading: loadingOverview } = useQuery<OverviewRes>({
    queryKey: ['admin-analytics-overview', days],
    queryFn: () => api.get<OverviewRes>(`/analytics/overview`, { days }),
  });

  const { data: departments = [], isLoading: loadingDepts } = useQuery<DeptRes[]>({
    queryKey: ['admin-analytics-departments'],
    queryFn: () => api.get<DeptRes[]>(`/analytics/departments`),
  });

  const handleExportCsv = async () => {
    toast.info('Generating CSV Analytics Summary Report...');
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/analytics/export`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token') || ''}`,
        },
      });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'gate_ignite_analytics_report.csv';
      a.click();
      toast.success('CSV Report exported successfully!');
    } catch {
      toast.error('Failed to export report');
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Institutional Analytics & Performance Intelligence"
        description="Comprehensive score distributions, department performance metrics, pass/fail trends, and proctoring telemetry analytics."
      >
        <Button size="sm" variant="outline" className="glass-button" onClick={handleExportCsv}>
          <Download className="h-4 w-4 mr-1 text-primary" /> Export CSV Report
        </Button>
      </PageHeader>

      {/* Date Filter Toolbar */}
      <div className="flex items-center justify-between gap-4 p-4 glass-card rounded-2xl">
        <div className="flex items-center gap-2 text-xs font-semibold">
          <Calendar className="h-4 w-4 text-primary" /> Select Time Window:
        </div>
        <div className="flex items-center gap-2">
          {[7, 30, 90, 0].map((d) => (
            <Button
              key={d}
              size="sm"
              variant={days === d ? 'default' : 'outline'}
              className="text-xs glass-button"
              onClick={() => setDays(d)}
            >
              {d === 0 ? 'All Time' : `${d} Days`}
            </Button>
          ))}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground uppercase font-semibold">Active Students</p>
              <p className="text-2xl font-extrabold mt-1 text-primary">{overview?.totalStudents || 0}</p>
            </div>
            <div className="p-2.5 bg-primary/10 rounded-xl text-primary"><Users className="h-5 w-5" /></div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground uppercase font-semibold">Total Exam Attempts</p>
              <p className="text-2xl font-extrabold mt-1 text-blue-600">{overview?.totalAttempts || 0}</p>
            </div>
            <div className="p-2.5 bg-blue-500/10 rounded-xl text-blue-600"><Activity className="h-5 w-5" /></div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground uppercase font-semibold">Institutional Pass Rate</p>
              <p className="text-2xl font-extrabold mt-1 text-emerald-600">{overview?.passRate || 0}%</p>
            </div>
            <div className="p-2.5 bg-emerald-500/10 rounded-xl text-emerald-600"><CheckCircle2 className="h-5 w-5" /></div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground uppercase font-semibold">Average Percentage</p>
              <p className="text-2xl font-extrabold mt-1 text-amber-500">{overview?.avgPercentage || 0}%</p>
            </div>
            <div className="p-2.5 bg-amber-500/10 rounded-xl text-amber-500"><Award className="h-5 w-5" /></div>
          </CardContent>
        </Card>
      </div>

      {/* Score Distribution & Department Breakdowns */}
      <div className="grid gap-6 lg:grid-cols-12">
        {/* Score Distribution Histogram Bar Representation */}
        <Card className="glass-card lg:col-span-6">
          <CardHeader>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-primary" /> Score Distribution Histogram
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            {loadingOverview ? (
              <div className="p-6 text-center text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin mx-auto" /> Loading score distribution...</div>
            ) : (
              overview?.scoreDistribution.map((bucket) => {
                const maxCount = Math.max(...(overview?.scoreDistribution.map((b) => b.count) || [1]), 1);
                const barPct = Math.round((bucket.count / maxCount) * 100);
                return (
                  <div key={bucket.range} className="space-y-1">
                    <div className="flex justify-between text-[11px] font-medium">
                      <span>Range {bucket.range}</span>
                      <span className="font-bold">{bucket.count} Results</span>
                    </div>
                    <Progress value={barPct} className="h-2" />
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>

        {/* Department Performance */}
        <Card className="glass-card lg:col-span-6">
          <CardHeader>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <Users className="h-5 w-5 text-emerald-600" /> Department Performance Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loadingDepts ? (
              <div className="p-6 text-center text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin mx-auto" /> Loading departments...</div>
            ) : !departments.length ? (
              <div className="p-6 text-center text-muted-foreground">No departments registered.</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="border-b border-border/50">
                    <TableHead>Department</TableHead>
                    <TableHead>Students</TableHead>
                    <TableHead>Attempts</TableHead>
                    <TableHead>Avg Score</TableHead>
                    <TableHead>Pass Rate</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {departments.map((d) => (
                    <TableRow key={d.id} className="border-b border-border/40">
                      <TableCell className="font-semibold text-xs">{d.name}</TableCell>
                      <TableCell className="text-xs">{d.studentCount}</TableCell>
                      <TableCell className="text-xs">{d.attemptsCount}</TableCell>
                      <TableCell className="text-xs font-bold text-primary">{d.avgPercentage}%</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="bg-emerald-100 text-emerald-800 text-[10px]">
                          {d.passRate}%
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}