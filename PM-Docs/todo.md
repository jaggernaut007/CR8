# Todo
1) Create a quiz based wbsite for the content created by the agent. The quiz should be based on the content of the pdf, ppt and video script. The quiz should be interactive and engaging for the users. The quiz should be able to test the users' understanding of the content record the data points in the database. Finally an admin dashabord should be able to visualise the data points and the performance of the users in the quiz. The quiz should be able to provide feedback to the users based on their performance in the quiz.
2) Create a feedback loop for the agent to improve its content creation based on the performance of the users in the quiz. The agent should be able to analyze the data points collected from the quiz and use that data to improve its content creation process. The agent should be able to identify areas where users are struggling and focus on improving those areas in future content creation.
3) The quiz content should be able to be customized by the admin. The admin should be able to add or remove questions from the quiz, as well as customize the feedback provided to users based on their performance. The admin should also be able to set different difficulty levels for the quiz and track the performance of users at each level.
4) The quiz itself should be able to show wrong answers and right answers in red green after it is completed. The quiz is not able to be retaken.
5) We must be able to create a video of the slides created by the agent, a voice based video with the slides should be created.Use opensource technologies to create this video. Think open-tts and ffmpeg for this. The video should be able to be embedded on websites. The video should also be able to be downloaded by users.
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

5. ~~We must be able to create a video of the slides created by the agent, a voice based video with the slides should be created. Use opensource technologies to create this video.~~
   - **Implemented (v0.4.0)**: Kokoro TTS local video pipeline — open-source, zero-cost. `VIDEO_PROVIDER=kokoro` chains: script parsing → Kokoro TTS (82M model, GPU-aware) → slide export (PyMuPDF/LibreOffice) → ffmpeg composition → MP4. Two-phase pipeline: sequential TTS → parallel ffmpeg. Hardware H.264 encoding (VideoToolbox/NVENC/QSV/AMF). GPU service offload via Cloud Run NVIDIA L4 + GCS data transfer. Videos are embeddable and downloadable. 507 tests passing.


## Upcoming

6. ~~Create a quiz-based website for the content created by the agent~~ **DONE (v0.5.4)**
7. Create a feedback loop for the agent to improve content based on quiz performance (→ v0.6)
8. Admin quiz customisation — add/remove questions, difficulty levels, custom feedback (→ v0.6)
9. ~~Quiz shows wrong/right answers in red/green after completion, one-attempt-only~~ **DONE (v0.5.4)**
10. Improve image/graphic generation for PPT slides (AI-generated diagrams, charts from data)
11. Add template support for PPT (custom .pptx templates for branding)
12. Multi-file batch processing with combined gap analysis across all documents
13. Citation/references for ppt in the same slide, pdf in the end.
14. ruff upgrade and codebase linting
15. github actions
16. caching for AI agents/vector databases and software dependencies (e.g. model files, ffmpeg binaries) to speed up setup and execution
17. user authentication and role-based access control for admin dashboard and quiz management and also login through google.
18. UI: Everystage has an eta and overall eta is present as well. We can also show the eta for each stage. This will help the users to understand how much time is left for the completion of the task.
19. description on what its doing during progress. high level description of what the agent is doing during the progress. This will help the users to understand the process jsut be sure that its working well.
20. Add estimated time for quiz generation and video generation. This will help the users to understand how much time is left for the completion of the task.