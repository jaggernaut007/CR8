# CR8 v0.5.2 Frontend Stack — Executive Summary

**Date:** 2026-03-09
**Researcher:** Claude Code (Research Assistant)
**Status:** Ready for implementation

---

## Stack Overview

| Component | Version | Status | Notes |
|-----------|---------|--------|-------|
| React | 19.2.4 | ✓ Safe | Stable; RSC vulnerabilities don't apply to SPA |
| Vite | 6.2.6 | ✓ Safe | LTS-adjacent stable branch with security patches |
| React Router | 7.13.1 | ✓ Safe | Latest with security updates |
| Tailwind CSS | 4.0.1+ | ✓ Safe | 5x faster builds; CSS-native config |
| TanStack Query | 5.90.21 | ✓ Safe | Industry-standard for server-state management |
| shadcn/ui | CLI-based | ✓ Safe | Components copied; no npm package |
| TypeScript | 5.6.3 | ✓ Safe | Strict mode throughout |

**Verdict:** All versions are production-ready with zero critical security blockers. This is a modern, well-maintained stack.

---

## Critical Security Findings

### React 19 CVEs (NOT a blocker for CR8 SPA)

**CVE-2025-55182** (CVSS 10.0 — Remote Code Execution)
**CVE-2026-23864** (CVSS 7.5 — Denial of Service)

Both CVEs affect **React Server Components (RSC)** only. CR8's SPA does NOT use RSC, so these vulnerabilities do not apply.

**What this means:**
- Plain React SPAs (like CR8) are unaffected
- Only affects frameworks with `use server` directives (Next.js, Remix, etc.)
- React 19.2.4 includes the latest patches if RSC were used
- Safe to proceed with React 19

**Source:** [React Security Advisory](https://react.dev/blog/2025/12/03/critical-security-vulnerability-in-react-server-components)

### Vite 6 CVEs (patched in 6.2.6+)

**CVE-2025-31125** (CVSS 5.3 — Arbitrary File Read)
**CVE-2025-32395** (CVSS 5.3 — Information Exposure)

Both are fixed in Vite 6.2.6+. These only affect development servers explicitly exposed to the network (`--host` or `server.host: '0.0.0.0'`). Local development is safe.

**Recommendation:** Use Vite 6.2.6 (not 7.x) for long-term stability.

**Source:** [Vite Security Notice](https://security.snyk.io/package/npm/vite)

### React Router 7 CVEs (patched in 7.13.1)

**CVE-2026-22029** (XSS via Open Redirects)
**CVE-2026-21884** (ScrollRestoration XSS)

Both fixed in React Router 7.12.0+. Version 7.13.1 is the latest.

**Recommendation:** Use React Router 7.13.1 (latest).

**Source:** [Netlify Changelog](https://www.netlify.com/changelog/2026-01-15-react-router-remix-security-vulnerabilities/)

### All Other Libraries (Clean)

- **Tailwind CSS v4:** No known CVEs
- **TanStack Query:** No CVEs in core package (minor XSS in unused experimental package)
- **shadcn/ui:** No CVEs; components are copied source code (supply chain safe)

---

## Implementation Path

### Phase 1: Project Setup (1-2 hours)

```bash
# 1. Create Node.js project structure
mkdir frontend
cd frontend
npm init -y

# 2. Install core dependencies
npm install react@19.2.4 react-dom@19.2.4 react-router-dom@7.13.1 @tanstack/react-query@5.90.21

# 3. Install dev dependencies
npm install -D vite@6.2.6 @vitejs/plugin-react@4.3.4 typescript@5.6.3
npm install -D tailwindcss@4.0.1 postcss@8.4.49 autoprefixer@10.4.20

# 4. Initialize TypeScript
npx tsc --init

# 5. Initialize Tailwind CSS v4
npx tailwindcss init -p

# 6. Initialize shadcn/ui
npx shadcn-ui@latest init
# Follow prompts; choose:
# - Framework: React
# - TypeScript: Yes
# - CSS mode: Default (new)

# 7. Add core shadcn/ui components
npx shadcn-ui@latest add button card input label dialog tabs form select
```

### Phase 2: Configuration (30 minutes)

Create these files with content from research notes:

1. **vite.config.ts** — includes FastAPI proxy setup
2. **tailwind.config.ts** — minimal, CSS-native config
3. **src/index.css** — @theme directives and custom utilities
4. **src/main.tsx** — QueryClientProvider + RouterProvider setup
5. **tsconfig.json** — React 19 JSX runtime, strict mode

All templates are in the research notes.

### Phase 3: Component Library (2-4 hours)

1. Set up component file structure: `src/components/ui/`, `src/components/`, `src/pages/`, `src/hooks/queries/`
2. Add more shadcn/ui components as needed: `table`, `pagination`, `toast`, `dropdown-menu`, etc.
3. Create custom hooks wrapping `useQuery`/`useMutation` for each API endpoint
4. Build core pages: Jobs list, Job detail, Upload, Settings

### Phase 4: Integration with FastAPI (1-2 hours)

1. Update `frontend/app.py` to serve `frontend/static/` catch-all
2. Test Vite dev proxy: `npm run dev` should hit `http://localhost:8080/api/*`
3. Add CORS middleware to FastAPI (allow `http://localhost:5173` in dev)
4. Test full flow: SPA → Query → FastAPI → Response

### Phase 5: Build & Deployment (1 hour)

1. Set up build script: `npm run build` outputs to `dist/`
2. Add post-build hook to copy `dist/` to `frontend/static/`
3. Test production build locally: `npm run build && python -m uvicorn ...`
4. Deploy to Cloud Run (no changes to Dockerfile needed; SPA is static assets)

---

## Key Configuration Snippets

### Vite Proxy Setup (vite.config.ts)

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8080',
      changeOrigin: true,
    },
  },
},
```

### React Router Entry (src/main.tsx)

```typescript
const router = createBrowserRouter([
  { path: '/', element: <App />, errorElement: <NotFound /> },
  // Add routes here
])

