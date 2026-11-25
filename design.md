# UI/UX Design Specification
## SocialEngage AI

## 1. Design direction
Create a premium, calm, light-mode productivity dashboard. The visual language should feel like a polished modern SaaS product: subtle lavender accents, soft neutral surfaces, restrained glass effects, generous spacing, crisp typography, and clear hierarchy.

Avoid overly dark interfaces, excessive gradients, noisy backgrounds, or flashy AI gimmicks.

## 2. Brand
- Working name: SocialEngage AI
- Voice: helpful, thoughtful, trustworthy, concise
- Tagline: “Meaningful engagement, made easier.”
- Visual motif: small sparkle or conversation mark; do not imitate social platform logos.

## 3. Design tokens
```css
:root {
  --color-bg: #F8F7FC;
  --color-surface: #FFFFFF;
  --color-surface-soft: #F1EFF8;
  --color-text: #242235;
  --color-text-muted: #77748B;
  --color-border: #E7E3F0;
  --color-primary: #7966D8;
  --color-primary-hover: #6754C5;
  --color-primary-soft: #EAE5FF;
  --color-success: #24856B;
  --color-warning: #B77928;
  --color-danger: #C45161;
  --shadow-card: 0 8px 28px rgba(45, 35, 90, 0.06);
  --radius-sm: 10px;
  --radius-md: 16px;
  --radius-lg: 22px;
  --radius-pill: 999px;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
}
```

## 4. Typography
- Use Inter or a system sans-serif.
- Page title: 26–30px, semibold.
- Section title: 17–20px, semibold.
- Body: 14–16px.
- Metadata: 12–13px.
- Use comfortable line-height; avoid dense text blocks.

## 5. Layout
- Desktop: fixed left navigation (220–250px), main content, optional right-side detail panel.
- Main content max width: 1200px.
- Mobile: compact top bar and stacked content; navigation becomes a drawer.
- Use 8px spacing rhythm.
- Cards should have subtle borders and soft shadows, not heavy outlines.

## 6. Navigation
- Overview
- Watchlist
- Post Inbox
- Drafts
- Activity
- Settings

Sidebar footer: connection status and account menu.

## 7. Screens

### Overview
Show:
- Tracked profiles
- New posts detected
- Drafts awaiting review
- Drafts approved/copied
- Recent activity
- Monitoring health

### Watchlist
- Search and filter targets by platform/status.
- Add target dialog with URL, platform, display name, and source method.
- Each row includes avatar placeholder, name, platform, status, last checked, pause/edit/remove actions.
- Explain source access availability clearly.

### Post Inbox
- Post cards with author, platform, preview, post date, detected date, relevance indicator.
- Filters: platform, target, relevance, status.
- Empty state: “No new posts yet. Your watchlist is being checked.”

### Draft Review
- Original post summary and external link.
- Draft editor.
- Tone/length selectors.
- Regenerate option.
- Copy comment and open post actions.
- Mark reviewed/skip.
- Never display an “Auto-post” action.

### Activity
- Timeline with filters.
- Distinguish success, skipped, and failed source checks.
- Provide understandable error details.

### Settings
- Comment preferences.
- Telegram connection.
- AI provider configuration (server-side secret setup guidance).
- Monitoring cadence and source limits.
- Privacy/data deletion.

## 8. Components
- `AppShell`
- `Sidebar`
- `Topbar`
- `MetricCard`
- `ProfileRow`
- `PostCard`
- `DraftEditor`
- `RelevanceBadge`
- `PlatformBadge`
- `SourceStatus`
- `EmptyState`
- `ErrorBanner`
- `ConfirmDialog`
- `Toast`

## 9. Interaction rules
- Every button must have a working action.
- Use confirmation for destructive actions.
- Show optimistic updates only when rollback is possible.
- Display loading skeletons for async data.
- Copy action should show confirmation.
- Source errors must not be disguised as “no new posts.”
- Provide keyboard focus and accessible labels.

## 10. Responsive behavior
- 1280px+: full sidebar and multi-column overview.
- 768–1279px: compact sidebar, two-column cards.
- Below 768px: drawer navigation, single-column cards, full-width editor.

## 11. Accessibility
- WCAG AA contrast target.
- Keyboard navigation.
- Visible focus states.
- Semantic headings and buttons.
- Do not rely on color alone for status.
