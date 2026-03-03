# Research: [Topic / Library / API Name]
<!-- Implementation research note.
     Place in: docs/research/[topic].md
     The agent reads these BEFORE implementing anything involving external libraries or APIs.
     This prevents hallucinated API calls and outdated method usage. -->

**Date researched:** [YYYY-MM-DD]
**Library version:** [exact version, e.g. stripe@14.2.0]
**Researched by:** [Agent session / human name]
**Status:** [Current | Needs update | Superseded]

---

## Question Being Answered

What specific implementation question motivated this research?
> How do we [do X] using [library Y] in the context of [our project]?

## Sources Consulted

| Source | URL | Date accessed |
|--------|-----|---------------|
| Official docs | [url] | [date] |
| Changelog / migration guide | [url] | [date] |
| GitHub issues (if relevant) | [url] | [date] |

> ⚠️ **Agent note:** Always use official documentation over blog posts for implementation decisions. Pin the exact version.

## What We Found

### The Correct Approach
```[language]
// Working code example with this exact library version
// Include imports, initialization, and the core pattern
```

### Key API Methods / Concepts
| Method / Concept | Purpose | Notes / Gotchas |
|-----------------|---------|----------------|
| `[method()]` | [what it does] | [any version-specific behaviour] |

### Configuration Required
```[language/yaml]
// Any environment variables, config files, or setup steps required
```

## What We Ruled Out (and Why)

| Approach | Why Rejected |
|----------|-------------|
| [Alternative A] | [Reason — e.g. deprecated in v14, doesn't support our use case] |
| [Alternative B] | [Reason] |

## Known Gotchas / Edge Cases

- [Behaviour that differs from what you'd expect]
- [Version-specific quirk]
- [Error that's easy to hit and how to avoid it]

## Decision Made

Based on this research, we will:
> [Concrete implementation decision]

## Files This Affects

- `[file path]` — [how it's affected]
- `[file path]` — [how it's affected]

---
*If this research is more than 6 months old or the library has had a major version bump, re-verify before implementing.*
