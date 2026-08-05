'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { UserButton } from '@clerk/nextjs';
import { ShieldCheck } from 'lucide-react';
import { cn } from '@examshield/utils';
import { ThemeToggle } from './theme-toggle';
import { APP_NAME } from '@/lib/constants';

export interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface AppShellProps {
  items: NavItem[];
  children: React.ReactNode;
  role: string;
}

/**
 * Shared portal chrome: fixed sidebar (collapsible on mobile), top bar with
 * theme toggle and account menu, scrollable content region.
 */
export function AppShell({ items, children, role }: AppShellProps) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen bg-muted/30">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r bg-background lg:flex">
        <div className="flex h-16 items-center gap-2 border-b px-6">
          <ShieldCheck className="h-6 w-6 text-primary" />
          <span className="text-sm font-semibold tracking-tight">{APP_NAME}</span>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {items.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  active
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:bg-accent hover:text-foreground',
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t p-3 text-xs text-muted-foreground">
          Signed in as <span className="font-medium capitalize">{role.replace('_', ' ')}</span>
        </div>
      </aside>

      <div className="flex flex-1 flex-col lg:pl-64">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-background/95 px-6 backdrop-blur">
          <div className="lg:hidden">
            <span className="font-semibold">{APP_NAME}</span>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            <UserButton afterSignOutUrl="/" />
          </div>
        </header>
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
