# Research: shadcn/ui Components and TanStack Query for CR8 Frontend

**Date researched:** 2026-03-09
**Library versions:** shadcn/ui (CLI-based, no npm version), @tanstack/react-query >= 5.90.21
**Researched by:** CR8 Research Assistant (Haiku)
**Status:** Current

---

## Question Being Answered

How do we use shadcn/ui to add pre-built, accessible UI components to our React 19 + Tailwind v4 SPA, and how do we use TanStack Query (React Query) for server-state management, caching, and automatic loading/error handling for API calls to FastAPI?

## Sources Consulted

| Source | URL | Date accessed |
|--------|-----|---------------|
| shadcn/ui docs | https://ui.shadcn.com/docs | 2026-03-09 |
| shadcn/ui CLI guide | https://ui.shadcn.com/docs/cli | 2026-03-09 |
| shadcn/ui Tailwind v4 compatibility | https://ui.shadcn.com/docs/tailwind-v4 | 2026-03-09 |
| TanStack Query documentation | https://tanstack.com/query/latest | 2026-03-09 |
| TanStack Query useQuery | https://tanstack.com/query/latest/docs/framework/react/reference/useQuery | 2026-03-09 |
| TanStack Query useMutation | https://tanstack.com/query/latest/docs/framework/react/reference/useMutation | 2026-03-09 |
| @tanstack/react-query npm | https://www.npmjs.com/package/@tanstack/react-query | 2026-03-09 |

---

## What We Found

### Part 1: shadcn/ui Components

#### What is shadcn/ui?

shadcn/ui is **not an npm package**. Instead, it's a CLI tool that copies pre-built, unstyled component source code into your project (`src/components/ui/`). This approach gives you:

- Full control over component implementation (no black-box dependencies)
- Easy customization (just edit the copied component file)
- Zero runtime overhead (components are just React + Tailwind)
- Type-safe components (all TypeScript)
- Tailwind v4 compatible (new components ship with v4 styles)

#### Installation & Setup

```bash
# 1. Initialize shadcn/ui in your React project
npx shadcn-ui@latest init

# 2. This creates:
#    - src/components/ui/ (component library)
#    - components.json (shadcn config)
#    - Copies necessary utilities (cn() helper)

# 3. Install individual components as needed
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
npx shadcn-ui@latest add input
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add tabs
npx shadcn-ui@latest add form
npx shadcn-ui@latest add alert
npx shadcn-ui@latest add dropdown-menu
npx shadcn-ui@latest add select
npx shadcn-ui@latest add toast
```

#### Key Components for CR8 Frontend

**Core UI Components:**
- `button` — CTA buttons with variants (primary, secondary, outline, ghost)
- `card` — containers with header/content/footer layout
- `input` — text inputs with validation styling
- `label` — accessible form labels
- `select` — dropdown selects
- `checkbox` — checkboxes with custom styling
- `radio-group` — radio button groups
- `textarea` — multi-line text input

**Layout & Structure:**
- `tabs` — tabbed content switcher
- `dialog` — modal dialogs (job details, filters, etc.)
- `dropdown-menu` — context menus and action buttons
- `sheet` — slide-out panels (often used for mobile navigation)
- `breadcrumb` — navigation breadcrumbs

**Data Display:**
- `table` — data tables with sortable columns
- `pagination` — page navigation controls
- `badge` — labels and status indicators
- `progress` — progress bars

**Feedback:**
- `toast` — notifications and alerts
- `alert` — alert containers
- `tooltip` — hover/focus tooltips
- `popover` — floating content panels

**Forms (Advanced):**
- `form` — Form component (uses React Hook Form under the hood)
- `calendar` — date picker
- `date-picker` — date/time selection
- `combobox` — searchable dropdown

#### shadcn/ui + React 19 Compatibility

