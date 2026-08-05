'use client';

import { useUser } from '@clerk/nextjs';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle, Badge, Button } from '@examshield/ui';
import { User, Mail, Shield, Calendar, BookOpen, Building } from 'lucide-react';

export default function ProfilePage() {
  const { user, isLoaded } = useUser();

  if (!isLoaded) {
    return (
      <div className="space-y-4">
        <PageHeader title="Student Profile" description="Your account information and settings." />
        <Card className="animate-pulse">
          <CardContent className="p-8 h-48 bg-muted/30 rounded" />
        </Card>
      </div>
    );
  }

  const role = (user?.publicMetadata?.role as string) || 'student';
  const primaryEmail = user?.primaryEmailAddress?.emailAddress || 'No email associated';

  return (
    <div className="space-y-6">
      <PageHeader
        title="Student Profile"
        description="View your enrolled identity and examination access permissions."
      />

      <Card className="overflow-hidden border">
        <div className="h-24 bg-gradient-to-r from-primary/20 via-primary/10 to-background border-b" />
        <CardContent className="p-6 relative pt-0">
          <div className="flex flex-col sm:flex-row items-start sm:items-end justify-between gap-4 -mt-12 mb-6">
            <div className="flex items-end gap-4">
              <div className="h-20 w-20 rounded-2xl bg-primary text-primary-foreground flex items-center justify-center text-2xl font-bold border-4 border-background shadow-lg overflow-hidden">
                {user?.imageUrl ? (
                  <img src={user.imageUrl} alt={user.fullName ?? 'User'} className="h-full w-full object-cover" />
                ) : (
                  user?.firstName?.[0] ?? 'S'
                )}
              </div>
              <div className="mb-1">
                <h2 className="text-xl font-bold tracking-tight">{user?.fullName ?? 'Student Account'}</h2>
                <p className="text-sm text-muted-foreground flex items-center gap-1.5 mt-0.5">
                  <Mail className="h-3.5 w-3.5" /> {primaryEmail}
                </p>
              </div>
            </div>

            <Badge variant="outline" className="capitalize px-3 py-1 bg-background text-sm font-semibold">
              <Shield className="h-3.5 w-3.5 mr-1.5 text-primary" /> {role} Role
            </Badge>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 pt-4 border-t">
            <div className="p-4 rounded-xl bg-muted/30 border space-y-1">
              <p className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                <Building className="h-3.5 w-3.5" /> Department
              </p>
              <p className="text-sm font-semibold">Computer Science & Engineering</p>
            </div>

            <div className="p-4 rounded-xl bg-muted/30 border space-y-1">
              <p className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                <BookOpen className="h-3.5 w-3.5" /> Academic Batch
              </p>
              <p className="text-sm font-semibold">Semester 6 • 2026 Batch</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
