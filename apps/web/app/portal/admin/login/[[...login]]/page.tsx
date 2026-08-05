import { SignIn } from '@clerk/nextjs';
import { APP_NAME } from '@/lib/constants';
import Link from 'next/link';
import { ShieldCheck, Lock } from 'lucide-react';

export default function AdminLoginPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-slate-950 dark:bg-slate-950 text-slate-100 p-4 sm:p-8">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-2">
          <div className="mx-auto w-14 h-14 rounded-2xl bg-amber-500/10 text-amber-500 flex items-center justify-center mb-3 border border-amber-500/20 shadow-inner">
            <ShieldCheck className="h-7 w-7" />
          </div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 mb-2">
            <Lock className="h-3 w-3" /> RESTRICTED ACCESS
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">{APP_NAME}</h1>
          <p className="text-sm text-slate-400">Administrator Management Portal</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 shadow-2xl rounded-2xl p-6">
          <SignIn
            appearance={{
              variables: { colorPrimary: 'hsl(38 92% 50%)' },
              elements: {
                card: 'shadow-none p-0 border-0 bg-transparent',
                rootBox: 'w-full',
              },
            }}
            forceRedirectUrl="/admin"
          />

          <div className="mt-6 pt-6 border-t border-slate-800 text-center space-y-1.5">
            <p className="text-xs text-slate-400">Student looking for your exams?</p>
            <Link
              href="/login"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-amber-400 hover:underline"
            >
              Go to Student Login →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