All shadcn/ui components are updated for React 19:
- Forward refs removed (React 19 doesn't require them for all cases)
- New hooks patterns supported (useActionState, useOptimistic)
- No PropTypes (React 19 deprecated them)
- Full TypeScript support with strict mode

#### Example: Using shadcn/ui Button Component

```typescript
import { Button } from "@/components/ui/button"

export function JobCard({ jobId, onDelete }: { jobId: string; onDelete: () => void }) {
  return (
    <div className="flex gap-2">
      <Button variant="default">View</Button>
      <Button variant="outline">Edit</Button>
      <Button
        variant="destructive"
        onClick={onDelete}
      >
        Delete
      </Button>
    </div>
  )
}
```

**Button variants available:**
- `default` — primary button (blue background)
- `secondary` — secondary button (gray background)
- `outline` — outlined button (border only)
- `ghost` — text-only button (no background)
- `link` — link-styled button
- `destructive` — danger button (red)

#### Example: Using shadcn/ui Card + Form

```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export function JobForm() {
  const [title, setTitle] = React.useState("")

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create New Job</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <Label htmlFor="title">Job Title</Label>
            <Input
              id="title"
              placeholder="Enter job title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <Button onClick={() => console.log("Submit", title)}>
            Create Job
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
```

#### Customizing shadcn/ui Components

Since components are copied into your project, you can customize them:

```typescript
// src/components/ui/button.tsx (already copied)
// You can modify the styling directly:

const buttonVariants = cva(
  "inline-flex items-center justify-center font-medium rounded-lg transition-colors cursor-pointer",
  {
    variants: {
      variant: {
        default: "bg-primary text-white hover:bg-primary-dark",
        // ... other variants
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 px-3 text-sm",
        lg: "h-11 px-8 text-lg",
      },
    },
  }
)

// Add new variant:
export const buttonVariants = cva(
  // ... (existing)
  {
    variants: {
      variant: {
        // ... existing
        "gradient": "bg-gradient-to-r from-primary to-accent text-white hover:shadow-lg",
      },
    },
  }
)
```

### Part 2: TanStack Query for Data Fetching

#### What is TanStack Query?

TanStack Query (formerly React Query) is a server-state management library that handles:
- Fetching data from APIs
- Automatic caching of responses
- Refetching on window focus or interval
- Loading/error state management
- Query invalidation and mutations

**Why use it instead of `useEffect` + `useState`?**
- Reduces boilerplate (loading/error handling is automatic)
- Intelligent caching (avoids duplicate requests)
- Automatic refetching (keeps data fresh)
- DevTools for debugging cache state
- Works great with TanStack Router and server frameworks

#### Basic Setup (in React main.tsx)

```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

const queryClient = new QueryClient()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  </React.StrictMode>,
)
```

#### Using useQuery for GET Requests

```typescript
import { useQuery } from '@tanstack/react-query'

// Define a custom hook for fetching jobs
export function useJobs(filters?: { status?: string }) {
  return useQuery({
    queryKey: ['jobs', filters], // Cache key includes filters
    queryFn: async () => {
      const params = new URLSearchParams(filters)
      const response = await fetch(`/api/jobs?${params}`)
      if (!response.ok) throw new Error('Failed to fetch jobs')
      return response.json()
    },
    staleTime: 1000 * 60 * 5, // 5 minutes before refetch
    gcTime: 1000 * 60 * 10, // 10 minutes cache lifetime
    retry: 1,
    enabled: true, // Can disable query conditionally
  })
}

// Use in component
export function JobsList() {
  const { data: jobs, isLoading, error } = useJobs()

  if (isLoading) return <div>Loading jobs...</div>
  if (error) return <div>Error: {error.message}</div>

  return (
    <ul>
      {jobs?.map((job) => (
        <li key={job.id}>{job.title}</li>
      ))}
    </ul>
  )
}
```

#### Using useMutation for POST/PATCH/DELETE

```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query'

export function useCreateJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (newJob: { title: string; description: string }) => {
      const response = await fetch('/api/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newJob),
      })
      if (!response.ok) throw new Error('Failed to create job')
      return response.json()
    },
    onSuccess: () => {
      // Invalidate the jobs list to trigger a refetch
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
    onError: (error) => {
      console.error('Error creating job:', error)
    },
  })
}

// Use in component with shadcn/ui form
export function CreateJobDialog() {
  const [open, setOpen] = React.useState(false)
  const createJob = useCreateJob()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget as HTMLFormElement)
    await createJob.mutateAsync({
      title: formData.get('title') as string,
      description: formData.get('description') as string,
    })
    setOpen(false)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>Create Job</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New Job</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input name="title" placeholder="Job title" required />
          <textarea name="description" placeholder="Description" required />
          <Button type="submit" disabled={createJob.isPending}>
            {createJob.isPending ? 'Creating...' : 'Create'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}
```

#### Configuration & Best Practices

**Global QueryClient defaults:**
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 min before refetch
      gcTime: 1000 * 60 * 10, // 10 min cache lifetime
      retry: 1,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
      refetchOnMount: true,
    },
    mutations: {
      retry: 1,
    },
  },
})
```

**queryKey conventions:**
```typescript
// DO: Include all variables that affect the query
const { data } = useQuery({
  queryKey: ['jobs', { status: 'active', page: 2 }],
  queryFn: ({ queryKey }) => {
    const [, filters] = queryKey
    return fetchJobs(filters)
  },
})

