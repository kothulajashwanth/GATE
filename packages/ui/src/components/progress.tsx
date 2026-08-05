'use client';

import * as React from 'react';
import { cn } from '@examshield/utils';

function Progress({ className, value, ...props }: React.HTMLAttributes<HTMLDivElement> & { value?: number }) {
  return (
    <div
      className={cn('relative h-2 w-full overflow-hidden rounded-full bg-secondary', className)}
      {...props}
    >
      <div
        className="h-full bg-primary transition-all duration-300"
        style={{ width: `${Math.min(100, Math.max(0, value ?? 0))}%` }}
      />
    </div>
  );
}

Progress.displayName = 'Progress';

export { Progress };