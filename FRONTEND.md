# LIMEN — Frontend Architecture & Clinical Editorial Glass Design System

> **Document role:** canonical frontend architecture, interaction design, visual language, component system, responsive behavior, accessibility rules, and implementation constraints.  
> **Status:** foundation specification.  
> **Applies to:** `apps/web/**`

---

<div align="center">

# ◈ LIMEN / FRONTEND

### Clinical Editorial Glass

**Depth over decoration · Readability over effect · Meaningful color over random color**

</div>

---

# 1. Product Form Factor

## Decision

LIMEN will be built as a:

> **responsive, desktop-first web application with an app-like experience.**

Optional after the core challenge flow is stable:

- PWA manifest;
- installable mode;
- offline shell for non-clinical static assets.

Not in the critical path:

- native iOS;
- native Android;
- Electron;
- Tauri;
- duplicated desktop/mobile applications.

## Why

The competition requires browser/API interaction and a browser voice experience.

A single web application provides:

- fastest reproducibility;
- easiest evaluator access;
- direct microphone support;
- one UI codebase;
- no installer;
- easy demo capture;
- simple integration with FastAPI/WebSocket.

---

# 2. Required & Recommended Surfaces

## P0 — Required

### `/call`

Voice interaction.

### `/knowledge`

Knowledge administration console.

## P1 — Strong differentiators

### `/trace/:callId`

TRAZA decision audit.

### `/sessions`

Call/session history.

### `/settings`

Client preferences in one glass panel: theme, language, account, microphone,
session actions (delete account / sign out). Runtime diagnostics stay collapsed.

## P2 — Optional

### `/`

Commercial entry/landing: what the product does, how a session moves, how client
data is separated, and what is honestly not wired yet.

### `/login`, `/register`

Account entry. Public routes; every surface above sits behind the session guard.

---

# 3. Authentication — approved, minimal, product-driven

The challenge itself does not require enterprise authentication or role
management, and none is implemented: no OAuth/SSO, no MFA, no hospital RBAC.

What **is** implemented, approved by product and recorded in
[ADR-0004](docs/adr/ADR-0004-client-auth.md): a client account plus a session
cookie, because the knowledge base holds each clinic's own clinical corpus. Without
accounts, one client's uploaded protocols would be retrievable inside another
client's call, and a deletion could erase somebody else's corpus.

Scope of the exception:

- `/`, `/login`, `/register` public; `/call`, `/knowledge`, `/trace`, `/sessions`,
  `/settings` behind `RequireAuth`.
- `GET /health` stays public so a cold deployment can be probed.
- Session in an httpOnly cookie, never in `localStorage` — retrieved documents
  and patient speech are untrusted input.
- A demo account is seeded by `make bootstrap` so cold start still reaches a call
  without manual setup.

Anything beyond that — identity providers, password reset mail, role hierarchies —
remains out of scope.

---

# 4. Visual Direction

## Name

# **Clinical Editorial Glass**

A controlled combination of:

- deep editorial dark surfaces;
- refined glass layers;
- cinematic but quiet gradients;
- very high information clarity;
- sparse premium composition;
- meaningful clinical color;
- modern sans-serif UI typography;
- restrained serif accents on the landing only — never inside the workspace.

The interface must feel like:

> **a serious clinical-intelligence workspace, not a generic AI dashboard.**

---

# 5. What We Take from the Visual References

## Atmospheric glass UI

Keep:

- depth;
- soft environmental gradients;
- translucent inspectors;
- split workspaces.

Avoid:

- background imagery behind dense data;
- excessive blur;
- concept-art over functionality.

## Minimal black product UI

Keep:

- negative space;
- restraint;
- crisp typography;
- luxury through simplicity.

Avoid:

- low-information screens in operational workflows.

## Split onboarding UI

Keep:

- narrative + action separation;
- step-driven composition.

Use primarily for:

- document ingestion;
- empty states;
- guided first-run flows.

## "Clarity in Complexity" editorial hero

This is the closest visual philosophy to LIMEN.

Keep:

- calm composition;
- visual hierarchy;
- large whitespace;
- soft depth;
- premium typography.

## Warm light onboarding

Use only as a subtle human accent.

Do not turn the clinical workspace into peach/orange branding.

## Glass settings panel

Use for:

- settings;
- inspectors;
- drawers;
- side panels;
- context overlays.

---

# 6. What LIMEN Must NOT Look Like

