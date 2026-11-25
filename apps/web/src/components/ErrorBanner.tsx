import { AlertCircle, RefreshCw, X } from 'lucide-react';

interface ErrorBannerProps {
  title?: string;
  message: string;
  code?: string;
  requestId?: string;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export function ErrorBanner({
  title = 'Something went wrong',
  message,
  code,
  requestId,
  onRetry,
  onDismiss,
}: ErrorBannerProps) {
  return (
    <div className="error-banner" role="alert">
      <div className="error-banner-body">
        <AlertCircle size={18} style={{ flexShrink: 0, marginTop: 2 }} aria-hidden="true" />
        <div className="stack-sm" style={{ gap: 4 }}>
          <strong style={{ fontSize: 14 }}>{title}</strong>
          <p style={{ fontSize: 13 }}>{message}</p>
          {(code || requestId) && (
            <p style={{ fontSize: 12, opacity: 0.85 }}>
              {code ? `Code: ${code}` : ''}
              {code && requestId ? ' · ' : ''}
              {requestId ? `Request ID: ${requestId}` : ''}
            </p>
          )}
        </div>
      </div>
      <div className="row-wrap" style={{ gap: 6 }}>
        {onRetry && (
          <button type="button" className="btn btn-secondary btn-sm" onClick={onRetry}>
            <RefreshCw size={14} aria-hidden="true" />
            Retry
          </button>
        )}
        {onDismiss && (
          <button
            type="button"
            className="btn btn-ghost btn-icon"
            onClick={onDismiss}
            aria-label="Dismiss error"
          >
            <X size={16} aria-hidden="true" />
          </button>
        )}
      </div>
    </div>
  );
}
