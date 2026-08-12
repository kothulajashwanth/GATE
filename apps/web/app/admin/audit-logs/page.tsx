'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, Badge, Input } from '@examshield/ui';
import { Search, Loader2 } from 'lucide-react';
import { formatDate } from '@examshield/utils';

interface AuditLogRes {
  id: string;
  action: string;
  entityType: string;
  entityId: string | null;
  actorId: string | null;
  actorEmail: string;
  ipAddress: string | null;
  createdAt: string | null;
}

export default function AdminAuditLogsPage() {
  const api = useApiClient();
  const [search, setSearch] = useState('');

  const { data: logs = [], isLoading } = useQuery<AuditLogRes[]>({
    queryKey: ['admin-audit-logs'],
    queryFn: () => api.get<AuditLogRes[]>('/analytics/audit-logs'),
  });

  const filtered = logs.filter(
    (l) =>
      l.action.toLowerCase().includes(search.toLowerCase()) ||
      (l.actorEmail && l.actorEmail.toLowerCase().includes(search.toLowerCase())) ||
      (l.entityType && l.entityType.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="System Audit Logs & Security History"
        description="Immutable audit record of administrative actions, roster modifications, exam scheduling, and security events."
      />

      <div className="flex items-center gap-4 max-w-md">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search audit logs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 glass-input"
          />
        </div>
      </div>

      <Card className="glass-card">
        <CardContent className="p-0 divide-y divide-border/40">
          {isLoading ? (
            <div className="p-8 text-center text-muted-foreground flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading audit logs from PostgreSQL...
            </div>
          ) : !filtered.length ? (
            <div className="p-8 text-center text-muted-foreground">No audit logs found.</div>
          ) : (
            filtered.map((log) => (
              <div key={log.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="font-bold bg-primary/10 text-primary border-primary/20">
                      {log.action}
                    </Badge>
                    <span className="font-semibold text-foreground">
                      Entity: {log.entityType} {log.entityId ? `(#${log.entityId.slice(0, 8)})` : ''}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-muted-foreground">
                    <span>
                      Actor: <strong className="text-foreground">{log.actorEmail}</strong>
                    </span>
                    {log.ipAddress && <span>IP: {log.ipAddress}</span>}
                  </div>
                </div>
                <span className="text-muted-foreground whitespace-nowrap font-mono text-[11px]">
                  {log.createdAt ? formatDate(log.createdAt) : 'N/A'}
                </span>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