Forbidden visual patterns:

- generic shadcn dashboard with default styles;
- neon cyberpunk;
- gamer HUD;
- glowing borders on every card;
- gradient on every button;
- blur on every surface;
- huge rounded cards everywhere;
- random purple SaaS gradient;
- excessive icons;
- glass with illegible text;
- decorative particles;
- animated backgrounds competing with clinical data;
- 3D gimmicks;
- skeleton loaders that never reflect actual layout;
- Dribbble-only controls with poor UX;
- hidden critical actions for visual cleanliness.

---

# 7. Brand Color System

## Core palette

| Token | Hex | Role |
|---|---:|---|
| Midnight 950 | `#05070B` | application canvas |
| Midnight 925 | `#0A1018` | primary brand dark |
| Midnight 900 | `#111925` | elevated surface |
| Midnight 850 | `#182333` | active elevated surface |
| LIMEN Cyan | `#2AA8A8` | intelligence / focus / primary |
| Evidence Teal | `#1A7D7D` | evidence / retrieval |
| Atmosphere Beam | `#6A8AAA` | environmental light only — never a state |
| Voice Patient | `#4F8FFF` | patient speech on the audio sphere |
| Voice Agent | `#F08A3C` | agent speech on the audio sphere |
| Ice 50 | `#F4F7F9` | brightest content |
| Ice 100 | `#E6EEF2` | primary light text |
| Slate 300 | `#9AADB8` | secondary text |
| Slate 500 | `#657887` | tertiary text |
| TRAZA Violet | `#7D6FD4` | observability / audit |
| Signal Green | `#3DB87E` | expected recovery |
| Signal Amber | `#E5A83A` | uncertainty / review |
| Signal Coral | `#E2555F` | escalation / danger |
| Signal Coral | `#EE5D68` | escalation / danger |
| Soft Apricot | `#F2C6A8` | rare human/warm accent |

---

# 8. Semantic Color Rules

Color is never merely decorative in operational screens.

```text
CYAN    = intelligence / active control / focus
TEAL    = evidence / knowledge
VIOLET  = traceability / observability
GREEN   = expected / healthy status
AMBER   = uncertainty / warning / review
CORAL   = escalation / destructive / critical
```

Never use:

- green for unrelated success if it could be confused with clinical GREEN;
- red for decorative emphasis;
- amber for generic selected state.

Clinical semantics take priority.

---

# 9. CSS Design Tokens

Create:

```text
apps/web/src/styles/tokens.css
```

Baseline:

```css
:root {
  --limen-bg-0: #05070b;
  --limen-bg-1: #0a1018;
  --limen-bg-2: #111925;
  --limen-bg-3: #182333;

  --limen-cyan: #2aa8a8;
  --limen-teal: #1a7d7d;
  --limen-violet: #7d6fd4;

  --limen-green: #3db87e;
  --limen-amber: #e5a83a;
  --limen-coral: #e2555f;

  --limen-voice-patient: #4f8fff;
  --limen-voice-agent: #f08a3c;
  --limen-beam: #6a8aaa;

  --limen-ice: #e6eef2;
  --limen-white: #f4f7f9;
  --limen-text-2: #9aadb8;
  --limen-text-3: #657887;

  --glass-surface: rgba(14, 22, 34, 0.55);
  --glass-surface-strong: rgba(10, 16, 24, 0.78);
  --glass-border: rgba(230, 240, 245, 0.08);
  --glass-highlight: rgba(255, 255, 255, 0.04);
  --glass-sheen: rgba(255, 255, 255, 0.06);

  --shadow-panel: 0 16px 40px rgba(0, 0, 0, 0.32);
  --shadow-float: 0 24px 72px rgba(0, 0, 0, 0.42);

  --radius-xs: 6px;
  --radius-sm: 10px;
  --radius-md: 14px;
  --radius-lg: 18px;
  --radius-xl: 24px;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;
}
```

## Dual ground: dark and light

`:root` (and `[data-theme="dark"]`) is the default clinical ground.
`[data-theme="light"]` overrides the **same token names** with a bright canvas, so
no component branches on the theme.

Rules that keep the two grounds honest:

- Content tokens are semantic, not literal. `--limen-white` means "brightest
  content", so in light mode it resolves to near-black. Never read a token as a
  colour name.
- High-contrast actions use the pair `--limen-inverse-fill` / `--limen-inverse-ink`,
  which flip together. `--limen-ink-on-accent` is the ink on a saturated fill.
