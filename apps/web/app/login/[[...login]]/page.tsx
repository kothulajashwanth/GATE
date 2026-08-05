import { SignIn } from '@clerk/nextjs';
import { APP_NAME } from '@/lib/constants';
import Link from 'next/link';
import { ShieldAlert } from 'lucide-react';

export default function StudentLoginPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-gradient-to-b from-background via-muted/20 to-muted/40 p-4 sm:p-8">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-2">
          <div className="mx-auto w-12 h-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mb-3">
            <ShieldAlert className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">{APP_NAME}</h1>
          <p className="text-sm text-muted-foreground">Student Examination Portal Sign In</p>
        </div>

        <div className="bg-card border shadow-sm rounded-2xl p-6">
          <SignIn
            appearance={{
              variables: { colorPrimary: 'hsl(220 70% 45%)' },
              elements: {
                card: 'shadow-none p-0 border-0 bg-transparent',
                rootBox: 'w-full',
              },
            }}
            forceRedirectUrl="/student"
            signUpUrl="/sign-up"
          />

          <div className="mt-6 pt-6 border-t border-border text-center space-y-1.5">
            <p className="text-sm font-medium text-foreground">Are you an Administrator?</p>
            <Link
              href="/portal/admin/login"
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-primary hover:underline"
            >
              Login to the Admin Portal →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
