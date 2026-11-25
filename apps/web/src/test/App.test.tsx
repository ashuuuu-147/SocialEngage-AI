import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { App } from '../App';
import { AuthSession } from '../lib/auth';

const DEMO_SESSION: AuthSession = {
  mode: 'demo',
  label: 'Offline Demo Preview',
};

describe('SocialEngage AI Frontend', () => {
  it('renders Auth sign-in view and allows entering Demo Preview or Dev Workspace', async () => {
    render(<App initialSession={null} />);

    expect(screen.getByRole('heading', { name: /SocialEngage AI/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Continue with Demo Workspace/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Preview UI Offline/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Preview UI Offline/i }));

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Overview' })).toBeInTheDocument();
    });
    expect(screen.getByText('Tracked Profiles')).toBeInTheDocument();
  });

  it('navigates across all 6 workspace sections and never renders an Auto-post button', async () => {
    render(<App initialSession={DEMO_SESSION} />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Overview' })).toBeInTheDocument();
    });

    const nav = screen.getByRole('navigation', { name: 'Workspace sections' });

    fireEvent.click(within(nav).getByRole('button', { name: /Watchlist/i }));
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Watchlist' })).toBeInTheDocument();
    });
    expect(screen.getByText(/Compliant Source Availability/i)).toBeInTheDocument();

    fireEvent.click(within(nav).getByRole('button', { name: /Post Inbox/i }));
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Post Inbox' })).toBeInTheDocument();
    });

    fireEvent.click(within(nav).getByRole('button', { name: /Drafts/i }));
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Draft Review' })).toBeInTheDocument();
    });

    // Critical safety requirement: NEVER display an Auto-post button
    expect(screen.queryByText(/auto-post/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /auto.?post/i })).not.toBeInTheDocument();

    fireEvent.click(within(nav).getByRole('button', { name: /Activity/i }));
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Activity' })).toBeInTheDocument();
    });
    expect(screen.getByText('Monitoring Jobs')).toBeInTheDocument();

    fireEvent.click(within(nav).getByRole('button', { name: /Settings/i }));
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Settings' })).toBeInTheDocument();
    });
    expect(screen.getByText('Telegram Notifications')).toBeInTheDocument();
  });

  it('opens Manual Post modal from Topbar and submits a post with generated drafts', async () => {
    render(<App initialSession={DEMO_SESSION} />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Overview' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /^Submit Post URL$/i }));

    const dialog = screen.getByRole('dialog');
    expect(
      within(dialog).getByRole('heading', { name: /Submit Post URL & Text/i })
    ).toBeInTheDocument();

    fireEvent.change(within(dialog).getByLabelText(/Post URL/i), {
      target: { value: 'https://www.linkedin.com/feed/update/urn:li:activity:999999' },
    });
    fireEvent.change(within(dialog).getByLabelText(/Author Name/i), {
      target: { value: 'Alex Rivera' },
    });
    fireEvent.change(within(dialog).getByLabelText(/Post Text \/ Caption Preview/i), {
      target: { value: 'Testing automated cloud cron workflows for engineering teams.' },
    });

    fireEvent.click(within(dialog).getByRole('button', { name: /^Submit Post$/i }));

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
    expect(screen.getByText(/ready for review/i)).toBeInTheDocument();
  });

  it('supports DraftEditor copy, open post, skip, and ConfirmDialog delete', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    });
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);

    render(<App initialSession={DEMO_SESSION} />);

    const nav = screen.getByRole('navigation', { name: 'Workspace sections' });
    fireEvent.click(within(nav).getByRole('button', { name: /Drafts/i }));

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Draft Review' })).toBeInTheDocument();
    });

    const editors = await screen.findAllByLabelText('Comment draft editor');
    const firstEditor = editors[0];

    // Copy comment triggers clipboard + confirmation toast
    fireEvent.click(within(firstEditor).getByRole('button', { name: /Copy Comment/i }));
    await waitFor(() => {
      expect(writeText).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByText(/Comment copied to clipboard!/i)).toBeInTheDocument();

    // Open post opens canonical URL in a new tab
    fireEvent.click(within(firstEditor).getByRole('button', { name: /Open Post/i }));
    await waitFor(() => {
      expect(openSpy).toHaveBeenCalledWith(
        expect.stringContaining('https://'),
        '_blank',
        'noopener,noreferrer'
      );
    });

    // Skip marks the draft skipped
    fireEvent.click(within(firstEditor).getByRole('button', { name: /^Skip$/i }));
    await waitFor(() => {
      expect(within(firstEditor).getByText(/Status: skipped/i)).toBeInTheDocument();
    });

    // Delete opens ConfirmDialog and deletes only upon confirmation
    fireEvent.click(within(firstEditor).getByRole('button', { name: /^Delete$/i }));
    const confirmDialog = screen.getByRole('alertdialog');
    expect(
      within(confirmDialog).getByRole('heading', { name: /Delete comment draft\?/i })
    ).toBeInTheDocument();

    fireEvent.click(within(confirmDialog).getByRole('button', { name: /Delete Draft/i }));
    await waitFor(() => {
      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    });
  });

  it('sends X-Dev-User-Id header to real API and displays backend error envelope in ErrorBanner', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/overview')) {
        return new Response(
          JSON.stringify({
            error: {
              code: 'DATABASE_UNAVAILABLE',
              message: 'Backend database connection failed.',
              request_id: 'req-12345',
            },
          }),
          { status: 503, headers: { 'Content-Type': 'application/json' } }
        );
      }
      return new Response(JSON.stringify([]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    });

    render(
      <App
        initialSession={{
          mode: 'dev',
          devUserId: '00000000-0000-0000-0000-000000000001',
          label: 'Dev Workspace',
        }}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Backend database connection failed.')).toBeInTheDocument();
    });
    expect(screen.getByText(/Code: DATABASE_UNAVAILABLE/)).toBeInTheDocument();
    expect(screen.getByText(/Request ID: req-12345/)).toBeInTheDocument();

    const firstCallHeaders = fetchMock.mock.calls[0]?.[1]?.headers as Headers;
    expect(firstCallHeaders.get('X-Dev-User-Id')).toBe(
      '00000000-0000-0000-0000-000000000001'
    );
  });
});
