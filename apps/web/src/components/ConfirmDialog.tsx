import { useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  destructive = true,
  busy = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !busy) {
        onCancel();
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [open, busy, onCancel]);

  if (!open) return null;

  return (
    <div
      className="modal-overlay"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget && !busy) onCancel();
      }}
    >
      <div
        className="modal-card modal-card-sm"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-desc"
      >
        <div className="row-wrap" style={{ alignItems: 'flex-start' }}>
          <span
            className="metric-icon"
            style={{
              background: destructive ? 'var(--color-danger-soft)' : 'var(--color-primary-soft)',
              color: destructive ? 'var(--color-danger-text)' : 'var(--color-primary-text)',
            }}
          >
            <AlertTriangle size={18} aria-hidden="true" />
          </span>
          <div style={{ flex: 1 }}>
            <h2 id="confirm-dialog-title" className="section-title">
              {title}
            </h2>
            <p id="confirm-dialog-desc" className="meta-text" style={{ marginTop: 6 }}>
              {description}
            </p>
          </div>
        </div>

        <div className="row-wrap" style={{ justifyContent: 'flex-end', marginTop: 8 }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onCancel}
            disabled={busy}
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            className={`btn ${destructive ? 'btn-danger' : 'btn-primary'}`}
            onClick={onConfirm}
            disabled={busy}
          >
            {busy ? 'Working...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
