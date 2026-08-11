'use client';

import Link from 'next/link';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, Button, Badge } from '@examshield/ui';
import { CheckCircle2, Trophy, ArrowRight, ShieldCheck } from 'lucide-react';

export default function ExamCompletedPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background bg-ambient-light p-4">
      <Card className="glass-modal max-w-md w-full text-center p-8 space-y-6">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-600 mx-auto shadow-inner">
          <CheckCircle2 className="h-10 w-10" />
        </div>

        <div className="space-y-2">
          <h2 className="text-xl font-extrabold text-foreground">Examination Submitted</h2>
          <p className="text-xs text-muted-foreground">
            Your examination responses have been securely persisted and locked in Render PostgreSQL.
          </p>
        </div>

        <div className="p-4 rounded-xl bg-muted/40 text-xs space-y-2 border border-border/40 text-left">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Status:</span>
            <Badge variant="default" className="bg-emerald-600 text-[10px]">SUBMITTED & LOCKED</Badge>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Evaluation:</span>
            <span className="font-bold text-foreground">Automatic Scoring Complete</span>
          </div>
        </div>

        <Link href="/student">
          <Button className="w-full glass-button bg-primary text-white">
            Return to Student Dashboard <ArrowRight className="h-4 w-4 ml-2" />
          </Button>
        </Link>
      </Card>
    </div>
  );
}
