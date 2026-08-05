'use client';

import { Button } from '@examshield/ui';

export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background text-center text-foreground">
        <h1 className="text-2xl font-semibold">Something went wrong</h1>
        <p className="max-w-sm text-muted-foreground">
          An unexpected error occurred. Please try reloading the page.
        </p>
        <Button onClick={reset}>Try again</Button>
      </body>
    </html>
  );
}
