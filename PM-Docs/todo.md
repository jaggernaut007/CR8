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

## Upcoming

5. Improve image/graphic generation for PPT slides (AI-generated diagrams, charts from data)
6. Add template support for PPT (custom .pptx templates for branding)
7. Multi-file batch processing with combined gap analysis across all documents
