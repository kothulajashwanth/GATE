'use client';

import { useUser } from '@clerk/nextjs';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle, Badge, Button } from '@examshield/ui';
import { User, ShieldCheck, Mail, Key } from 'lucide-react';

export default function AdminProfilePage() {
  const { user } = useUser();

  const email = user?.primaryEmailAddress?.emailAddress ?? 'kothulajashwanth@gmail.com';
  const username = user?.username ?? 'admin';

  return (
    <div className="space-y-6 max-w-3xl">
      <PageHeader title="Administrator Profile" description="Your authenticated administrator identity and system credentials." />

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-bold flex items-center gap-2">
            <User className="h-5 w-5 text-primary" /> Profile Identity
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div className="flex items-center gap-4 p-4 rounded-xl bg-muted/30 border">
            <div className="w-14 h-14 rounded-2xl bg-amber-500/10 text-amber-500 font-bold text-xl flex items-center justify-center border border-amber-500/20">
              {email.slice(0, 1).toUpperCase()}
            </div>
            <div>
              <h3 className="font-bold text-base">{email}</h3>
              <p className="text-xs text-muted-foreground">Username: <span className="font-medium text-foreground">{username}</span></p>
              <Badge className="mt-1 bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30">
                <ShieldCheck className="h-3 w-3 mr-1" /> SYSTEM ADMINISTRATOR
              </Badge>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 text-xs">
            <div className="p-3 bg-muted/20 rounded-lg border">
              <span className="text-muted-foreground block">Clerk User ID</span>
              <span className="font-mono text-foreground font-semibold">{user?.id ?? 'user_3HVXV8AB0gCdYtGagjNxwn0XIgF'}</span>
            </div>
            <div className="p-3 bg-muted/20 rounded-lg border">
              <span className="text-muted-foreground block">Assigned Role</span>
              <span className="font-bold text-emerald-600 uppercase">SUPER ADMIN</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