ReactDOM.createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={new QueryClient()}>
    <RouterProvider router={router} />
  </QueryClientProvider>,
)
```

### Tailwind v4 Design Tokens (src/index.css)

```css
@import "tailwindcss";

@theme {
  --color-primary: #0066cc;
  --color-secondary: #f0f0f0;
  /* ... more tokens ... */
}

@layer components {
  .glass { @apply backdrop-blur-md bg-white/10 border border-white/20 rounded-xl; }
  .btn-primary { @apply bg-primary text-white hover:bg-primary-dark; }
}
```

### TanStack Query Custom Hook (src/hooks/queries/useJobs.ts)

```typescript
export function useJobs(filters?: { status?: string }) {
  return useQuery({
    queryKey: ['jobs', filters],
    queryFn: async () => {
      const response = await fetch('/api/jobs')
      if (!response.ok) throw new Error('Failed to fetch')
      return response.json()
    },
    staleTime: 1000 * 60 * 5,
  })
}
```

---

## Breaking Changes & Compatibility

### React 19 Breaking Changes (Handled)
- ✓ No PropTypes needed (use TypeScript)
- ✓ No defaultProps (use ES6 defaults)
- ✓ Ref cleanup functions (rarely needed in SPA)
- ✓ Forward refs (no longer required for all cases)

### Tailwind v4 Breaking Changes (Handled)
- ✓ Config moved to CSS `@theme`
- ✓ Class renames (e.g., `flex-grow` → `grow`) auto-migrated
- ✓ Deprecated classes removed (auto-migrate with CLI tool)

### React Router v7 Breaking Changes (None for new SPA)
- Starting fresh, so no migration needed
- Use `createBrowserRouter` (modern API)

---

## Browser Support

Minimum supported browsers:
- Safari 16.4+
- Chrome 111+
- Firefox 128+
- Edge 79+

This is due to Tailwind v4's use of modern CSS features (`@property`, `color-mix()`, cascade layers).

---

## File Structure (Recommended)

```
frontend/
├── package.json                 (dependencies, scripts)
├── vite.config.ts              (Vite config with proxy)
├── tailwind.config.ts           (Tailwind minimal config)
├── tsconfig.json                (TypeScript strict mode)
├── postcss.config.cjs           (auto-generated by Tailwind init)
├── components.json              (auto-generated by shadcn init)
├── src/
│   ├── main.tsx                (entry: Router + Query + devtools)
│   ├── index.css               (@theme, @layer directives)
│   ├── App.tsx                 (root component)
│   ├── pages/                  (route-level components)
│   │   ├── JobsList.tsx
│   │   ├── JobDetail.tsx
│   │   ├── Upload.tsx
│   │   └── NotFound.tsx
│   ├── components/
│   │   ├── ui/                 (shadcn/ui components — auto-generated)
│   │   ├── JobCard.tsx         (custom components)
│   │   ├── Header.tsx
│   │   └── Sidebar.tsx
│   ├── hooks/
│   │   └── queries/            (custom Query hooks)
│   │       ├── useJobs.ts
│   │       ├── useCreateJob.ts
│   │       └── useJobDetail.ts
│   ├── lib/
│   │   ├── api.ts              (fetch client, error handling)
│   │   └── utils.ts            (utility functions)
│   └── types/
│       └── api.ts              (TypeScript types for API responses)
├── dist/                        (generated on build)
└── .gitignore                   (node_modules, dist/, .vite/)
```

---

## Next Steps

1. **Read the full research notes** before starting implementation:
   - `/docs/research/react-vite-fastapi.md` — Core setup, Vite proxy, React Router
   - `/docs/research/tailwind-css-v4.md` — Design tokens, glassmorphism, custom utilities
   - `/docs/research/shadcn-ui-tanstack-query.md` — Component library, data fetching

2. **Create a new branch:** `git checkout -b feature/react-spa-shell`

3. **Follow Phase 1-5** implementation path above

4. **Test locally:**
   ```bash
   npm run dev          # Vite dev server on 5173
   python -m uvicorn frontend.app:app --reload  # FastAPI on 8080
   # Browser: http://localhost:5173
   # Test API proxy: fetch('/api/jobs') should reach FastAPI
   ```

5. **Create PR** with full test coverage for frontend components

---

## Production Checklist

- [ ] All React components have TypeScript types
- [ ] All API calls use TanStack Query hooks
- [ ] All forms use shadcn/ui + React Hook Form
- [ ] CSS uses Tailwind utilities (no custom CSS except `@layer`)
- [ ] Vite build produces minified, tree-shaken output
- [ ] Environment variables properly configured for prod (API base URL, etc.)
- [ ] No console.logs or debugger statements in prod code
- [ ] Tested on Safari 16.4+, Chrome 111+, Firefox 128+
- [ ] CORS headers verified between FastAPI and frontend
- [ ] JWT/auth flow tested end-to-end
- [ ] Build script copies `dist/` to `frontend/static/`

---

## Support & Debugging

### Vite Proxy Not Working?
- Check that FastAPI is running on `http://localhost:8080`
- Verify `server.proxy['/api'].target` in `vite.config.ts`
- Look for CORS errors in browser console (FastAPI CORS middleware should handle it)

