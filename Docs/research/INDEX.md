# Research Index

Implementation research notes for the CR8 pipeline.
Read the relevant note before implementing any feature that uses an external library or API.

## How to Use

1. Check this index for existing notes
2. If a current note exists, read it before implementing
3. If no note exists (or it's outdated), create one:
   - Copy `docs/research/RESEARCH-TEMPLATE.md` → `docs/research/[library].md`
   - Research the official docs for the exact version in `pyproject.toml`
   - Add a row to this index when done

## Research Notes

| Topic | File | Version | Date | Status |
|-------|------|---------|------|--------|
| *(none yet — add entries here as research notes are created)* | | | | |

## Priority Research Needed

These libraries are used in CR8 but have no research notes yet:

| Library | Version in pyproject.toml | Why it matters |
|---------|--------------------------|----------------|
| LangGraph | `>=0.2` | Core pipeline orchestration — API changes frequently |
| OpenAI SDK | (via langchain-openai `>=0.3`) | Model names, streaming API, tool calling |
| ChromaDB | `>=0.5` | Collection management, embedding functions, query API |
| Tavily | `>=0.5` | Search parameters, result filtering, rate limits |
| HeyGen | REST API (no Python SDK) | Avatar video generation — undocumented edge cases |
| fpdf2 | `>=2.8` | Multi-column PDF layout — complex API |
| python-pptx | `>=1.0` | Slide master styles, shape positioning |

## Notes That Are Outdated

Check this section when a library has a major version bump:
- *(none flagged yet)*
