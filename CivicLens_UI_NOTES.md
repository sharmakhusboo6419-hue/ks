# CivicLens UI update

The Streamlit app now has a dark civic-tech visual system, a four-step workflow, mode selection, sidebar settings, image preview, structured analysis cards, urgency/category badges, key-detail tiles, next-step checklist, download summary, copy-friendly summary output, loading status, and friendly empty/error states.

## Model integration

- The existing OpenAI-compatible POST flow remains in `\.opencode/app.py`.
- Set `GEMMA_4_ENDPOINT` to the deployed `/v1/chat/completions` URL. It defaults to `http://localhost:8000/v1/chat/completions` for the local mock server.
- The UI prefers the existing `display_civic_data` tool-call response and maps `action_steps` to the checklist.
- Plain-text model responses are supported with a fallback parser. For richer cards, return `category`, `title`, `summary`, `action_steps`, `key_details`, and `urgency` from the tool call.
- The download is intentionally plain text; a PDF export would require an additional PDF dependency or a separate document service.

Run locally with:

```bash
.venv/bin/streamlit run .opencode/app.py --server.port 8501
```
