# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.4.x   | Yes                |
| 0.3.x   | Best-effort        |
| < 0.3   | No                 |

## Reporting a Vulnerability

If you discover a security vulnerability in CR8, please report it responsibly:

1. **Do not** open a public GitHub issue for security vulnerabilities.
2. Email the maintainers with a description of the issue, steps to reproduce, and any relevant logs or screenshots.
3. You will receive an acknowledgement within 48 hours.
4. A fix will be developed and released within 90 days of the report (coordinated disclosure).

## Security Best Practices for Deployment

- **API Keys**: Local development reads keys from `.env` (never committed). Production keys live in **Doppler** and are injected as environment variables at deploy time by `deploy.sh` (run via `doppler run`). Never commit `.env` files.
- **LangSmith Tracing**: Tracing is opt-in (disabled by default). Set `LANGCHAIN_API_KEY` and `LANGCHAIN_TRACING_V2=true` only if you want trace data sent to LangSmith.
- **Temp Files**: The video pipeline uses `tempfile.TemporaryDirectory()` for all intermediate files, ensuring cleanup on completion or failure.
- **Subprocess Calls**: All external process calls (e.g., LibreOffice for PPTX conversion) use explicit argument lists with timeouts — no `shell=True`.
- **File Uploads**: Uploaded files are validated by extension and processed in isolated directories.