- Atmosphere gradients share one definition and differ only by the `--atmo-beam`
  / `--atmo-cyan` / `--atmo-teal` mix ratios.
- Clinical semantics survive the flip: green/amber/coral/teal/violet keep their
  meaning and darken enough to stay legible on a bright canvas.
- Every theme-scoped token must be declared in **both** blocks. `design-tokens.test.ts`
  fails the build otherwise.
- Colour never reaches a component as `text-[var(--token)]`: Tailwind resolves an
  unhinted arbitrary value as a font size and silently drops the colour. Use the
  named utilities from the `@theme inline` bridge.

Preference: `ThemeProvider` writes `data-theme` on `<html>` and persists
`limen.theme`; an inline script in `index.html` applies it before first paint.
Default dark, light opt-in.

## Language

`i18next` with the namespaces `common`, `shell`, `landing`, `auth`. Default `es`
(the patient-facing voice loop is Spanish), persisted as `limen.locale`, and
switchable from the landing nav, the auth screens, and the account menu.

Backend clinical vocabulary (`GREEN`, `UNKNOWN`, `CONFLICTING`, document status)
is **never** translated — it is a contract value, not interface copy.

---

# 10. Glass Specification

Glassmorphism is a material system, not a theme toggle.

## Level 0 — Solid

Use for:

- dense tables;
- logs;
- long text;
- critical forms.

```css
background: rgba(6, 18, 31, 0.96);
```

## Level 1 — Soft glass

Use for:

- cards;
- secondary panels.

```css
background: rgba(10, 30, 46, 0.64);
backdrop-filter: blur(14px) saturate(115%);
border: 1px solid rgba(225, 248, 248, 0.10);
```

## Level 2 — Inspector glass

Use for:

- drawers;
- trace inspector;
- settings;
- side panes.

```css
background: rgba(7, 26, 43, 0.76);
backdrop-filter: blur(22px) saturate(125%);
border: 1px solid rgba(225, 248, 248, 0.12);
```

## Level 3 — Modal/floating

Use sparingly.

```css
background: rgba(7, 20, 32, 0.88);
backdrop-filter: blur(30px) saturate(130%);
```

## Rule

No more than **two visible glass-depth levels** in one local region.

---

# 11. Typography

## Operational UI

Primary:

```text
Manrope Variable
```

Fallback:

```text
Inter Variable, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
```

Manrope carries the operational UI, including empty states, upload surfaces, and
inspectors. Instrument Serif is a landing accent only.

## Editorial accent

Optional:

```text
Instrument Serif
```

Allowed only for rare landing accents outside the claim headline.

Never use serif for:

- workspace empty states;
- clinical values;
- tables;
- forms;
- metrics;
- alerts.

## Scale

```text
Display XL    64–72 / 0.96
Display L     48–56 / 1.00
H1            36–40 / 1.10
H2            28–32 / 1.15
H3            20–24 / 1.25
Body L        17–18 / 1.55
Body          15–16 / 1.55
Body S        13–14 / 1.45
Label         12–13 / 1.30
Metric        tabular numerals
```

---

# 12. Layout System

## Application shell

Desktop:

```text
┌──────────────────────────────────────────────────────────────┐
│ Context Header                                               │
├───────────┬──────────────────────────────────────────────────┤
│ Nav Rail  │ Workspace                                        │
│ 88 px     │                                                  │
│           │                                                  │
└───────────┴──────────────────────────────────────────────────┘
```

Optional contextual inspector:

```text
┌───────────┬─────────────────────────────┬────────────────────┐
│ Nav Rail  │ Workspace                   │ Inspector          │
│           │                             │ 320–380 px         │
└───────────┴─────────────────────────────┴────────────────────┘
```

## Width

- full viewport application shell;
- no centered `max-width: 1200px` dashboard cage for operational screens;
- content-specific maximum widths inside panels only.

---

# 13. Navigation

Primary navigation:

```text
Call
Knowledge
Trace
Sessions
Settings
```

Use a compact left rail.

Visual behavior:

- icon + label on desktop;
- selected item uses subtle solid/glass pill;
- no colored icon rainbow;
- cyan selected-state accent;
- tooltips on collapsed state.

---

# 14. Frontend Architecture

