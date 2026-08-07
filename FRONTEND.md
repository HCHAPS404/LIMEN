# LIMEN Frontend — Clinical Editorial Glass

> Foundation stub derived from `ARCHITECTURE.md`. Expand as screens mature.

## Stack

- React + Vite + TypeScript (strict)
- TanStack Query for server state
- Zustand for local UI/call state
- Radix primitives where interaction requires them
- React Router for shell navigation

## Surfaces

| Route | Purpose | Status |
|-------|---------|--------|
| `/call` | Voice call interface | Planned (shell) |
| `/knowledge` | Live knowledge admin | Planned (shell) |
| `/traza` | Decision trace | Planned (shell) |
| `/sessions` | Call history | Planned (shell) |
| `/settings` | Diagnostics / model declaration | In Progress (health wired) |

## Design tokens

Defined in `apps/web/src/styles/tokens.css`:

- Cool clinical slate backgrounds (not purple-on-white, not cream/terracotta)
- Display: Source Serif 4
- Body: IBM Plex Sans
- Semantic risk colors: green / yellow / orange / red
- Glass borders + restrained motion; honor `prefers-reduced-motion`

## Rules

- No arbitrary color literals in components — use tokens.
- No default shadcn look.
- Brand (LIMEN) must remain a primary signal in the shell.
- First viewport of promotional surfaces stays sparse; this app shell is operational, not a marketing landing page.
- Every interactive screen needs loading / empty / error / success / disabled states when data-bound.
