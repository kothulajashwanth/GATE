'use client';

'use client';

import { useState } from 'react';
import {
  Card, CardContent, CardHeader, CardTitle, Button, Input, Badge,
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Label,
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '@examshield/ui';
import { MoreHorizontal, Plus, Search, Download, Upload } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import { DataTablePagination } from '@/components/data-table-pagination';
import { EmptyState } from '@/components/empty-state';
import { toast } from 'sonner';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import type { Paginated } from '@examshield/types';
import { downloadBlob } from '@examshield/utils';

interface StudentRow {
  id: string;
  rollNumber: string;
  name: string;
  email: string;
  phone: string | null;
  isActive: boolean;
  department: { id: string; name: string } | null;
  semester: { id: string; name: string } | null;
  section: { id: string; name: string } | null;
}

const studentSchema = z.object({
  rollNumber: z.string().min(1, 'Roll number required'),
  email: z.string().email('Invalid email'),
  firstName: z.string().min(1, 'First name required'),
  lastName: z.string().optional(),
  phone: z.string().optional(),
  departmentId: z.string().min(1, 'Department required'),
  semesterId: z.string().min(1, 'Semester required'),
  sectionId: z.string().min(1, 'Section required'),
  parentName: z.string().optional(),
  parentPhone: z.string().optional(),
});
type StudentForm = z.infer<typeof studentSchema>;

function CreateStudentDialog({ onCreated }: { onCreated: () => void }) {
  const api = useApiClient();
  const { register, handleSubmit, reset, watch, formState: { errors } } = useForm<StudentForm>({
    resolver: zodResolver(studentSchema),
  });
  const [open, setOpen] = useState(false);

  const departmentId = watch('departmentId');
  const semesterId = watch('semesterId');

  const { data: departments } = useQuery({
    queryKey: ['departments'],
    queryFn: () => api.get<{ id: string; name: string; code: string }[]>('/academic/departments'),
  });
  const { data: semesters } = useQuery({
    queryKey: ['semesters', departmentId],
    queryFn: () => api.get<{ id: string; name: string }[]>(`/academic/departments/${departmentId}/semesters`),
    enabled: !!departmentId,
  });
  const { data: sections } = useQuery({
    queryKey: ['sections', semesterId],
    queryFn: () => api.get<{ id: string; name: string }[]>(`/academic/semesters/${semesterId}/sections`),
    enabled: !!semesterId,
  });

  const mutation = useMutation({
    mutationFn: (values: StudentForm) => api.post('/students', values),
    onSuccess: () => {
      toast.success('Student created');
      setOpen(false);
      reset();
      onCreated();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm"><Plus className="h-4 w-4" /> Add Student</Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add Student</DialogTitle>
          <DialogDescription>Create a student account and assign placement.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit((v) => mutation.mutate(v))} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Roll Number</Label>
              <Input {...register('rollNumber')} placeholder="e.g. CS2024001" />
              {errors.rollNumber && <p className="text-xs text-destructive">{errors.rollNumber.message}</p>}
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input type="email" {...register('email')} placeholder="student@college.edu" />
              {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
            </div>
            <div className="space-y-2">
              <Label>First Name</Label>
              <Input {...register('firstName')} />
              {errors.firstName && <p className="text-xs text-destructive">{errors.firstName.message}</p>}
            </div>
            <div className="space-y-2">
              <Label>Last Name</Label>
              <Input {...register('lastName')} />
            </div>
            <div className="space-y-2">
              <Label>Phone</Label>
              <Input {...register('phone')} placeholder="+91..." />
            </div>
            <div className="space-y-2">
              <Label>Parent Name</Label>
              <Input {...register('parentName')} />
            </div>
            <div className="space-y-2">
              <Label>Parent Phone</Label>
              <Input {...register('parentPhone')} />
            </div>
            <div className="space-y-2">
              <Label>Department</Label>
              <Select value={departmentId} onValueChange={(v) => register('departmentId').onChange({ target: { value: v } })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select department" />
                </SelectTrigger>
                <SelectContent>
                  {departments?.map((d) => <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Semester</Label>
              <Select value={semesterId} onValueChange={(v) => register('semesterId').onChange({ target: { value: v } })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select semester" />
                </SelectTrigger>
                <SelectContent>
                  {semesters?.map((s) => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Section</Label>
              <Select value={watch('sectionId')} onValueChange={(v) => register('sectionId').onChange({ target: { value: v } })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select section" />
                </SelectTrigger>
                <SelectContent>
                  {sections?.map((s) => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? 'Creating...' : 'Create Student'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function StudentsPage() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [deptFilter, setDeptFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState('');

  const params: Record<string, unknown> = { page, page_size: 20 };
  if (query) params.query = query;
  if (deptFilter) params.department_id = deptFilter;
  if (activeFilter) params.is_active = activeFilter === 'active';

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['students', params],
    queryFn: () => api.get<Paginated<StudentRow>>('/students', params),
  });

  const { data: departments } = useQuery({
    queryKey: ['departments'],
    queryFn: () => api.get<{ id: string; name: string }[]>('/academic/departments'),
  });

  const toggleActive = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      api.patch(`/students/${id}`, { isActive }),
    onSuccess: () => {
      toast.success('Student status updated');
      queryClient.invalidateQueries({ queryKey: ['students'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteStudent = useMutation({
    mutationFn: (id: string) => api.delete(`/students/${id}`),
    onSuccess: () => {
      toast.success('Student deleted');
      queryClient.invalidateQueries({ queryKey: ['students'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const handleExport = async () => {
    const blob = await api.raw.download('/students/export');
    downloadBlob(blob, `students-${new Date().toISOString().slice(0, 10)}.xlsx`);
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Students" description="Manage student accounts, placements, and status">
        <Button variant="outline" size="sm" onClick={handleExport}><Download className="h-4 w-4" /> Export</Button>
        <CreateStudentDialog onCreated={refetch} />
      </PageHeader>

      <div className="flex flex-col gap-4 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="Search by roll number, name, or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { setQuery(search); setPage(1); } }}
          />
        </div>
        <Select value={deptFilter} onValueChange={(v) => { setDeptFilter(v); setPage(1); }}>
          <SelectTrigger className="w-[200px]"><SelectValue placeholder="All departments" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All departments</SelectItem>
            {departments?.map((d) => <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={activeFilter} onValueChange={(v) => { setActiveFilter(v); setPage(1); }}>
          <SelectTrigger className="w-[150px]"><SelectValue placeholder="All status" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All status</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="inactive">Inactive</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-muted-foreground">Loading...</div>
          ) : !data?.items.length ? (
            <div className="p-8">
              <EmptyState
                title="No students found"
                description="Add students manually or import from Excel."
                action={<CreateStudentDialog onCreated={refetch} />}
              />
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Roll Number</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Department</TableHead>
                    <TableHead>Semester</TableHead>
                    <TableHead>Section</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((student) => (
                    <TableRow key={student.id}>
                      <TableCell className="font-mono text-xs">{student.rollNumber}</TableCell>
                      <TableCell>
                        <div className="font-medium">{student.name}</div>
                        <div className="text-xs text-muted-foreground">{student.email}</div>
                      </TableCell>
                      <TableCell>{student.department?.name ?? '—'}</TableCell>
                      <TableCell>{student.semester?.name ?? '—'}</TableCell>
                      <TableCell>{student.section?.name ?? '—'}</TableCell>
                      <TableCell>
                        <Badge variant={student.isActive ? 'success' : 'destructive'}>
                          {student.isActive ? 'Active' : 'Disabled'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon"><MoreHorizontal className="h-4 w-4" /></Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              onClick={() => toggleActive.mutate({ id: student.id, isActive: !student.isActive })}
                            >
                              {student.isActive ? 'Disable' : 'Activate'}
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              className="text-destructive"
                              onClick={() => { if (confirm(`Delete student ${student.rollNumber}?`)) deleteStudent.mutate(student.id); }}
                            >
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="p-4">
                <DataTablePagination page={page} totalPages={data.totalPages} onPageChange={setPage} />
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}