```text
apps/web/src/
│
├── app/
│   ├── App.tsx
│   ├── providers/
│   ├── router/
│   └── layouts/
│
├── pages/
│   ├── Landing/
│   ├── Call/
│   ├── Knowledge/
│   ├── Trace/
│   ├── Sessions/
│   └── Settings/
│
├── features/
│   ├── call-session/
│   ├── knowledge-base/
│   ├── traceability/
│   ├── sessions/
│   └── diagnostics/
│
├── components/
│   ├── primitives/
│   ├── shell/
│   ├── glass/
│   ├── feedback/
│   ├── data/
│   └── brand/
│
├── audio/
│   ├── recorder.ts
│   ├── vad.ts
│   ├── playback.ts
│   └── audio-session.ts
│
├── api/
│   ├── client.ts
│   ├── calls.ts
│   ├── knowledge.ts
│   ├── traces.ts
│   └── types.ts
│
├── state/
│   ├── call-store.ts
│   └── ui-store.ts
│
├── hooks/
├── lib/
├── styles/
│   ├── globals.css
│   ├── tokens.css
│   ├── typography.css
│   └── motion.css
│
└── test/
```

---

# 15. Frontend Stack

Canonical baseline:

| Area | Choice |
|---|---|
| Runtime | React |
| Language | TypeScript |
| Build | Vite |
| Styling | Tailwind + CSS variables |
| Accessible primitives | Radix UI |
| Server state | TanStack Query |
| Local state | Zustand |
| Routing | React Router |
| Icons | Lucide |
| Motion | Framer Motion, sparingly |
| Unit tests | Vitest |
| Component tests | React Testing Library |
| E2E | Playwright |
| Audio | Web Audio API |
| Realtime | native WebSocket |

## Note on component libraries

Radix may supply behavior.

LIMEN must own the visual language.

Do not import a template theme and call it finished.

---

# 16. Screen Specification — Call

## Primary objective

Make the voice interaction calm, immediate, and observable without overwhelming the patient-facing experience.

## Layout

```text
┌─────────────────────────────────────────────────────────────┐
│ Patient / Session                Connected · 03:42          │
├───────────────────────────────────┬─────────────────────────┤
│                                   │                         │
│        CALL EXPERIENCE            │   LIVE CONTEXT          │
│                                   │                         │
│            voice orb              │  Risk       YELLOW      │
│            waveform               │  Unknowns   2           │
│            status                 │  Sources    3           │
│                                   │                         │
│       latest transcript           │  Clinical state         │
│                                   │  Evidence preview       │
│                                   │                         │
├───────────────────────────────────┴─────────────────────────┤
│                        End session                          │
└─────────────────────────────────────────────────────────────┘
```

## Voice states

Must visually distinguish:

```text
IDLE
REQUESTING_MIC
LISTENING
PROCESSING_STT
THINKING
SPEAKING
INTERRUPTED
ERROR
ENDED
```

The Call experience uses a reactive particle sphere (`VoiceOrb`):

- patient turns (`LISTENING`, `INTERRUPTED`) → blue→white field;
- agent turns (`SPEAKING`) → orange→white field;
- idle / ended → silver mesh at rest;
- energy comes from measured mic level when the patient speaks.

Never use one generic spinner for every state.
Voice sphere colors are speaker identity only — never clinical risk.

## Barge-in

When patient speech is detected while TTS plays:

- stop playback;
- change agent state to Listening;
- preserve the interrupted agent turn in trace;
- do not overlap voices.

---

# 17. Screen Specification — Knowledge

## Primary objective

Make G5 obvious and verifiable.

Layout:

```text
┌───────────────────────────────┬─────────────────────────────┐
│ Knowledge Base                │ Selected Source             │
│                               │                             │
│ + Add source                  │ filename                    │
│                               │ version                     │
│ AVAILABLE  protocol-a.pdf     │ sha256                      │
│ PROCESSING test.pdf           │ pages/chunks                │
│ REMOVED    old.pdf            │ processing state            │
│                               │                             │
│                               │ Verify retrieval            │
│                               │ Delete source               │
└───────────────────────────────┴─────────────────────────────┘
```

## Upload states

```text
UPLOADING
PROCESSING
AVAILABLE
FAILED
REMOVING
REMOVED
```

No optimistic fake "AVAILABLE".

The API state is authoritative.

---

# 18. Screen Specification — TRAZA

## Primary objective

Turn hidden AI behavior into an inspectable engineering artifact.

