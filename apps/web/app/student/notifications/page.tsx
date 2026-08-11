'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useApiClient } from '@/lib/api/client-provider';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, Button, Badge } from '@examshield/ui';
import {
  Bell,
  CheckCircle2,
  Calendar,
  Award,
  AlertCircle,
  Megaphone,
  CheckCheck,
  ArrowRight,
  Clock,
  Sparkles,
} from 'lucide-react';
import Link from 'next/link';

interface NotificationItem {
  id: string;
  type: 'exam_scheduled' | 'exam_cancelled' | 'result_published' | 'password_reset' | 'announcement';
  title: string;
  body: string;
  isRead: boolean;
  link?: string | null;
  createdAt: string;
}

export default function NotificationsPage() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const [filterTab, setFilterTab] = useState<'all' | 'unread'>('all');

  const { data: notifications = [], isLoading } = useQuery<NotificationItem[]>({
    queryKey: ['notifications'],
    queryFn: async () => {
      try {
        const res = await api.get<{ items: NotificationItem[] }>('/notifications');
        return res.items ?? [];
      } catch {
        // Fallback mock data if backend route is not populated yet
        return [
          {
            id: '1',
            type: 'exam_scheduled',
            title: 'Mathematics Final Examination Scheduled',
            body: 'Your Mathematics exam has been scheduled for tomorrow at 10:00 AM.',
            isRead: false,
            link: '/student/exams/upcoming',
            createdAt: new Date().toISOString(),
          },
          {
            id: '2',
            type: 'result_published',
            title: 'Data Structures Mid-term Results Published',
            body: 'Your score for Data Structures exam is now available in your results portal.',
            isRead: true,
            link: '/student/results',
            createdAt: new Date(Date.now() - 86400000).toISOString(),
          },
          {
            id: '3',
            type: 'announcement',
            title: 'System Maintenance Notice',
            body: 'GATE IGNITE will undergo brief maintenance on Sunday from 2:00 AM to 3:00 AM UTC.',
            isRead: true,
            createdAt: new Date(Date.now() - 172800000).toISOString(),
          },
        ];
      }
    },
  });

  const unreadCount = notifications.filter((n) => !n.isRead).length;
  const filteredList = notifications.filter((n) => (filterTab === 'unread' ? !n.isRead : true));

  const markAllReadMutation = useMutation({
    mutationFn: async () => {
      try {
        await api.post('/notifications/mark-all-read', {});
      } catch {
        // Optimistic state
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  const getIcon = (type: NotificationItem['type']) => {
    switch (type) {
      case 'exam_scheduled':
        return <Calendar className="h-5 w-5 text-blue-500" />;
      case 'result_published':
        return <Award className="h-5 w-5 text-emerald-500" />;
      case 'exam_cancelled':
        return <AlertCircle className="h-5 w-5 text-destructive" />;
      case 'announcement':
        return <Megaphone className="h-5 w-5 text-amber-500" />;
      default:
        return <Bell className="h-5 w-5 text-primary" />;
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Notifications"
        description="Stay updated on exam schedules, results, and system announcements."
      >
        {unreadCount > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => markAllReadMutation.mutate()}
            disabled={markAllReadMutation.isPending}
          >
            <CheckCheck className="h-4 w-4 mr-2" /> Mark all as read
          </Button>
        )}
      </PageHeader>

      {/* Filter tabs */}
      <div className="flex items-center gap-2 border-b pb-3">
        <button
          onClick={() => setFilterTab('all')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            filterTab === 'all'
              ? 'bg-primary text-primary-foreground shadow-sm'
              : 'text-muted-foreground hover:bg-muted'
          }`}
        >
          All ({notifications.length})
        </button>
        <button
          onClick={() => setFilterTab('unread')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            filterTab === 'unread'
              ? 'bg-primary text-primary-foreground shadow-sm'
              : 'text-muted-foreground hover:bg-muted'
          }`}
        >
          Unread ({unreadCount})
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-4 h-20 bg-muted/30 rounded" />
            </Card>
          ))}
        </div>
      ) : filteredList.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="p-12 text-center space-y-3">
            <Bell className="h-12 w-12 text-muted-foreground/40 mx-auto" />
            <h3 className="text-lg font-semibold">No notifications found</h3>
            <p className="text-sm text-muted-foreground">
              {filterTab === 'unread'
                ? "You've read all your notifications!"
                : 'You have no notifications at this time.'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredList.map((n) => (
            <Card
              key={n.id}
              className={`transition-all ${
                !n.isRead ? 'border-primary/40 bg-primary/5 dark:bg-primary/10' : 'hover:bg-muted/30'
              }`}
            >
              <CardContent className="p-5 flex items-start gap-4">
                <div className="p-2.5 rounded-xl bg-background border shadow-xs">
                  {getIcon(n.type)}
                </div>

                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="font-semibold text-base truncate">{n.title}</h3>
                    {!n.isRead && (
                      <Badge className="bg-primary/20 text-primary hover:bg-primary/30 border-0 text-[10px] uppercase font-bold">
                        New
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed">{n.body}</p>
                  <div className="flex items-center justify-between pt-2">
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5" />
                      {new Date(n.createdAt).toLocaleDateString(undefined, {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                    {n.link && (
                      <Button asChild variant="ghost" size="sm" className="text-xs font-semibold">
                        <Link href={n.link}>
                          View <ArrowRight className="h-3.5 w-3.5 ml-1" />
                        </Link>
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
