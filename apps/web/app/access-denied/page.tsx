'use client';

import { useUser } from '@clerk/nextjs';
import { AccessDeniedModal } from '@/components/access-denied-modal';

export default function AccessDeniedPage() {
  const { user } = useUser();
  const email = user?.primaryEmailAddress?.emailAddress?.toLowerCase() ?? '';

  return <AccessDeniedModal userEmail={email} />;
}
