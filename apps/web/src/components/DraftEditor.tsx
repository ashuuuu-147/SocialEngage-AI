import { useEffect, useState } from 'react';
import {
  Archive,
  Check,
  Copy,
  ExternalLink,
  RefreshCw,
  Save,
  SkipForward,
  Trash2,
} from 'lucide-react';
import type { DraftAction, DraftWithPost } from '../lib/types';
import { ConfirmDialog } from './ConfirmDialog';
import { RelevanceBadge } from './RelevanceBadge';

interface DraftEditorProps {
  draft: DraftWithPost;
  onSaveEdit: (draftId: string, editedText: string) => Promise<void>;
  onRegenerate: (
    draftId: string,
    params: { tone: string; length: 'short' | 'medium' | 'detailed'; instruction?: string }
  ) => Promise<void>;
  onMark: (draftId: string, action: DraftAction) => Promise<void>;
  onDelete: (draftId: string) => Promise<void>;
  onCopiedSuccess: () => void;
}

const TONE_OPTIONS = [
  { value: 'professional-conversational', label: 'Professional & Conversational' },
  { value: 'warm-encouraging', label: 'Warm & Encouraging' },
  { value: 'curious-analytical', label: 'Curious & Analytical' },
  { value: 'concise-executive', label: 'Concise & Executive' },
];

const LENGTH_OPTIONS: Array<{ value: 'short' | 'medium' | 'detailed'; label: string }> = [
  { value: 'short', label: 'Short (1–2 sentences)' },
  { value: 'medium', label: 'Medium (2–3 sentences)' },
  { value: 'detailed', label: 'Detailed (3–4 sentences)' },
];

