'use client';

import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle, Button } from '@examshield/ui';
import { FileText, Download, Printer, BarChart3, PieChart, FileSpreadsheet } from 'lucide-react';
import { toast } from 'sonner';

export default function AdminReportsPage() {
  const generateReport = (type: string) => {
    toast.success(`Generating ${type} report PDF/Excel export...`);
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Academic Reports & Institutional Analytics" description="Generate PDF, Excel, CSV, and printable audit reports for department heads and accreditation." />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card className="hover:shadow-md transition-shadow">
          <CardHeader>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <FileSpreadsheet className="h-5 w-5 text-emerald-600" /> Department Performance Summary
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-muted-foreground">Department-wise average scores, passing rates, and question difficulty distribution.</p>
            <Button size="sm" className="w-full" onClick={() => generateReport('Department Performance')}>
              <Download className="h-3.5 w-3.5 mr-2" /> Download Report (PDF/Excel)
            </Button>
          </CardContent>
        </Card>

        <Card className="hover:shadow-md transition-shadow">
          <CardHeader>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-primary" /> Examination Security & Violations Log
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-muted-foreground">Audit report of warning counts, tab switching, and proctoring termination reasons.</p>
            <Button size="sm" variant="outline" className="w-full" onClick={() => generateReport('Proctoring Audit')}>
              <Printer className="h-3.5 w-3.5 mr-2" /> Print Audit Summary
            </Button>
          </CardContent>
        </Card>

        <Card className="hover:shadow-md transition-shadow">
          <CardHeader>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <FileText className="h-5 w-5 text-amber-500" /> Question Bank Taxonomy Audit
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-muted-foreground">Bloom Taxonomy distribution, difficulty balancing, and question versioning history.</p>
            <Button size="sm" variant="outline" className="w-full" onClick={() => generateReport('Taxonomy Audit')}>
              <Download className="h-3.5 w-3.5 mr-2" /> Export CSV Roster
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
