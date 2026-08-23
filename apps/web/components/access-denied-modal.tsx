'use client';

import { ShieldAlert, Lock, ArrowRight, LogIn } from 'lucide-react';
import { Button } from '@examshield/ui';
import Link from 'next/link';

interface AccessDeniedModalProps {
  userEmail?: string;
}

export function AccessDeniedModal({ userEmail }: AccessDeniedModalProps) {
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-in fade-in duration-200">
      <div className="w-full max-w-md rounded-2xl border border-rose-500/30 bg-slate-900/90 p-6 sm:p-8 text-center shadow-2xl backdrop-blur-xl animate-in zoom-in-95 duration-300 motion-reduce:animate-none space-y-5">
        <div className="mx-auto w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-500 shadow-inner">
          <Lock className="h-8 w-8 animate-pulse text-rose-500" />
        </div>

        <div>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-400 font-extrabold text-[10px] tracking-wider uppercase mb-3">
            <ShieldAlert className="h-3 w-3" /> ADMIN ACCESS REQUIRED
          </span>
          <h2 className="text-2xl font-extrabold tracking-tight text-white">
            Access Restricted
          </h2>
          <p className="text-sm font-medium text-slate-300 mt-2">
            You don't have permission to access the Admin Portal.
          </p>
          <p className="text-xs text-slate-400 mt-1">
            Please sign in with an authorized administrator account to continue.
          </p>
        </div>

        {userEmail && (
          <div className="py-2 px-3 rounded-lg bg-slate-950/60 border border-slate-800 text-[11px] text-slate-400 font-mono">
            Signed in as: <span className="text-slate-200 font-semibold">{userEmail}</span>
          </div>
        )}

        <div className="flex flex-col gap-2.5 pt-2">
          <Button
            asChild
            size="lg"
            className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs cursor-pointer shadow-lg transition-all duration-150 active:scale-[0.98]"
          >
            <Link href="/student">
              Go to Student Portal <ArrowRight className="h-4 w-4 ml-1.5" />
            </Link>
          </Button>

          <Button
            asChild
            variant="outline"
            size="lg"
            className="w-full glass-button text-xs font-semibold cursor-pointer transition-all duration-150 active:scale-[0.98]"
          >
            <Link href="/sign-in">
              <LogIn className="h-4 w-4 mr-1.5 text-muted-foreground" /> Back to Login
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