```text
┌──────────────────────────────┬─────────────────────────────┐
│ Timeline                     │ Inspector                   │
│                              │                             │
│ Patient statement            │ Decision: YELLOW            │
│ ↓                            │ Confidence / uncertainty    │
│ Clinical extraction          │                             │
│ ↓                            │ Evidence                    │
│ Retrieval                    │ source.pdf · p.17           │
│ ↓                            │ source-2.pdf · p.4          │
│ Safety evaluation            │                             │
│ ↓                            │ Activated rules             │
│ Final response               │ Metrics                     │
└──────────────────────────────┴─────────────────────────────┘
```

Use violet only for trace/audit semantics.

Evidence links use teal.

Risk uses clinical green/amber/coral.

---

# 19. Screen Specification — Sessions

A lightweight operational list.

Columns:

- call ID;
- patient ID/display alias;
- procedure;
- postoperative day;
- start time;
- final risk;
- escalated;
- duration;
- trace link.

Do not build a huge analytics product.

---

# 20. Screen Specification — Settings

Settings is the **client preference surface**, not an ops dashboard.
All preference blocks live in **one glass container**; session actions sit last.

Primary sections (top → bottom):

```text
appearance     dark / light (explicit choice, browser-local)
language       ES / EN interface labels
account        signed-in identity (read-only)
microphone     real capture check before a call
diagnostics    collapsed runtime verification
session        delete account → sign out (destructive / exit, last)
```

Runtime diagnostics (model, persistence, knowledge, STT/TTS, telemetry) stay
behind a collapsed disclosure for verification. Missing signals remain unknown.
Delete account calls `DELETE /api/auth/me` after an explicit confirmation.

---

# 21. Landing Page

A commercial product entrance that stays usable, not a sales site. It answers what
LIMEN does, for whom, how a session moves, and how client data is separated — then
sends the visitor to an account.

Structure (wide marketing surface, paced sections — not a dense card stack):

```text
sticky floating nav   shared column glass bar · brand · how it works · security · language · theme · auth
hero                  compact brand stack | VoiceOrb (idle ↔ patient blue only)
problem               open editorial (no card cage)
how it works          section lead + three glass step tiles
system pillars        section lead + four glass tiles
data & security       open lead + guarantee list
current state         quiet band, stated plainly
closing tile          create account / enter workspace
footer                brand, tagline, section links, license
```

Headline (copy lives in the `landing` i18n namespace, ES and EN):

> **Seguimiento postoperatorio por voz, con la duda a la vista.**

Composition rules:

- The hero carries brand, one headline, one sentence, and the CTA pair over a
  large centered voice sphere. No badges, no invented stat strip.
- The sphere is the dominant right-side visual. On the landing it only moves
  between idle and patient blue while someone speaks — never agent orange.
  The call workspace is where the field alternates idle / patient blue / agent
  orange. If the mic is blocked, the landing sphere stays idle.
- One shared column (`max-w-[72rem]`) for nav, hero, and every body section so
  the page reads as one composition instead of a narrow stack in a wide void.
- Glass tiles are for interactive/section blocks only (steps, pillars, closing).
  Editorial bands (problem, status, security lead) stay open for air.
- No forced italics in the claim. Serif is an accent elsewhere, never the headline.
- CTAs are auth-aware: a visitor sees *create account* / *sign in*; a signed-in
  client sees *enter workspace*.

Never on this surface: invented metrics, pricing, testimonials, waitlist,
competition badges, or marketing navigation beyond product entry.

---

# 22. Core Components

Required reusable components:

```text
AppShell
NavRail
ContextHeader

GlassPanel
SolidPanel
InspectorPanel

StatusChip
RiskBadge
Metric
MetricStrip

Button
IconButton
TextField
Select
Toggle
Dialog
Drawer
Tooltip

DocumentRow
DocumentStatus
UploadDropzone
EvidenceCitation

VoiceOrb
Waveform
CallState
TranscriptTurn

TraceEvent
TraceTimeline
DecisionCard
ClinicalStateGrid

EmptyState
ErrorState
LoadingState
ConnectionState
```

---

# 23. Buttons

## Inverse

Solid ice on dark. Reserved for the entry surface, where the dominant action is
not an operational control and cyan would compete with clinical meaning.

## Primary

Cyan, mostly solid.

Use for one dominant action per region inside the workspace.

## Secondary

Dark glass/outline.

## Destructive

Coral only for:

- delete;
- destructive reset;
- critical stop.

## Clinical risk actions

