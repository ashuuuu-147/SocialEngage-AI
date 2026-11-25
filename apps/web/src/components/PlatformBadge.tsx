import { Briefcase, Camera } from 'lucide-react';
import type { PlatformType } from '../lib/types';

export function PlatformBadge({ platform }: { platform: PlatformType | string }) {
  const isLinkedIn = platform === 'linkedin';
  return (
    <span className={`badge ${isLinkedIn ? 'badge-primary' : 'badge-neutral'}`}>
      {isLinkedIn ? (
        <Briefcase size={12} aria-hidden="true" />
      ) : (
        <Camera size={12} aria-hidden="true" />
      )}
      <span>{isLinkedIn ? 'LinkedIn' : 'Instagram'}</span>
    </span>
  );
}
