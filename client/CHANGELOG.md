# CivicLens — Changelog (this update)

## New features
1. **Multilingual output** — sidebar language selector: English, Hindi, Kannada, Tamil, Telugu, Marathi. The model writes summary, key details, dates, actions, glossary, and forms in the chosen language (language is part of the cache key, so switching language produces a fresh, cached analysis).
2. **Key Dates + calendar export** — "Key Dates" tab lists deadlines (with days-remaining when ISO-parsed) and an "Add to calendar" button downloads an .ics file (one event per date, reminder 1 day before).
3. **Chat with the document** — Chat tab with st.chat_input/st.chat_message. The uploaded image and the first analysis are kept in context; 3 suggested starter questions are generated from the analysis (no extra model call).
4. **Simplify mode** — "Explain in simple words" toggle in the sidebar. Prompts the model for a 6th-grade-level summary and puts unavoidable jargon into the glossary card.
5. **Civic issue report generator** — for photo uploads, the Report tab auto-drafts a complaint (title, issue type, severity, editable location — plus a global optional address field — suggested department, urgency). Departments are mapped from issue keywords (pothole → Roads, garbage → Solid Waste, streetlight → Electricity, water → Water Board, etc.), with a general fallback.
6. **Letter/email drafter** — "Draft complaint letter" produces a formal letter from the report, editable in a text area, with Download .txt, Download .pdf, and Copy (pyperclip) buttons.
7. **Form helper** — for municipal forms, the Actions tab lists each form field with a plain-language explanation and a tickable checklist of documents to bring.
8. **Trust features** — per-field confidence scores from the model; anything below 0.6 gets an amber "please verify" badge and a confidence pill row under the summary card. Persistent AI-generated-content disclaimer in the footer and sidebar.
9. **History & export** — in-session history in the sidebar (time, title, category, urgency, summary snippet); "Export report as PDF" combines summary, key details, key dates, actions, glossary, documents, and the drafted letter, with a .txt fallback if PDF fails.
10. **Text-to-speech** — "Listen to summary" button uses gTTS in the selected language; audio is cached in-session and played via st.audio.

## Structure
- `client/prompts.py` — prompt builders, language table, payload/tool schema, starter questions.
- `client/parsers.py` — response normalization + validation + safe fallback (plain-text model responses still render), authority mapping.
- `client/exporters.py` — .ics builder, complaint-letter drafter, PDF/text report builder (fpdf2, auto-detects a system Unicode font).
- `client/inference.py` — model calls: `analyze_artifact` (st.cache_data) and `chat_turn` (uncached), plus timeout mapping.
- `client/app.py` — UI, tabs (Summary | Key Dates | Actions | Chat | Report), sidebar, session state.
- Existing inference logic (multimodal message + display_civic_data tool call) is unchanged in shape — only moved into `inference.py`.

## requirements.txt (new packages)
- gtts>=2.4 — text-to-speech
- fpdf2>=2.7 — PDF export
- pyperclip>=1.8 — copy-letter button

## What you need to configure / know
- `GEMMA_4_ENDPOINT` (env var, default `http://localhost:8000/v1/chat/completions`) — point it at your AWS-hosted Gemma 4.
- **Indic PDFs**: fpdf2 uses the first system font with broad Unicode coverage it can find (`NotoSans-Regular.ttf` etc.). For best Hindi/Tamil/Kannada/Telugu/Marathi rendering, install e.g. `noto-fonts` (Devanagari/Tamil/Kannada/Telugu). Latin reports work with any font.
- **TTS** needs internet access (gTTS calls Google's service).
- **Copy button** needs a clipboard backend on Linux (`xclip`/`wl-clipboard`); otherwise you get an inline hint and can still download.
- The model must support tool calling with the `confidence` object; if it returns plain text, the app falls back gracefully (empty dates/actions sections).
