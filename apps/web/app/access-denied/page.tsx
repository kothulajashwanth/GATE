'use client';

import { useUser, useClerk } from '@clerk/nextjs';
import { Card, CardContent, Button } from '@examshield/ui';
import { ShieldX, LogOut, LayoutDashboard } from 'lucide-react';
import Link from 'next/link';

export default function AccessDeniedPage() {
  const { user } = useUser();
  const { signOut } = useClerk();

  const email = user?.primaryEmailAddress?.emailAddress?.toLowerCase() ?? '';
  const username = user?.username?.toLowerCase() ?? '';
  const role = (
    (user?.publicMetadata?.role as string) ||
    (user?.unsafeMetadata?.role as string) ||
    (email === 'kothulajashwanth@gmail.com' || username === 'admin' ? 'admin' : 'student')
  ).toLowerCase();

  const isAdmin = role === 'admin' || role === 'super_admin';
  const targetHome = isAdmin ? '/admin' : '/student';

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background p-4 sm:p-8">
      <Card className="w-full max-w-md border-destructive/30 shadow-xl overflow-hidden">
        <div className="h-2 bg-destructive" />
        <CardContent className="p-8 text-center space-y-6">
          <div className="mx-auto w-16 h-16 rounded-2xl bg-destructive/10 text-destructive flex items-center justify-center border border-destructive/20 shadow-inner">
            <ShieldX className="h-8 w-8" />
          </div>

          <div className="space-y-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Unauthorized Access</h1>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Your account (<span className="font-semibold text-foreground">{email || 'signed in'}</span>) does not have permission to access this module.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-muted/40 border text-xs text-muted-foreground space-y-1">
            <p className="font-semibold text-foreground">Assigned Role: <span className="uppercase text-destructive font-bold">{role}</span></p>
            <p>Access to administrative portals is strictly restricted to verified Administrator accounts.</p>
          </div>

          <div className="flex flex-col gap-3 pt-2">
            <Button asChild size="lg" className="w-full">
              <Link href={targetHome}>
                <LayoutDashboard className="h-4 w-4 mr-2" /> Go to Your Portal ({role})
              </Link>
            </Button>

            <Button
              variant="outline"
              size="lg"
              className="w-full text-muted-foreground"
              onClick={() => signOut({ redirectUrl: '/login' })}
            >
              <LogOut className="h-4 w-4 mr-2" /> Sign Out & Switch Account
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