Do not make risk levels look like ordinary buttons unless interactive behavior requires it.

---

# 24. Forms

Rules:

- label always visible;
- placeholder is not a label;
- focus ring uses cyan;
- errors include text, not color only;
- destructive confirmation names the document/action;
- upload supports drag/drop and file picker;
- progress is real backend progress/state.

---

# 25. Motion Language

Target:

```text
180–260 ms
```

Use:

- opacity;
- translate 8–12px;
- scale max 0.98 → 1.00;
- background/border interpolation.

Avoid:

- bounce;
- spring overshoot in clinical actions;
- dramatic parallax;
- infinite glowing animations.

## Reduced motion

Respect:

```css
@media (prefers-reduced-motion: reduce)
```

Core interaction cannot depend on animation.

---

# 26. Accessibility

Minimum:

- WCAG AA contrast;
- keyboard navigation;
- visible focus;
- semantic labels;
- `aria-live` for call state changes where appropriate;
- no color-only status encoding;
- minimum interactive target around 40–44px;
- transcript text scalable;
- microphone permission errors explained in text.

---

# 27. Responsive Strategy

## Desktop ≥ 1200

Full app shell + contextual inspector.

## Tablet 768–1199

Inspector becomes drawer or collapsible pane.

## Mobile < 768

Challenge demo is not optimized around mobile, but core actions must remain usable.

Priority:

1. call controls;
2. knowledge CRUD;
3. trace reading.

No separate mobile product.

---

# 28. Data & State Rules

## TanStack Query

Use for server-owned state:

- documents;
- sessions;
- traces;
- API health;
- settings from backend.

## Zustand

Use for ephemeral client state:

- microphone state;
- playback;
- current call UI;
- drawer state.

Do NOT mirror complete server responses into Zustand.

---

# 29. Realtime Contract

WebSocket handles:

- audio or audio-related events;
- call lifecycle;
- incremental runtime events.

Do not use WebSocket for ordinary CRUD where HTTP is simpler.

Example event shape:

```json
{
  "type": "call.state",
  "call_id": "...",
  "sequence": 42,
  "timestamp": "...",
  "payload": {
    "state": "SPEAKING"
  }
}
```

All event types must be discriminated unions in TypeScript.

---

# 30. Error Experience

Never show:

```text
Something went wrong.
```

when a meaningful error is known.

Examples:

### Microphone denied

```text
Microphone access is blocked.
Enable microphone permission in your browser and try again.
```

### STT unavailable

```text
Speech recognition is temporarily unavailable.
Your call session is preserved. Retry transcription.
```

### Document failed

Show:

- filename;
- stage;
- failure message;
- retry action.

---

# 31. Performance Budget

Frontend priorities:

- avoid giant animation libraries beyond what is needed;
- lazy-load Trace/Settings if useful;
- no uncompressed background video;
- no multi-megabyte decorative hero art in application shell;
- avoid re-rendering waveform on full React tree;
- audio visualization should use canvas/WebAudio efficiently.

Visual polish cannot damage voice latency.

---

# 32. Frontend Testing

## Unit/component

Test:

- risk badge semantics;
- document states;
- upload errors;
- call state transitions;
- accessibility labels.

## Integration

Test:

- call page API state;
- knowledge add/delete;
- trace rendering.

## E2E smoke

At minimum:

```text
open app
backend healthy
open call
microphone permission handling
open knowledge
upload test document
observe AVAILABLE
delete
observe REMOVED
open trace
```

---

# 33. Visual QA Checklist

Before considering a screen complete:

```text
[ ] uses LIMEN tokens
[ ] no arbitrary hex in component
[ ] no generic template styling
[ ] glass supports hierarchy rather than decoration
[ ] contrast passes
[ ] all states exist
[ ] semantic colors are correct
[ ] empty/error/loading states exist
[ ] keyboard navigation works
[ ] reduced motion works
[ ] 1440px desktop looks intentional
[ ] 1024px still works
[ ] mobile critical action is reachable
```

---

# 34. Final Frontend Verdict

LIMEN should visually communicate:

> **calm intelligence under clinical uncertainty.**

The interface should be memorable because of:

- restraint;
- hierarchy;
- transparency of reasoning;
- controlled material depth;

not because it is visually loud.

---

<div align="center">

## ◈ Design Rule

**If an effect makes the interface prettier but makes clinical state, evidence, or action harder to read, remove the effect.**

</div>
