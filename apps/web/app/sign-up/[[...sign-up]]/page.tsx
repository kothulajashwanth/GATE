import { SignUp } from '@clerk/nextjs';
import { APP_NAME } from '@/lib/constants';

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-muted/40 p-4">
      <div className="text-center">
        <h1 className="text-2xl font-bold tracking-tight">{APP_NAME}</h1>
        <p className="text-sm text-muted-foreground">Create your student account</p>
      </div>
      <SignUp appearance={{ variables: { colorPrimary: 'hsl(220 70% 45%)' } }} />
    </div>
  );
}
