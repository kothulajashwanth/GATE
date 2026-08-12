'use client';

import { useUser, useAuth } from '@clerk/nextjs';
import { useQuery } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, Badge } from '@examshield/ui';
import { Mail, Shield, BookOpen, Building, Hash, Phone, Loader2 } from 'lucide-react';

interface StudentProfile {
  id: string;
  rollNumber: string;
  firstName: string;
  lastName: string;
  email: string;
  phone?: string | null;
  department?: { id: string; name: string } | null;
  semester?: { id: string; name: string } | null;
  section?: { id: string; name: string } | null;
}

export default function ProfilePage() {
  const api = useApiClient();
  const { user, isLoaded: userLoaded } = useUser();
  const { isLoaded: authLoaded, isSignedIn } = useAuth();

  const { data: profile, isLoading } = useQuery<StudentProfile>({
    queryKey: ['student', 'profile', authLoaded, isSignedIn],
    queryFn: () => api.get<StudentProfile>('/student/profile'),
    enabled: authLoaded && isSignedIn,
    retry: 2,
  });

  if (!userLoaded || isLoading) {
    return (
      <div className="space-y-4">
        <PageHeader title="Student Profile" description="Your account information and settings." />
        <Card className="animate-pulse glass-card">
          <CardContent className="p-8 h-48 bg-muted/30 rounded flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-primary mr-2" /> Loading student profile from PostgreSQL...
          </CardContent>
        </Card>
      </div>
    );
  }

  const role = (user?.publicMetadata?.role as string) || 'student';
  const primaryEmail = profile?.email || user?.primaryEmailAddress?.emailAddress || 'No email associated';
  const rollNumber = profile?.rollNumber || 'STU-PROVISIONED';
  const departmentName = profile?.department?.name || 'General Engineering';
  const semesterName = profile?.semester?.name || 'Academic Semester';
  const sectionName = profile?.section?.name || 'Section A';

  return (
    <div className="space-y-6">
      <PageHeader
        title="Student Profile"
        description="View your enrolled identity, roll number, department, and examination access permissions."
      />

      <Card className="glass-card overflow-hidden border">
        <div className="h-28 bg-gradient-to-r from-primary/30 via-primary/10 to-background border-b" />
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
                <h2 className="text-xl font-bold tracking-tight">{user?.fullName ?? `${profile?.firstName} ${profile?.lastName}`}</h2>
                <p className="text-sm text-muted-foreground flex items-center gap-1.5 mt-0.5">
                  <Mail className="h-3.5 w-3.5" /> {primaryEmail}
                </p>
              </div>
            </div>

            <Badge variant="outline" className="capitalize px-3 py-1 bg-background text-sm font-semibold glass-button">
              <Shield className="h-3.5 w-3.5 mr-1.5 text-primary" /> {role} Role
            </Badge>
          </div>

          <div className="grid gap-4 sm:grid-cols-3 pt-4 border-t border-border/40">
            <div className="p-4 rounded-xl glass-card space-y-1">
              <p className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                <Hash className="h-3.5 w-3.5 text-primary" /> Roll Number
              </p>
              <p className="text-base font-bold text-foreground">{rollNumber}</p>
            </div>

            <div className="p-4 rounded-xl glass-card space-y-1">
              <p className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                <Building className="h-3.5 w-3.5 text-primary" /> Department
              </p>
              <p className="text-base font-bold text-foreground">{departmentName}</p>
            </div>

            <div className="p-4 rounded-xl glass-card space-y-1">
              <p className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                <BookOpen className="h-3.5 w-3.5 text-primary" /> Academic Batch & Section
              </p>
              <p className="text-base font-bold text-foreground">{semesterName} • {sectionName}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
