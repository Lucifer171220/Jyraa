'use client';

import { AppFrame } from '@/app/AppFrame';

export function ClientComponents({ children }: { children: React.ReactNode }) {
  return <AppFrame>{children}</AppFrame>;
}
