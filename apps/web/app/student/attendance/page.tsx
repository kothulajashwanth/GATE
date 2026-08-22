'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function StudentAttendancePage() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/student');
  }, [router]);

  return null;
}
