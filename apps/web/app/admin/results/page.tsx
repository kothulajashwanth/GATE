'use client';

import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge, Input } from '@examshield/ui';
import { Award, Search, Download, CheckCircle2, XCircle, Clock, FileSpreadsheet } from 'lucide-react';
import { useState } from 'react';
import { formatDate } from '@examshield/utils';

export default function AdminResultsPage() {
  const [search, setSearch] = useState('');

  const resultsList = [
    { id: '1', studentName: 'Alex Johnson', rollNo: 'CSE2024-001', examTitle: 'Data Structures Mid-term', score: 92, total: 100, percentage: 92, status: 'PASS', date: new Date().toISOString() },
    { id: '2', studentName: 'Sarah Smith', rollNo: 'CSE2024-045', examTitle: 'Data Structures Mid-term', score: 78, total: 100, percentage: 78, status: 'PASS', date: new Date().toISOString() },
    { id: '3', studentName: 'Michael Brown', rollNo: 'ECE2024-012', examTitle: 'Operating Systems Quiz', score: 35, total: 100, percentage: 35, status: 'FAIL', date: new Date(Date.now() - 86400000).toISOString() },
  ];

  const filtered = resultsList.filter((r) =>
    r.studentName.toLowerCase().includes(search.toLowerCase()) || r.rollNo.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <PageHeader title="Examination Results & Evaluation" description="View automated evaluations, student rank standings, and score breakdowns.">
        <Button variant="outline"><FileSpreadsheet className="h-4 w-4 mr-2" /> Export Roster Excel</Button>
      </PageHeader>

      <div className="flex items-center gap-4 max-w-md">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search student name or roll number..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
        </div>
      </div>

      <Card>
        <CardContent className="p-0 divide-y">
          {filtered.map((res) => (
            <div key={res.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-muted/20">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-base">{res.studentName}</span>
                  <Badge variant="outline" className="font-mono text-xs">{res.rollNo}</Badge>
                </div>
                <p className="text-xs text-muted-foreground">{res.examTitle} • Attempted {formatDate(res.date)}</p>
              </div>

              <div className="flex items-center gap-6 justify-between sm:justify-end">
                <div className="text-right">
                  <span className="font-extrabold text-lg">{res.score} / {res.total}</span>
                  <p className="text-xs text-muted-foreground">{res.percentage}% Score</p>
                </div>
                <Badge className={res.status === 'PASS' ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300' : 'bg-rose-500/15 text-rose-700'}>
                  {res.status === 'PASS' ? <CheckCircle2 className="h-3.5 w-3.5 mr-1" /> : <XCircle className="h-3.5 w-3.5 mr-1" />}
                  {res.status}
                </Badge>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
