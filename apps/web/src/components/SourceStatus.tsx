import { AlertTriangle, CheckCircle2, HelpCircle, PauseCircle, XCircle } from 'lucide-react';

interface SourceStatusProps {
  status: string;
}

export function SourceStatus({ status }: SourceStatusProps) {
  const normalized = status.toLowerCase();

  if (normalized === 'active' || normalized === 'succeeded' || normalized === 'healthy') {
    return (
      <span className="badge badge-success">
        <CheckCircle2 size={12} aria-hidden="true" />
        <span>{normalized === 'succeeded' ? 'Succeeded' : normalized === 'healthy' ? 'Healthy' : 'Active'}</span>
      </span>
    );
  }

  if (normalized === 'paused' || normalized === 'idle' || normalized === 'skipped') {
    return (
      <span className="badge badge-neutral">
        <PauseCircle size={12} aria-hidden="true" />
        <span>
          {normalized === 'paused'
            ? 'Paused'
            : normalized === 'skipped'
              ? 'Skipped'
              : 'Idle'}
        </span>
      </span>
    );
  }

  if (normalized === 'unsupported') {
    return (
      <span className="badge badge-warning">
        <HelpCircle size={12} aria-hidden="true" />
        <span>Unsupported Source</span>
      </span>
    );
  }

  if (normalized === 'degraded') {
    return (
      <span className="badge badge-warning">
        <AlertTriangle size={12} aria-hidden="true" />
        <span>Degraded</span>
      </span>
    );
  }

  return (
    <span className="badge badge-danger">
      <XCircle size={12} aria-hidden="true" />
      <span>{normalized === 'failed' ? 'Failed' : 'Error'}</span>
    </span>
  );
}
