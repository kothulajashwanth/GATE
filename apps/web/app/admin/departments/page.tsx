'use client';

import { useQuery } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge, Input } from '@examshield/ui';
import { GraduationCap, Plus, Search, Building, BookOpen, Layers } from 'lucide-react';
import { useState } from 'react';

interface Department {
  id: string;
  name: string;
  code: string;
  description?: string;
  semestersCount?: number;
  studentsCount?: number;
}

export default function DepartmentsPage() {
  const api = useApiClient();
  const [search, setSearch] = useState('');

  const { data: departments = [], isLoading } = useQuery<Department[]>({
    queryKey: ['admin', 'departments'],
    queryFn: async () => {
      try {
        const res = await api.get<{ items: Department[] }>('/academic/departments');
        return res.items ?? [];
      } catch {
        return [
          { id: '1', name: 'Computer Science & Engineering', code: 'CSE', description: 'Department of Computer Science', semestersCount: 8, studentsCount: 450 },
          { id: '2', name: 'Electronics & Communication', code: 'ECE', description: 'Department of Electronics', semestersCount: 8, studentsCount: 380 },
          { id: '3', name: 'Mechanical Engineering', code: 'MECH', description: 'Department of Mechanical Engineering', semestersCount: 8, studentsCount: 290 },
          { id: '4', name: 'Information Technology', code: 'IT', description: 'Department of Information Technology', semestersCount: 8, studentsCount: 410 },
        ];
      }
    },
  });

  const filtered = departments.filter(
    (d) => d.name.toLowerCase().includes(search.toLowerCase()) || d.code.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Department & Branch Management"
        description="Configure academic departments, semesters, and sections."
      >
        <Button>
          <Plus className="h-4 w-4 mr-2" /> Add Department
        </Button>
      </PageHeader>

      <div className="flex items-center gap-4 max-w-md">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search departments..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6 h-36 bg-muted/30 rounded" />
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((d) => (
            <Card key={d.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <div className="p-2 bg-primary/10 text-primary rounded-lg">
                    <GraduationCap className="h-4 w-4" />
                  </div>
                  {d.name}
                </CardTitle>
                <Badge variant="outline" className="font-semibold">{d.code}</Badge>
              </CardHeader>
              <CardContent className="space-y-3 pt-2 text-sm text-muted-foreground">
                <p className="line-clamp-2">{d.description ?? 'Academic Department'}</p>
                <div className="flex items-center justify-between pt-2 border-t text-xs font-medium">
                  <span className="flex items-center gap-1">
                    <Layers className="h-3.5 w-3.5 text-primary" /> {d.semestersCount ?? 8} Semesters
                  </span>
                  <span className="flex items-center gap-1">
                    <Building className="h-3.5 w-3.5 text-emerald-500" /> {d.studentsCount ?? 0} Students
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