// DON'T: Leave out filter variables
// const { data } = useQuery({
//   queryKey: ['jobs'], // Will not track page changes!
// })
```

**Mutation cache invalidation:**
```typescript
// After creating a job, refetch the list
const createJob = useMutation({
  mutationFn: createJobAPI,
  onSuccess: (newJob) => {
    // Option 1: Invalidate the entire list
    queryClient.invalidateQueries({ queryKey: ['jobs'] })

    // Option 2: Update the cache directly (faster)
    queryClient.setQueryData(['jobs'], (old: Job[]) => [...(old || []), newJob])

    // Option 3: Invalidate only relevant queries
    queryClient.invalidateQueries({
      queryKey: ['jobs'],
      exact: false, // Also invalidates ['jobs', {...filters}]
    })
  },
})
```

#### TanStack Query Devtools

Install separately for debugging:
```bash
npm i @tanstack/react-query-devtools
```

Access at bottom-right corner of your app (in development) to inspect:
- Query cache state
- Query lifecycle (fetching, stale, inactive)
- Query history
- Manual refetch/invalidation

---

## What We Ruled Out (and Why)

| Approach | Why Rejected |
|----------|-------------|
| Material-UI instead of shadcn/ui | Material-UI is heavier (~100kb), less customizable, and has more opinionated styling. shadcn/ui gives full control. |
| Building UI from scratch | shadcn/ui components are battle-tested, accessible, and save development time. No reason to reimplement buttons and dialogs. |
| Using plain `fetch()` instead of TanStack Query | Query eliminates boilerplate (loading/error states, retries, caching). Much better DX for complex data flows. |
| Zustand/Redux instead of TanStack Query | Zustand is for client state (theme, UI state). Query is specifically for server state (API data). Use both if needed. |
| SWR instead of TanStack Query | Both are good, but Query has more features (mutations, devtools, invalidation patterns). Choose one — we chose Query. |
| Directly importing shadcn components from npm | shadcn/ui components ARE NOT on npm. You must use the CLI to copy them into your project. |

---

## Known Gotchas / Edge Cases

### shadcn/ui

**1. Components are copied, not imported:**
```bash
# This DOESN'T work (no npm package):
npm i shadcn-ui
import Button from 'shadcn-ui' # ❌

# This WORKS (CLI copies to src/components/ui/):
npx shadcn-ui@latest add button
import { Button } from '@/components/ui/button' # ✓
```

**2. Updating components:**
```bash
# If shadcn/ui releases a new version, re-run add to get updates:
npx shadcn-ui@latest add button --overwrite

# Or use the CLI to check for updates:
npx shadcn-ui@latest update
```

**3. Tailwind config must include shadcn content:**
```typescript
// tailwind.config.ts
export default {
  content: [
    './src/**/*.{js,ts,jsx,tsx}',
    // Make sure this is included!
  ],
}
```

**4. Theming colors:**
shadcn components use CSS variables for theming. The exact variables depend on which components you add. Check `src/components/ui/button.tsx` to see which variables it expects. Common ones: `--primary`, `--secondary`, `--destructive`.

### TanStack Query

**1. queryKey must be an array:**
```typescript
// ✓ Correct
useQuery({ queryKey: ['jobs', { page: 1 }] })