### Tailwind Classes Not Showing?
- Ensure `src/index.css` is imported in `src/main.tsx`
- Check that `tailwind.config.ts` includes your template files in `content`
- Run `npx tailwindcss -i src/index.css -o dist/output.css` to verify

### React Query Cache Not Updating?
- After mutations, manually invalidate queries: `queryClient.invalidateQueries({ queryKey: ['jobs'] })`
- Use React Query DevTools (browser tab) to inspect cache state
- Ensure `queryKey` includes all variables that affect the query

### shadcn/ui Components Not Styling?
- Check that Tailwind CSS is properly configured
- Ensure `src/components/ui/button.tsx` (or whichever component) imports styles correctly
- Components expect certain CSS variables (e.g., `--primary`); add them to `@theme` in `src/index.css`

---

## Resources

- **React 19 Docs:** https://react.dev
- **Vite Documentation:** https://vite.dev
- **React Router Guide:** https://reactrouter.com
- **Tailwind CSS v4:** https://tailwindcss.com/blog/tailwindcss-v4
- **TanStack Query:** https://tanstack.com/query/latest
- **shadcn/ui:** https://ui.shadcn.com

---

**Researched by:** CR8 Research Assistant (Haiku, March 2026)
**Re-verify if:** React/Vite/React Router/Tailwind have major version bumps, or 6+ months pass
