'use client';

import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle, Button } from '@examshield/ui';
import { FileText, Download, BarChart3, FileSpreadsheet } from 'lucide-react';
import { toast } from 'sonner';

export default function AdminReportsPage() {
  const handleExportCsv = async (title: string) => {
    toast.info(`Generating ${title}...`);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/analytics/export`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('auth_token') || ''}`,
        },
      });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'gate_ignite_institutional_report.csv';
      a.click();
      toast.success(`${title} exported successfully!`);
    } catch {
      toast.error('Failed to export report');
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Academic Reports & Institutional Intelligence"
        description="Generate, print, and export CSV & Excel reports for department heads, accreditation, and security audits."
      />

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <FileSpreadsheet className="h-5 w-5 text-emerald-600" /> Institutional Grade Summary
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-muted-foreground">
              Complete student examination performance report with marks obtained, total marks, percentages, and pass/fail statuses.
            </p>
            <Button size="sm" className="w-full glass-button" onClick={() => handleExportCsv('Institutional Grade Summary')}>
              <Download className="h-3.5 w-3.5 mr-2 text-primary" /> Download CSV Summary Report
            </Button>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-primary" /> Proctoring & Security Audit Log
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-muted-foreground">
              Audit log of proctoring telemetry violations, tab switches, warning counts, and session terminations.
            </p>
            <Button size="sm" variant="outline" className="w-full glass-button" onClick={() => handleExportCsv('Proctoring & Security Audit Log')}>
              <Download className="h-3.5 w-3.5 mr-2 text-primary" /> Download Security Audit Log (CSV)
            </Button>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <FileText className="h-5 w-5 text-amber-500" /> Question Pool Taxonomy Audit
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-muted-foreground">
              Bloom's Taxonomy classification audit, difficulty distribution, and verified question metadata report.
            </p>
            <Button size="sm" variant="outline" className="w-full glass-button" onClick={() => handleExportCsv('Question Pool Taxonomy Audit')}>
              <Download className="h-3.5 w-3.5 mr-2 text-primary" /> Export Question Taxonomy (CSV)
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
