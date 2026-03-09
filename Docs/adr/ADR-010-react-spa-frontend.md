# ADR-010: React SPA Frontend (Vite + Tailwind v4 + React Router v7)
<!-- Architecture Decision Record
     Place in: docs/adr/ADR-010-react-spa-frontend.md
     Reference from AGENTS.md so the agent knows these exist.
     The agent reads ADRs before making structural decisions. -->

**Date:** 2026-03-09
**Status:** Accepted
**Deciders:** Shreyas Jagannath, Claude Code
**Version:** v0.5.2

---

## Context

CR8's frontend was a Jinja2 server-rendered prototype — a single HTML file with inline
JavaScript. This worked for early development but could not support the features required
for v0.5.2 and beyond:

- **Real-time pipeline progress** with stage-aware ETA, log streaming, and cancel support
  requires structured client-side state and polling — awkward with server-rendered HTML.
- **JWT authentication** with in-memory access tokens, silent refresh via httpOnly cookies,
  and protected routes demands a proper client-side auth layer.
- **Component reuse** across upload, progress, results, and upcoming quiz UI (Phase 4)
  requires a component model — Jinja2 macros are insufficient.
- **Glassmorphism design system** with backdrop-blur, transparency layers, and responsive
  layouts benefits from utility-first CSS with design tokens.

The decision needed to be made at v0.5.2 because the Jinja2 prototype was blocking
progress on the dashboard, file upload drag-drop, and progress visualization features.

## Decision

> We will use **React 19 + Vite 7 + Tailwind CSS v4 + React Router v7 + Tanstack Query v5**
> as the frontend stack, served as a static SPA from FastAPI with a dual-serve fallback
> to Jinja2 during the migration period.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **React 19 + Vite 7 + Tailwind v4 (chosen)** | Largest ecosystem; best component libraries (shadcn/ui); strongest hiring pool; Vite HMR is fast; Tanstack Query handles server-state elegantly; Tailwind v4 CSS-native config fits glassmorphism | Requires Node.js build step; two package managers (uv + npm); heavier bundle than HTMX |
| Enhanced Jinja2 + HTMX | No build step; progressive enhancement; minimal JS; stays in Python ecosystem | Real-time progress polling is awkward; JWT auth in pure HTML is clunky; no component reuse for quiz UI; poor state management for multi-step flows |
| Next.js 15 (SSR) | SEO-friendly; file-based routing; React ecosystem access | SSR is overkill for auth-gated SPA; adds Node.js runtime to Cloud Run (dual-runtime); RSC CVEs (CVE-2025-55182) are a concern; heavier deployment |
| Vue 3 + Vite | Simpler learning curve; good DX; single-file components | Smaller ecosystem than React; fewer component libraries at shadcn/ui quality; smaller hiring pool |
| Svelte/SvelteKit | Smallest bundles; excellent DX; truly reactive | Smallest community; fewest battle-tested component libraries; hardest to hire for |

## Consequences

**Positive:**
- Component reuse across all pages (upload, progress, results, future quiz UI)
- Real-time progress with Tanstack Query polling (`refetchInterval`) and structured cache
- JWT auth flow with in-memory tokens and silent refresh — no localStorage exposure
- Glassmorphism design system via Tailwind v4 `@theme` directives and `@utility` layers
- Vite dev server proxies `/api` to FastAPI — no CORS issues in development
- Type safety end-to-end with TypeScript strict mode
- Testing infrastructure: Vitest for unit tests, Playwright for E2E

**Negative / Trade-offs:**
- Two package managers: `uv` (Python) and `npm` (Node.js) — increases onboarding friction
- Build step required: `make build-frontend` must run before production deployment
- Bundle size is larger than HTMX/vanilla JS (~150KB gzipped for React + Router + Query)
- Jinja2 templates kept temporarily (dual-serve pattern) — tech debt until full migration

**Neutral:**
- FastAPI remains the sole production server — React builds to static files, no Node.js in prod
- Vite dev server runs on port 5173; FastAPI on 8080 — two processes during development
- Browser support floor raised to Safari 16.4+, Chrome 111+, Firefox 128+ (Tailwind v4 requirement)

## Implementation Notes

- **Files affected:**
  - `frontend/react-app/` — entire SPA source tree (package.json, vite.config.ts, src/)
  - `frontend/app.py` — SPA catch-all route: detects `frontend/static/index.html`, serves React or falls back to Jinja2
  - `frontend/static/` — gitignored build output copied from `react-app/dist/`
  - `Makefile` — `build-frontend` and `e2e` targets

- **Patterns to follow:**
  - Access tokens in memory only — never in localStorage or cookies
  - All API calls go through `src/api/client.ts` (JWT-aware fetch wrapper with auto-refresh on 401)
  - All GET requests use Tanstack Query hooks — no raw `useEffect` + `fetch`
  - Pages in `src/pages/`, reusable components in `src/components/`, API modules in `src/api/`
  - Tailwind design tokens defined in `src/index.css` via `@theme` — no `tailwind.config.ts`

- **Things to avoid:**
  - Do NOT use `localStorage` for tokens (XSS vector)
  - Do NOT add a Node.js runtime to the production Docker image — React is static assets only
  - Do NOT import from `react-router-dom` — v7 uses `react-router` directly
  - Do NOT use Tailwind v3 `tailwind.config.js` patterns — v4 uses CSS-native `@theme`
  - Do NOT create API route handlers in the React app — all API logic lives in FastAPI

## References

- `frontend/react-app/package.json` — dependency versions and scripts
- `frontend/react-app/vite.config.ts` — Vite config with FastAPI proxy and Vitest setup
- `frontend/react-app/src/App.tsx` — routing setup with protected routes
- `frontend/app.py` — dual-serve pattern (React SPA vs Jinja2 fallback)
- `docs/research/FRONTEND_STACK_SUMMARY.md` — full stack research with CVE analysis
- `docs/research/react-vite-fastapi.md` — React + Vite + FastAPI integration research
- `docs/research/tailwind-css-v4.md` — Tailwind v4 migration and design system research
- ADR-002: Dual auth strategy (JWT + legacy session) — auth architecture this SPA consumes