// ❌ Wrong (not an array)
useQuery({ queryKey: 'jobs' as any })
```

**2. Automatic refetch on window focus:**
```typescript
// By default, queries refetch when user returns to tab
// This can spam your API — disable if needed:
useQuery({
  queryFn,
  refetchOnWindowFocus: false,
})
```

**3. Loading state is NOT reset on error:**
```typescript
const { isLoading, error } = useQuery(...)

// If query fails, isLoading is false BUT error is set
// Handle both states:
if (isLoading) return <Spinner />
if (error) return <Error message={error.message} />
return <Success data={data} />
```

**4. Mutations don't auto-refetch:**
```typescript
// After a mutation, queries don't automatically update
// You MUST invalidate or update manually:
useMutation({
  mutationFn: updateJobAPI,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['jobs'] })
  },
})
```

**5. Stale time vs. GC time:**
```typescript
// staleTime = how long before the query is "stale" and eligible for refetch
// gcTime = how long to keep the data in memory after it goes unused

// Example: staleTime=5min, gcTime=10min
// - User visits page, query runs (data fresh)
// - After 5 min, data is stale (will refetch on next use)
// - User leaves for 11 min, data is garbage collected (removed from cache)
// - User returns, query runs again (cache was cleared)
```

---

## Security Assessment

### shadcn/ui

| Check | Result | Notes |
|-------|--------|-------|
| Open CVEs | None | No known vulnerabilities in shadcn/ui (it's component source code, not a binary package). |
| License | MIT | Compatible with CR8. No restrictions. |
| Security concerns | Registry injection risk | Users should verify they're installing from the official shadcn/ui source, not malicious clones. Use only the official CLI. |
| Last update | Active (weekly) | Component libraries are updated regularly for React/Tailwind compatibility. |
| Customization safety | Safe | Since you own the component code, you can audit and modify as needed. |

**Verdict:** **SAFE to use.** shadcn/ui is a popular, well-maintained component library with no known security issues. The fact that components are copied into your project is actually a security advantage (no supply chain risk from binary packages).

### TanStack Query

| Check | Result | Notes |
|-------|--------|-------|
| Open CVEs | Minor (XSS in @tanstack/react-query-next-experimental) | Main `@tanstack/react-query` package has no critical CVEs. The experimental Next.js package (v5.18.0+) has an XSS fix, but we're not using that. |
| License | MIT | Compatible with CR8. |
| Last release | v5.90.21 (Feb 2026) | Actively maintained. New releases every 1-2 weeks. |
| Maintainer count | TanStack (Tanner Linsley + community) | Well-resourced. Industry standard for React query management. |
| Transitive dependencies | ~5 dependencies | All are well-maintained. No heavy dependencies. |
| Known incidents | None | No major security incidents reported. |

**Verdict:** **SAFE to add.** TanStack Query is a mature, production-tested library with no security issues in the core package.

---

## Decision Made

Based on this research, we will:

1. **Use shadcn/ui CLI** to scaffold and add components as needed.
2. **Add core components:** button, card, input, label, dialog, tabs, form, select, table, pagination, badge, toast.
3. **Customize shadcn/ui components** by editing the copied source files in `src/components/ui/`.
4. **Use TanStack Query v5.90.21+** for all API data fetching and caching.
5. **Define custom hooks** (`useJobs()`, `useCreateJob()`, etc.) wrapping `useQuery`/`useMutation` for consistent error handling.
6. **Invalidate queries** after mutations to keep data in sync with the backend.
7. **Use React Query Devtools** in development for debugging query cache state.
8. **Configure global QueryClient defaults** for staleTime, gcTime, and retry behavior.

---

## Files This Affects

- `src/components/ui/*` — shadcn/ui component library (auto-generated by CLI)
- `src/hooks/queries/*` — custom hooks wrapping useQuery/useMutation (create these per feature)
- `src/main.tsx` — QueryClientProvider and Devtools setup
- `frontend/package.json` — add `@tanstack/react-query`, `@tanstack/react-query-devtools`
- `components.json` — auto-generated by shadcn/ui init

---

*If this research is more than 6 months old or shadcn/ui/TanStack Query have major updates, re-verify before implementing.*
