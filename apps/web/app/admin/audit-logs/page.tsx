'use client';

import { PageHeader } from '@/components/page-header';
import { Card, CardContent, Badge, Input } from '@examshield/ui';
import { History, Search, ShieldCheck, UserCheck, Key, Database } from 'lucide-react';
import { useState } from 'react';
import { formatDate } from '@examshield/utils';

export default function AdminAuditLogsPage() {
  const [search, setSearch] = useState('');

  const logs = [
    { id: '1', action: 'Question Bank Ingestion', details: 'Ingested 50 questions from Java_Mid1.pdf (OCR fallback used)', admin: 'kothulajashwanth@gmail.com', ip: '192.168.1.1', timestamp: new Date().toISOString() },
    { id: '2', action: 'Exam Rule Update', details: 'Updated maximum security warning count to 3 warnings', admin: 'kothulajashwanth@gmail.com', ip: '192.168.1.1', timestamp: new Date(Date.now() - 3600000).toISOString() },
    { id: '3', action: 'Student Roster Import', details: 'Imported 120 student accounts via Excel file CSE_Roster.xlsx', admin: 'kothulajashwanth@gmail.com', ip: '192.168.1.1', timestamp: new Date(Date.now() - 86400000).toISOString() },
  ];

  const filtered = logs.filter((l) => l.action.toLowerCase().includes(search.toLowerCase()) || l.details.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="space-y-6">
      <PageHeader title="System Audit Logs & Security History" description="Immutable audit record of administrative actions, roster modifications, and rule updates." />

      <div className="flex items-center gap-4 max-w-md">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search audit logs..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
        </div>
      </div>

      <Card>
        <CardContent className="p-0 divide-y">
          {filtered.map((log) => (
            <div key={log.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="font-bold">{log.action}</Badge>
                  <span className="font-semibold text-foreground">{log.details}</span>
                </div>
                <div className="flex items-center gap-3 text-muted-foreground">
                  <span>Admin: <strong className="text-foreground">{log.admin}</strong></span>
                  <span>IP: {log.ip}</span>
                </div>
              </div>
              <span className="text-muted-foreground whitespace-nowrap">{formatDate(log.timestamp)}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
