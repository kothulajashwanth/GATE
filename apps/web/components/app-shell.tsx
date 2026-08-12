'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { UserButton } from '@clerk/nextjs';
import { ShieldCheck, Menu, X, Sparkles } from 'lucide-react';
import { cn } from '@examshield/utils';
import { ThemeToggle } from './theme-toggle';
import { APP_NAME } from '@/lib/constants';
import { useState, useEffect } from 'react';

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

export function AppShell({ items, children, role }: AppShellProps) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div className="relative min-h-screen bg-background bg-ambient-light">
      {/* Liquid Glass Desktop Sidebar */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col glass-sidebar lg:flex">
        <div className="flex h-16 items-center gap-3 border-b border-border/50 px-6">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 border border-primary/20 text-primary shadow-sm">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-bold tracking-tight text-foreground">{APP_NAME}</span>
            <span className="text-[10px] text-muted-foreground uppercase font-mono tracking-widest">Liquid Glass Portal</span>
          </div>
        </div>

        <nav className="flex-1 space-y-1 px-4 py-4">
          {items.map((item) => {
            const isActive = pathname === item.href || (item.href !== '/admin' && item.href !== '/student' && pathname.startsWith(item.href));
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 rounded-xl px-3 py-2.5 text-xs font-semibold transition-all duration-200',
                  isActive
                    ? 'glass-card bg-primary/10 text-primary border-primary/20 shadow-sm'
                    : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground'
                )}
              >
                <Icon className={cn('h-4 w-4', isActive ? 'text-primary' : 'text-muted-foreground')} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-border/50 p-4">
          <div className="flex items-center justify-between rounded-xl bg-muted/40 p-3 border border-border/40">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-amber-500" />
              <span className="text-xs font-medium text-foreground capitalize">{role} Account</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Mobile Sidebar */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="fixed inset-0 bg-background/80 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <div className="fixed inset-y-0 left-0 w-64 glass-sidebar p-4 shadow-2xl flex flex-col">
            <div className="flex items-center justify-between border-b border-border/50 pb-4 mb-4">
              <span className="text-sm font-bold text-foreground">{APP_NAME}</span>
              <button onClick={() => setMobileOpen(false)} className="p-1 rounded-lg hover:bg-muted">
                <X className="h-5 w-5" />
              </button>
            </div>
            <nav className="space-y-1 flex-1">
              {items.map((item) => {
                const isActive = pathname === item.href;
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileOpen(false)}
                    className={cn(
                      'flex items-center gap-3 rounded-xl px-3 py-2.5 text-xs font-semibold transition-all',
                      isActive ? 'bg-primary/10 text-primary font-bold' : 'text-muted-foreground hover:bg-muted'
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="lg:pl-64 flex flex-col min-h-screen">
        {/* Glass Top Header Navbar */}
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between glass-navbar px-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileOpen(true)}
              className="p-2 rounded-xl border border-border/50 hover:bg-muted lg:hidden"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="hidden sm:flex flex-col">
              <span className="text-xs font-bold text-foreground capitalize">
                {pathname?.split('/')[2] ? pathname.split('/')[2]?.replace('-', ' ') : 'Dashboard'}
              </span>
              <span className="text-[10px] text-muted-foreground font-mono">GATE IGNITE Platform</span>
            </div>
          </div>

          <div className="flex items-center gap-3" suppressHydrationWarning>
            <ThemeToggle />
            <div className="h-5 w-[1px] bg-border/60" />
            {mounted ? <UserButton afterSignOutUrl="/" /> : <div className="h-7 w-7 rounded-full bg-muted animate-pulse" />}
          </div>
        </header>

        <main className="flex-1 p-6 z-10">{children}</main>
      </div>
    </div>
  );
}
