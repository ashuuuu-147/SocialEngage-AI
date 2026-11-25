import React, { useCallback, useEffect, useState } from 'react';
import {
  Bell,
  Download,
  ExternalLink,
  KeyRound,
  Plus,
  Send,
  Trash2,
  Unlink,
} from 'lucide-react';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { ErrorBanner } from '../components/ErrorBanner';
import { useToast } from '../components/Toast';
import { useAuth } from '../lib/auth';
import { extractErrorInfo } from '../lib/format';
import type {
  NotificationSettings,
  Preferences,
  StyleSample,
  TelegramConnectResponse,
  UserProfile,
} from '../lib/types';

function splitCsv(raw: string): string[] {
  return raw
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

export function SettingsPage() {
  const { api, signOut } = useAuth();
  const { showToast } = useToast();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ message: string; code?: string; requestId?: string } | null>(
    null
  );

  // Profile
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [displayName, setDisplayName] = useState('');
  const [timezone, setTimezone] = useState('Asia/Kolkata');

  // Preferences
  const [prefs, setPrefs] = useState<Preferences | null>(null);
  const [tone, setTone] = useState('professional-conversational');
  const [length, setLength] = useState<'short' | 'medium' | 'detailed'>('short');
  const [language, setLanguage] = useState('English');
  const [emojiLevel, setEmojiLevel] = useState<'none' | 'low' | 'medium'>('low');
  const [relevanceThreshold, setRelevanceThreshold] = useState(0.7);
  const [preferredTopicsText, setPreferredTopicsText] = useState('');
  const [excludedTopicsText, setExcludedTopicsText] = useState('');
  const [avoidPhrasesText, setAvoidPhrasesText] = useState('');
  const [monitoringInterval, setMonitoringInterval] = useState(30);
  const [retentionDays, setRetentionDays] = useState(90);

  // Style Samples
  const [samples, setSamples] = useState<StyleSample[]>([]);
  const [newSample, setNewSample] = useState('');

  // Notifications & Telegram
  const [notif, setNotif] = useState<NotificationSettings | null>(null);
  const [connectInfo, setConnectInfo] = useState<TelegramConnectResponse | null>(null);
  const [verifyCode, setVerifyCode] = useState('');
  const [verifyChatId, setVerifyChatId] = useState('');
  const [dailyDigestEnabled, setDailyDigestEnabled] = useState(true);
  const [digestTime, setDigestTime] = useState('09:00');

  // Dialogs & saving states
  const [savingSection, setSavingSection] = useState<string | null>(null);
  const [confirmDisconnectOpen, setConfirmDisconnectOpen] = useState(false);
  const [confirmDeleteAccountOpen, setConfirmDeleteAccountOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [p, pr, ss, ns] = await Promise.all([
        api.getProfile(),
        api.getPreferences(),
        api.listStyleSamples(),
        api.getNotificationSettings(),
      ]);
      setProfile(p);
      setDisplayName(p.display_name || '');
      setTimezone(p.timezone || 'Asia/Kolkata');

      setPrefs(pr);
      setTone(pr.tone);
      setLength((pr.length as 'short' | 'medium' | 'detailed') || 'short');
      setLanguage(pr.language);
      setEmojiLevel((pr.emoji_level as 'none' | 'low' | 'medium') || 'low');
      setRelevanceThreshold(pr.relevance_threshold);
      setPreferredTopicsText(pr.preferred_topics.join(', '));
      setExcludedTopicsText(pr.excluded_topics.join(', '));
      setAvoidPhrasesText(pr.avoid_phrases.join(', '));
      setMonitoringInterval(pr.monitoring_interval_minutes);
      setRetentionDays(pr.data_retention_days);

      setSamples(ss);
      setNotif(ns);
      setDailyDigestEnabled(ns.daily_digest_enabled);
      setDigestTime((ns.digest_time || '09:00:00').slice(0, 5));
    } catch (err) {
      setError(extractErrorInfo(err));
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault();
    setSavingSection('profile');
    try {
      const updated = await api.updateProfile({
        display_name: displayName.trim(),
        timezone: timezone.trim(),
      });
      setProfile(updated);
      showToast('Profile settings saved.', 'success');
    } catch (err) {
      showToast(extractErrorInfo(err).message, 'error');
    } finally {
      setSavingSection(null);
    }
  }

  async function handleSavePreferences(e: React.FormEvent) {
    e.preventDefault();
    setSavingSection('preferences');
    try {
      const updated = await api.updatePreferences({
        tone,
        length,
        language: language.trim() || 'English',
        emoji_level: emojiLevel,
        relevance_threshold: relevanceThreshold,
        preferred_topics: splitCsv(preferredTopicsText),
        excluded_topics: splitCsv(excludedTopicsText),
        avoid_phrases: splitCsv(avoidPhrasesText),
        monitoring_interval_minutes: monitoringInterval,
        data_retention_days: retentionDays,
      });
      setPrefs(updated);
      showToast('Comment & monitoring preferences saved.', 'success');
    } catch (err) {
      showToast(extractErrorInfo(err).message, 'error');
    } finally {
      setSavingSection(null);
    }
  }

  async function handleAddSample(e: React.FormEvent) {
    e.preventDefault();
    if (newSample.trim().length < 5) {
      showToast('Style sample must be at least 5 characters.', 'warning');
      return;
    }
    setSavingSection('sample');
    try {
      const created = await api.createStyleSample(newSample.trim());
      setSamples((prev) => [created, ...prev]);
      setNewSample('');
      showToast('Style sample added.', 'success');
    } catch (err) {
      showToast(extractErrorInfo(err).message, 'error');
    } finally {
      setSavingSection(null);
    }
  }

  async function handleDeleteSample(sampleId: string) {
    setSavingSection(`sample-${sampleId}`);
    try {
      await api.deleteStyleSample(sampleId);
      setSamples((prev) => prev.filter((s) => s.id !== sampleId));
      showToast('Style sample removed.', 'info');
    } catch (err) {
      showToast(extractErrorInfo(err).message, 'error');
    } finally {
      setSavingSection(null);
    }
  }

  async function handleConnectTelegram() {
    setSavingSection('telegram-connect');
    try {
      const res = await api.connectTelegram();
      setConnectInfo(res);
      setVerifyCode(res.verification_code);
      showToast('Verification code generated.', 'info');
    } catch (err) {
      showToast(extractErrorInfo(err).message, 'error');
    } finally {
      setSavingSection(null);
    }
  }

  async function handleVerifyTelegram(e: React.FormEvent) {
    e.preventDefault();
    setSavingSection('telegram-verify');
    try {
      const updated = await api.verifyTelegram({
        verification_code: verifyCode.trim(),
        chat_id: verifyChatId.trim(),
      });
      setNotif(updated);
      setConnectInfo(null);
      setVerifyChatId('');
      showToast('Telegram chat verified and connected!', 'success');
    } catch (err) {
      showToast(extractErrorInfo(err).message, 'error');
    } finally {
      setSavingSection(null);
    }
  }

  async function handleTestTelegram() {
    setSavingSection('telegram-test');
    try {
      const res = await api.sendTestNotification();
      showToast(
        res.delivered ? `Test sent (${res.mode}): ${res.detail}` : `Test failed: ${res.detail}`,
        res.delivered ? 'success' : 'warning'
      );
    } catch (err) {
      showToast(extractErrorInfo(err).message, 'error');
    } finally {
      setSavingSection(null);
    }
  }

  async function handleDisconnectTelegram() {
    setSavingSection('telegram-disconnect');
    try {
      const updated = await api.disconnectTelegram();
      setNotif(updated);
      setConfirmDisconnectOpen(false);
      showToast('Telegram disconnected.', 'info');
    } catch (err) {
      showToast(extractErrorInfo(err).message, 'error');
    } finally {
      setSavingSection(null);
    }
  }

  async function handleSaveNotifications(e: React.FormEvent) {
    e.preventDefault();
    setSavingSection('notifications');
    try {
      const normalizedTime = digestTime.length === 5 ? `${digestTime}:00` : digestTime;
      const updated = await api.updateNotificationSettings({
        daily_digest_enabled: dailyDigestEnabled,
        digest_time: normalizedTime,
        telegram_enabled: notif?.telegram_enabled,
      });
      setNotif(updated);
      showToast('Notification settings updated.', 'success');
    } catch (err) {
      showToast(extractErrorInfo(err).message, 'error');
    } finally {
      setSavingSection(null);
    }
  }

  async function handleExportData() {
    setSavingSection('export');
    try {
      const data = await api.exportAccountData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `socialengage-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      showToast('Workspace data exported as JSON.', 'success');
    } catch (err) {
      showToast(extractErrorInfo(err).message, 'error');
    } finally {
      setSavingSection(null);
    }
  }

  async function handleDeleteAccount() {
    setSavingSection('delete-account');
    try {
      await api.deleteAccount();
      setConfirmDeleteAccountOpen(false);
      showToast('Account and all associated data deleted.', 'info');
      signOut();
    } catch (err) {
      showToast(extractErrorInfo(err).message, 'error');
    } finally {
      setSavingSection(null);
    }
  }

  if (loading) {
    return (
      <div className="stack-md">
        <div className="skeleton" style={{ height: 180 }} />
        <div className="skeleton" style={{ height: 260 }} />
      </div>
    );
  }

  return (
    <div className="stack-lg">
      {error && (
        <ErrorBanner
          title="Unable to load settings"
          message={error.message}
          code={error.code}
          requestId={error.requestId}
          onRetry={load}
        />
      )}

      {/* Workspace Profile */}
      {profile && (
        <form className="card stack-md" onSubmit={handleSaveProfile}>
          <div className="section-header" style={{ marginBottom: 0 }}>
            <h2 className="section-title">Workspace Profile</h2>
            <button
              type="submit"
              className="btn btn-primary btn-sm"
              disabled={savingSection === 'profile'}
            >
              {savingSection === 'profile' ? 'Saving...' : 'Save Profile'}
            </button>
          </div>
          <div className="cards-grid-2">
            <div className="field">
              <label htmlFor="profile-display-name" className="field-label">
                Display Name
              </label>
              <input
                id="profile-display-name"
                type="text"
                className="input"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                maxLength={120}
              />
            </div>
            <div className="field">
              <label htmlFor="profile-timezone" className="field-label">
                Timezone
              </label>
              <input
                id="profile-timezone"
                type="text"
                className="input"
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                maxLength={64}
              />
            </div>
          </div>
        </form>
      )}

      {/* Comment & Monitoring Preferences */}
      {prefs && (
        <form className="card stack-md" onSubmit={handleSavePreferences}>
          <div className="section-header" style={{ marginBottom: 0 }}>
            <h2 className="section-title">Comment Preferences & Monitoring Cadence</h2>
            <button
              type="submit"
              className="btn btn-primary btn-sm"
              disabled={savingSection === 'preferences'}
            >
              {savingSection === 'preferences' ? 'Saving...' : 'Save Preferences'}
            </button>
          </div>

          <div className="cards-grid-2">
            <div className="field">
              <label htmlFor="pref-tone" className="field-label">
                Default Tone
              </label>
              <select
                id="pref-tone"
                className="select"
                value={tone}
                onChange={(e) => setTone(e.target.value)}
              >
                <option value="professional-conversational">Professional & Conversational</option>
                <option value="warm-encouraging">Warm & Encouraging</option>
                <option value="curious-analytical">Curious & Analytical</option>
                <option value="concise-executive">Concise & Executive</option>
              </select>
            </div>

            <div className="field">
              <label htmlFor="pref-length" className="field-label">
                Default Length
              </label>
              <select
                id="pref-length"
                className="select"
                value={length}
                onChange={(e) => setLength(e.target.value as 'short' | 'medium' | 'detailed')}
              >
                <option value="short">Short (1–2 sentences)</option>
                <option value="medium">Medium (2–3 sentences)</option>
                <option value="detailed">Detailed (3–4 sentences)</option>
              </select>
            </div>

            <div className="field">
              <label htmlFor="pref-language" className="field-label">
                Language
              </label>
              <input
                id="pref-language"
                type="text"
                className="input"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
              />
            </div>

            <div className="field">
              <label htmlFor="pref-emoji" className="field-label">
                Emoji Level
              </label>
              <select
                id="pref-emoji"
                className="select"
                value={emojiLevel}
                onChange={(e) => setEmojiLevel(e.target.value as 'none' | 'low' | 'medium')}
              >
                <option value="none">None</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
              </select>
            </div>
          </div>

          <div className="field">
            <label htmlFor="pref-relevance" className="field-label">
              Minimum Relevance Threshold ({Math.round(relevanceThreshold * 100)}%)
            </label>
            <input
              id="pref-relevance"
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={relevanceThreshold}
              onChange={(e) => setRelevanceThreshold(Number(e.target.value))}
            />
            <span className="field-hint">
              Posts below this relevance score are skipped instead of generating generic drafts.
            </span>
          </div>

          <div className="cards-grid-2">
            <div className="field">
              <label htmlFor="pref-preferred-topics" className="field-label">
                Preferred Topics (comma-separated)
              </label>
              <input
                id="pref-preferred-topics"
                type="text"
                className="input"
                value={preferredTopicsText}
                onChange={(e) => setPreferredTopicsText(e.target.value)}
                placeholder="product engineering, AI safety, design systems"
              />
            </div>

            <div className="field">
              <label htmlFor="pref-excluded-topics" className="field-label">
                Excluded Topics (comma-separated)
              </label>
              <input
                id="pref-excluded-topics"
                type="text"
                className="input"
                value={excludedTopicsText}
                onChange={(e) => setExcludedTopicsText(e.target.value)}
                placeholder="giveaway, crypto"
              />
            </div>
          </div>

          <div className="field">
            <label htmlFor="pref-avoid-phrases" className="field-label">
              Phrases to Avoid (comma-separated)
            </label>
            <input
              id="pref-avoid-phrases"
              type="text"
              className="input"
              value={avoidPhrasesText}
              onChange={(e) => setAvoidPhrasesText(e.target.value)}
              placeholder="great post!, love this!, game changer"
            />
          </div>

          <div className="cards-grid-2">
            <div className="field">
              <label htmlFor="pref-interval" className="field-label">
                Monitoring Interval (minutes, 5–1440)
              </label>
              <input
                id="pref-interval"
                type="number"
                min={5}
                max={1440}
                className="input"
                value={monitoringInterval}
                onChange={(e) => setMonitoringInterval(Number(e.target.value))}
              />
            </div>

            <div className="field">
              <label htmlFor="pref-retention" className="field-label">
                Data Retention (days, 7–365)
              </label>
              <input
                id="pref-retention"
                type="number"
                min={7}
                max={365}
                className="input"
                value={retentionDays}
                onChange={(e) => setRetentionDays(Number(e.target.value))}
              />
            </div>
          </div>
        </form>
      )}

      {/* Personal Style Samples */}
      <section className="card stack-md" aria-label="Personal style samples">
        <div>
          <h2 className="section-title">Personal Style Samples</h2>
          <p className="meta-text">
            Add 2–4 examples of comments you have written so generated drafts reflect your voice.
          </p>
        </div>

        <form className="row-wrap" onSubmit={handleAddSample} style={{ alignItems: 'flex-start' }}>
          <label htmlFor="new-style-sample" className="sr-only">
            New style sample comment
          </label>
          <textarea
            id="new-style-sample"
            className="textarea"
            style={{ flex: 1, minWidth: 240, minHeight: 68 }}
            placeholder="Paste an authentic comment you've written..."
            value={newSample}
            onChange={(e) => setNewSample(e.target.value)}
            maxLength={1000}
          />
          <button
            type="submit"
            className="btn btn-secondary"
            disabled={savingSection === 'sample' || newSample.trim().length < 5}
          >
            <Plus size={15} aria-hidden="true" />
            Add Sample
          </button>
        </form>

        {samples.length === 0 ? (
          <p className="meta-text">No style samples added yet.</p>
        ) : (
          <div className="stack-sm">
            {samples.map((s) => (
              <div key={s.id} className="card-soft row-between">
                <p style={{ fontSize: 14, flex: 1 }}>{s.sample_text}</p>
                <button
                  type="button"
                  className="btn btn-danger-soft btn-sm"
                  onClick={() => handleDeleteSample(s.id)}
                  disabled={savingSection === `sample-${s.id}`}
                  aria-label="Delete style sample"
                >
                  <Trash2 size={14} aria-hidden="true" />
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Telegram Connection */}
      <section className="card stack-md" aria-label="Telegram notifications">
        <div className="row-between">
          <div>
            <h2 className="section-title">Telegram Notifications</h2>
            <p className="meta-text">
              Receive real-time draft alerts and daily digests on Telegram.
            </p>
          </div>
          <span className={`badge ${notif?.telegram_connected ? 'badge-success' : 'badge-neutral'}`}>
            <Bell size={12} aria-hidden="true" />
            {notif?.telegram_connected
              ? `Connected (${notif.telegram_chat_id_masked || 'Verified'})`
              : 'Not connected'}
          </span>
        </div>

        <div className="row-wrap">
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={handleConnectTelegram}
            disabled={savingSection === 'telegram-connect'}
          >
            Generate Verification Code
          </button>

          {notif?.telegram_connected && (
            <>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handleTestTelegram}
                disabled={savingSection === 'telegram-test'}
              >
                <Send size={14} aria-hidden="true" />
                Send Test Message
              </button>
              <button
                type="button"
                className="btn btn-danger-soft btn-sm"
                onClick={() => setConfirmDisconnectOpen(true)}
                disabled={savingSection === 'telegram-disconnect'}
              >
                <Unlink size={14} aria-hidden="true" />
                Disconnect Telegram
              </button>
            </>
          )}
        </div>

        {connectInfo && (
          <div className="card-soft stack-sm">
            <div className="row-between">
              <strong style={{ fontSize: 14 }}>
                Verification Code: <code>{connectInfo.verification_code}</code>
              </strong>
              {connectInfo.deep_link_url && (
                <a
                  href={connectInfo.deep_link_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-soft btn-sm"
                >
                  <ExternalLink size={14} aria-hidden="true" />
                  Open Telegram Bot
                </a>
              )}
            </div>
            <p className="meta-text">{connectInfo.instructions}</p>

            <form className="row-wrap" onSubmit={handleVerifyTelegram}>
              <input
                type="text"
                className="input"
                style={{ width: 190 }}
                placeholder="Verification code"
                aria-label="Telegram verification code"
                value={verifyCode}
                onChange={(e) => setVerifyCode(e.target.value)}
                required
              />
              <input
                type="text"
                className="input"
                style={{ width: 190 }}
                placeholder="Your Telegram Chat ID"
                aria-label="Telegram chat ID"
                value={verifyChatId}
                onChange={(e) => setVerifyChatId(e.target.value)}
                required
              />
              <button
                type="submit"
                className="btn btn-primary btn-sm"
                disabled={savingSection === 'telegram-verify'}
              >
                Verify Connection
              </button>
            </form>
          </div>
        )}

        <form className="row-between" onSubmit={handleSaveNotifications}>
          <div className="row-wrap">
            <label className="row-wrap" style={{ gap: 8, cursor: 'pointer', fontSize: 14 }}>
              <input
                type="checkbox"
                checked={dailyDigestEnabled}
                onChange={(e) => setDailyDigestEnabled(e.target.checked)}
              />
              <span>Enable daily digest</span>
            </label>

            <label htmlFor="digest-time" className="field-label">
              Digest time
            </label>
            <input
              id="digest-time"
              type="time"
              className="input"
              style={{ width: 130 }}
              value={digestTime}
              onChange={(e) => setDigestTime(e.target.value)}
            />
          </div>

          <button
            type="submit"
            className="btn btn-secondary btn-sm"
            disabled={savingSection === 'notifications'}
          >
            Save Digest Settings
          </button>
        </form>
      </section>

      {/* AI Provider Guidance */}
      <section className="card stack-sm" aria-label="AI provider configuration">
        <div className="row-wrap" style={{ gap: 8 }}>
          <KeyRound size={18} aria-hidden="true" />
          <h2 className="section-title">AI Provider Configuration</h2>
        </div>
        <p className="meta-text">
          For security, OpenAI, Anthropic, and Gemini API keys are configured exclusively on the
          backend server via environment secrets (<code>AI_PROVIDER</code>,{' '}
          <code>OPENAI_API_KEY</code>, <code>ANTHROPIC_API_KEY</code>, or{' '}
          <code>GEMINI_API_KEY</code>) and are never stored or exposed in your browser.
        </p>
      </section>

      {/* Privacy & Data */}
      <section className="card stack-md" aria-label="Privacy and data controls">
        <h2 className="section-title">Privacy & Data</h2>
        <div className="row-between">
          <div className="row-wrap">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleExportData}
              disabled={savingSection === 'export'}
            >
              <Download size={15} aria-hidden="true" />
              Export My Data (JSON)
            </button>
          </div>

          <button
            type="button"
            className="btn btn-danger-soft"
            onClick={() => setConfirmDeleteAccountOpen(true)}
            disabled={savingSection === 'delete-account'}
          >
            <Trash2 size={15} aria-hidden="true" />
            Delete Account
          </button>
        </div>
      </section>

      <ConfirmDialog
        open={confirmDisconnectOpen}
        title="Disconnect Telegram?"
        description="You will stop receiving Telegram draft alerts and digests until you verify a chat again."
        confirmLabel="Disconnect Telegram"
        busy={savingSection === 'telegram-disconnect'}
        onConfirm={handleDisconnectTelegram}
        onCancel={() => setConfirmDisconnectOpen(false)}
      />

      <ConfirmDialog
        open={confirmDeleteAccountOpen}
        title="Delete your account and all data?"
        description="This permanently deletes your profile, watchlist targets, drafts, style samples, and activity logs. This action cannot be undone."
        confirmLabel="Delete Account"
        busy={savingSection === 'delete-account'}
        onConfirm={handleDeleteAccount}
        onCancel={() => setConfirmDeleteAccountOpen(false)}
      />
    </div>
  );
}
