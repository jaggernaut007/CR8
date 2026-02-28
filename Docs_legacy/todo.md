# Todo

## Done

1. ~~Let the agent create pdf/ ppt / video scripts which are related to each other. The pdf is the ground truth and the ppt and video script are based on the pdf.~~
   - **Implemented**: Chained generation flow — PDF is always generated first as ground truth, PPT is structured around PDF chapters (enriched with research/gap data), video script is synced to PPT slides (one section per slide, content drawn from PDF + research).

2. ~~The agent can also create a video script that is based on the ppt.~~
   - **Implemented**: `SCRIPT_FROM_SLIDES` prompt generates a slide-synced script with `[SLIDE N: title]` sections. Script structure follows PPT slides exactly, script content draws from PDF modules + research data.

3. ~~The video script and the ppt is shared to the api, which creates the video.~~
   - **Implemented**: When video format is selected, the slide-synced script is passed to HeyGen API. UI enforces dependency chain (checking Video auto-checks Script and PPT).

4. ~~Optimize pipeline speed and token efficiency with multi-model routing~~
   - **Implemented**: 3-tier model system (nano/mini/premium), severity-based routing,
     filtered context per script, parallel PDF+PPT, split PPT structuring, ChromaDB caching,
     map-reduce summarization, module validation, hook variety enforcement, richer PDF rendering.

## Upcoming

5. Improve image/graphic generation for PPT slides (AI-generated diagrams, charts from data)
6. Add template support for PPT (custom .pptx templates for branding)
7. Multi-file batch processing with combined gap analysis across all documents