export function DraftEditor({
  draft,
  onSaveEdit,
  onRegenerate,
  onMark,
  onDelete,
  onCopiedSuccess,
}: DraftEditorProps) {
  const activeText = draft.edited_text ?? draft.draft_text;
  const [text, setText] = useState(activeText);
  const [tone, setTone] = useState('professional-conversational');
  const [length, setLength] = useState<'short' | 'medium' | 'detailed'>('short');
  const [instruction, setInstruction] = useState('');
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [copiedRecently, setCopiedRecently] = useState(false);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);

  useEffect(() => {
    setText(draft.edited_text ?? draft.draft_text);
  }, [draft.id, draft.draft_text, draft.edited_text]);

  const isDirty = text.trim() !== activeText.trim();

  async function handleCopy() {
    setBusyAction('copy');
    try {
      if (isDirty) {
        await onSaveEdit(draft.id, text.trim());
      }
      if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
        await navigator.clipboard.writeText(text.trim());
      }
      await onMark(draft.id, 'copied');
      setCopiedRecently(true);
      onCopiedSuccess();
      window.setTimeout(() => setCopiedRecently(false), 2200);
    } finally {
      setBusyAction(null);
    }
  }

  async function handleOpenPost() {
    if (!draft.post?.canonical_url) return;
    window.open(draft.post.canonical_url, '_blank', 'noopener,noreferrer');
    setBusyAction('open');
    try {
      await onMark(draft.id, 'opened');
    } finally {
      setBusyAction(null);
    }
  }

  async function handleSave() {
    if (!text.trim()) return;
    setBusyAction('save');
    try {
      await onSaveEdit(draft.id, text.trim());
    } finally {
      setBusyAction(null);
    }
  }

  async function handleRegenerate() {
    setBusyAction('regenerate');
    try {
      await onRegenerate(draft.id, {
        tone,
        length,
        instruction: instruction.trim() || undefined,
      });
      setInstruction('');
    } finally {
      setBusyAction(null);
    }
  }

  async function handleMarkAction(action: DraftAction) {
    setBusyAction(action);
    try {
      await onMark(draft.id, action);
    } finally {
      setBusyAction(null);
    }
  }

  async function handleConfirmDelete() {
    setBusyAction('delete');
    try {
      await onDelete(draft.id);
      setConfirmDeleteOpen(false);
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <div className="draft-editor" aria-label="Comment draft editor">
      <div className="row-between">
        <div className="row-wrap" style={{ gap: 8 }}>
          <span className="badge badge-primary" style={{ textTransform: 'capitalize' }}>
            Status: {draft.status}
          </span>
          {draft.style_variant && (
            <span className="badge badge-neutral">{draft.style_variant}</span>
          )}
          <RelevanceBadge score={draft.relevance_score} />
        </div>
        {draft.quality_score !== null && (
          <span className="meta-text">Quality: {Math.round(draft.quality_score * 100)}%</span>
        )}
      </div>

      <div className="field">
        <label htmlFor={`draft-textarea-${draft.id}`} className="field-label">
          Comment Draft (Human review required before posting)
        </label>
        <textarea
          id={`draft-textarea-${draft.id}`}
          className="textarea"
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={2000}
          rows={4}
        />
        <div className="row-between">
          <span className="field-hint">{text.length} / 2000 characters</span>
          {isDirty && (
            <button
              type="button"
              className="btn btn-soft btn-sm"
              onClick={handleSave}
              disabled={busyAction !== null || !text.trim()}
            >
              <Save size={14} aria-hidden="true" />
              {busyAction === 'save' ? 'Saving...' : 'Save Edits'}
            </button>
          )}
        </div>
      </div>

      <div className="cards-grid-2" style={{ gap: 10 }}>
        <div className="field">
          <label htmlFor={`draft-tone-${draft.id}`} className="field-label">
            Tone
          </label>
          <select
            id={`draft-tone-${draft.id}`}
            className="select"
            value={tone}
            onChange={(e) => setTone(e.target.value)}
          >
            {TONE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label htmlFor={`draft-length-${draft.id}`} className="field-label">
            Length
          </label>
          <select
            id={`draft-length-${draft.id}`}
            className="select"
            value={length}
            onChange={(e) => setLength(e.target.value as 'short' | 'medium' | 'detailed')}
          >
            {LENGTH_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="row-wrap" style={{ gap: 8 }}>
        <label htmlFor={`draft-instruction-${draft.id}`} className="sr-only">
          Optional regeneration instruction
        </label>
        <input
          id={`draft-instruction-${draft.id}`}
          type="text"
          className="input"
          style={{ flex: 1, minWidth: 180 }}
          placeholder="Optional instruction (e.g., ask about metrics)"
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          maxLength={300}
        />
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={handleRegenerate}
          disabled={busyAction !== null}
        >
          <RefreshCw size={14} aria-hidden="true" />
          {busyAction === 'regenerate' ? 'Regenerating...' : 'Regenerate'}
        </button>
      </div>

      <div className="row-between" style={{ paddingTop: 6, borderTop: '1px solid var(--color-border)' }}>
        <div className="row-wrap" style={{ gap: 8 }}>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={handleCopy}
            disabled={busyAction !== null || !text.trim()}
          >
            {copiedRecently ? <Check size={14} aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}
            {copiedRecently ? 'Copied!' : 'Copy Comment'}
          </button>

          {draft.post?.canonical_url && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={handleOpenPost}
              disabled={busyAction !== null}
            >
              <ExternalLink size={14} aria-hidden="true" />
              Open Post
            </button>
          )}
        </div>

        <div className="row-wrap" style={{ gap: 6 }}>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => handleMarkAction('skipped')}
            disabled={busyAction !== null}
          >
            <SkipForward size={14} aria-hidden="true" />
            Skip
          </button>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => handleMarkAction('archived')}
            disabled={busyAction !== null}
          >
            <Archive size={14} aria-hidden="true" />
            Archive
          </button>
          <button
            type="button"
            className="btn btn-danger-soft btn-sm"
            onClick={() => setConfirmDeleteOpen(true)}
            disabled={busyAction !== null}
          >
            <Trash2 size={14} aria-hidden="true" />
            Delete
          </button>
        </div>
      </div>

      <ConfirmDialog
        open={confirmDeleteOpen}
        title="Delete comment draft?"
        description="This permanently removes the draft from your review queue. The original post will remain in your inbox."
        confirmLabel="Delete Draft"
        busy={busyAction === 'delete'}
        onConfirm={handleConfirmDelete}
        onCancel={() => setConfirmDeleteOpen(false)}
      />
    </div>
  );
}
