import base64
import datetime as dt
import html
import json
import os
import re
import sys

import requests
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exporters import build_ics, build_pdf, build_text, draft_letter
from inference import GEMMA_4_ENDPOINT, ModelTimeout, analyze_artifact, chat_turn
from parsers import issue_severity, suggest_authority
from prompts import LANGUAGES, MODES, suggested_questions
from voice_component import voice_input

st.set_page_config(
    page_title="CivicLens | Clear civic action",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

GEMMA_4_ENDPOINT = os.environ.get("GEMMA_4_ENDPOINT", GEMMA_4_ENDPOINT)
SUPPORTED_TYPES = ["jpg", "jpeg", "png"]
LOW_CONFIDENCE = 0.6

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

:root {
    --ink: #f3f8f7;
    --muted: #9cb3b4;
    --teal: #55d6c2;
    --blue: #6ea8ff;
    --line: rgba(154, 198, 199, 0.18);
    --panel: rgba(24, 42, 48, 0.78);
    --panel-strong: #182b31;
}

.stApp {
    background: #0b171d;
    background-image: radial-gradient(circle at 85% 0%, rgba(50, 116, 130, .22), transparent 30%), linear-gradient(145deg, #0b171d 0%, #10242b 58%, #0b171d 100%);
    color: var(--ink);
    font-family: 'DM Sans', sans-serif;
}
.block-container { max-width: 1240px; padding: 2.6rem 4rem 2rem; }
h1, h2, h3, .hero-title { font-family: 'Space Grotesk', sans-serif !important; letter-spacing: -0.02em; }
h1 { font-size: clamp(2.2rem, 4.5vw, 4.2rem) !important; line-height: 1.05 !important; }
h2 { font-size: 1.4rem !important; }
p, label, .stCaption { color: var(--muted); }
.hero { padding: 0 0 2rem; }
.eyebrow { color: var(--teal); font-size: .76rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; }
.hero-title { background: linear-gradient(100deg, #f3f8f7 15%, #68dec9 60%, #77aaff 100%); -webkit-background-clip: text; background-clip: text; color: transparent; margin: .35rem 0 .8rem; }
.hero-copy { font-size: 1.1rem; line-height: 1.6; max-width: 680px; }
.workflow { display: grid; grid-template-columns: repeat(4, 1fr); gap: .65rem; margin: .5rem 0 1.8rem; }
.workflow-step { border-top: 1px solid var(--line); padding: .8rem .2rem 0; color: var(--muted); font-size: .85rem; }
.workflow-step strong { display: block; color: var(--ink); font-size: .95rem; margin-bottom: .2rem; }
.workflow-step span { color: var(--teal); font-weight: 700; margin-right: .35rem; }
.section-kicker { color: var(--muted); font-size: .77rem; letter-spacing: .12em; text-transform: uppercase; font-weight: 700; margin-bottom: .8rem; }
.upload-card, .result-card { background: var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: 1.35rem; box-shadow: 0 18px 60px rgba(0,0,0,.16); }
.upload-icon { color: var(--teal); font-size: 2rem; margin-bottom: .6rem; }
.privacy { font-size: .78rem; color: #87a0a2; margin-top: .6rem; }
.detail-pill { display: inline-block; border: 1px solid var(--line); border-radius: 99px; padding: .22rem .58rem; font-size: .72rem; color: var(--muted); }
.metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: .65rem; margin: .9rem 0 1.1rem; }
.metric { background: rgba(11, 23, 29, .5); border: 1px solid var(--line); border-radius: 12px; padding: .8rem; min-height: 76px; }
.metric-label { color: var(--muted); font-size: .72rem; text-transform: uppercase; letter-spacing: .08em; }
.metric-value { color: var(--ink); font-size: .95rem; font-weight: 600; margin-top: .3rem; overflow-wrap: anywhere; }
.badge { display: inline-block; border-radius: 99px; padding: .32rem .7rem; font-size: .73rem; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; }
.badge-category { color: #bceee7; background: rgba(85,214,194,.13); border: 1px solid rgba(85,214,194,.28); }
.badge-low { color: #a9d8ff; background: rgba(110,168,255,.14); }
.badge-medium { color: #ffe2a2; background: rgba(240,182,75,.15); }
.badge-high, .badge-critical { color: #ffb1a8; background: rgba(231,103,93,.16); }
.badge-verify { color: #ffd9a8; background: rgba(210,153,34,.18); }
.result-title { margin: .75rem 0 .85rem; }
.result-card h4 { color: var(--ink); margin: 1.15rem 0 .55rem; font-family: 'Space Grotesk', sans-serif; }
.check-item { border-bottom: 1px solid var(--line); padding: .75rem 0 .75rem 1.7rem; position: relative; color: #c9d8d7; }
.check-item:before { content: '✓'; position: absolute; left: 0; top: .72rem; color: var(--teal); font-weight: 700; }
.empty-state { text-align: center; padding: 2.8rem 1rem; border: 1px dashed rgba(154,198,199,.28); border-radius: 18px; color: var(--muted); }
.empty-state strong { display: block; color: var(--ink); font-family: 'Space Grotesk', sans-serif; font-size: 1.1rem; margin-bottom: .35rem; }
.stButton > button, .stDownloadButton > button { border-radius: 10px; border: 1px solid rgba(85,214,194,.5); background: linear-gradient(110deg, #2cae9e, #327ac6); color: white; font-weight: 700; min-height: 2.7rem; transition: transform .18s ease, box-shadow .18s ease; }
.stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(50,160,175,.25); border-color: var(--teal); }
[data-testid="stSidebar"] { background: #0d1c22; border-right: 1px solid var(--line); }
[data-testid="stSidebar"] h2 { font-size: 1.1rem !important; }
footer, #MainMenu { visibility: hidden; }
@media (max-width: 760px) { .block-container { padding: 2rem 1.1rem; } .workflow { grid-template-columns: repeat(2, 1fr); } .metric-grid { grid-template-columns: 1fr; } }
</style>
""",
    unsafe_allow_html=True,
)

DISCLAIMER = "⚠️ AI-generated guidance. Always verify dates, fees, and requirements with the official office or website before acting."


# ---------- session state ----------

for key, default in {
    "analysis": None,
    "chat": [],
    "history": [],
    "report": None,
    "letter": None,
    "tts_cache": {},
}.items():
    st.session_state.setdefault(key, default)


# ---------- helpers ----------

def conf_badge(field: str, data: dict) -> str:
    """'please verify' badge when the model is unsure about a field."""
    score = (data.get("confidence") or {}).get(field)
    try:
        score = float(score)
    except (TypeError, ValueError):
        return ""
    if score < LOW_CONFIDENCE:
        return ' <span class="badge badge-verify">please verify</span>'
    return ""


def render_confidence(data: dict) -> None:
    conf = data.get("confidence") or {}
    if not conf:
        return
    st.markdown('<div class="section-kicker">Confidence per field</div>', unsafe_allow_html=True)
    pills = []
    for field, score in conf.items():
        try:
            score = float(score)
        except (TypeError, ValueError):
            continue
        low = score < LOW_CONFIDENCE
        pills.append(
            f'<span class="detail-pill" style="color:{"#ffd9a8" if low else "#bceee7"}">'
            f'{html.escape(str(field))}: {score:.0%}{" ⚠ verify" if low else ""}</span>'
        )
    if pills:
        st.markdown(" ".join(pills), unsafe_allow_html=True)


def make_report(analysis: dict, address: str) -> dict:
    """Civic issue complaint report from the analysis."""
    category = analysis.get("category", "Civic issue")
    return {
        "issue_type": category,
        "severity": issue_severity(analysis.get("urgency", "Medium")),
        "urgency": (analysis.get("urgency") or "Medium").title(),
        "title": analysis.get("title") or f"{category} complaint",
        "description": analysis.get("summary", ""),
        "location": address or "[enter location]",
        "authority": analysis.get("suggested_authority") or suggest_authority(category),
    }


# ---------- sidebar ----------

with st.sidebar:
    st.markdown("## CivicLens")
    st.caption("Settings for this analysis")
    language = st.selectbox("Output language", list(LANGUAGES), index=0)
    detail_level = st.select_slider("Detail level", options=["Essential", "Balanced", "Thorough"], value="Balanced")
    simplify = st.toggle(
        "Explain in simple words", value=False,
        help="Rewrites the summary at a 6th-grade reading level and defines jargon in a glossary.")
    st.session_state.language = language

    st.divider()
    st.markdown("### How it works")
    st.markdown("**1. Upload** a notice, form, or issue photo.\n\n**2. Analyze** with Gemma 4.\n\n"
                "**3. Understand** in plain language.\n\n**4. Act** with letters, dates, and reports.")
    st.divider()

    st.markdown("### Session history")
    if st.session_state.history:
        for item in reversed(st.session_state.history):
            with st.expander(f"{item['ts']} · {item['title'][:38]}"):
                st.caption(f"{item['category']} · {item['urgency']}")
                summary = item["summary"]
                st.write(summary[:220] + ("…" if len(summary) > 220 else ""))
        if st.button("Clear history"):
            st.session_state.history = []
            st.rerun()
    else:
        st.caption("No analyses yet in this session.")
    st.divider()
    st.caption("AI-generated guidance should be verified with official sources.")


# ---------- hero + upload ----------

st.markdown('<div class="hero"><div class="eyebrow">🏛️ Civic clarity, one upload away</div><h1 class="hero-title">Make civic information easier to act on.</h1><p class="hero-copy">Turn confusing civic documents and street-level issues into clear, actionable insight — with dates, letters, and reminders.</p></div>', unsafe_allow_html=True)
st.markdown('<div class="workflow"><div class="workflow-step"><strong><span>01</span> Upload</strong>Share a civic artifact</div><div class="workflow-step"><strong><span>02</span> Analyze</strong>Read the visual context</div><div class="workflow-step"><strong>03 <span style="color: var(--teal)">Understand</span></strong>Plain-language guidance</div><div class="workflow-step"><strong><span>04</span> Act</strong>Letters, dates, and reports</div></div>', unsafe_allow_html=True)

mode = st.radio("What are you sharing?", list(MODES), horizontal=True, label_visibility="collapsed")
st.markdown('<div class="section-kicker">01 / Upload</div>', unsafe_allow_html=True)
st.markdown('<div class="upload-card"><div class="upload-icon">＋</div><h3>Drop a notice, form, or photo here</h3><p>Choose a clear image so CivicLens can read the details that matter.</p><div><span class="detail-pill">JPG</span> <span class="detail-pill">JPEG</span> <span class="detail-pill">PNG</span></div><div class="privacy">Privacy note: your image is sent only to the configured analysis endpoint.</div></div>', unsafe_allow_html=True)
uploaded_file = st.file_uploader("Upload civic artifact", type=SUPPORTED_TYPES, label_visibility="collapsed")

if uploaded_file is None:
    st.markdown('<div class="empty-state"><strong>Your analysis will appear here</strong>Upload an image above to turn the next civic question into a clear plan.</div>', unsafe_allow_html=True)
    st.stop()

bytes_data = uploaded_file.getvalue()
if not bytes_data:
    st.error("That file appears to be empty. Please upload a valid JPG or PNG image.")
    st.stop()
if len(bytes_data) > 12 * 1024 * 1024:
    st.error("Image is larger than 12 MB. Please upload a smaller photo.")
    st.stop()

image_b64 = base64.b64encode(bytes_data).decode("utf-8")

# Optional voice question (browser speech recognition)
spoken = voice_input() or ""
if spoken:
    st.caption(f'🎤 You asked: “{spoken}”')

# ---------- run analysis (cached on image+mode+language+simplify+voice) ----------

analysis_key = f"{uploaded_file.name}::{len(bytes_data)}::{mode}::{language}::{simplify}::{spoken}"
if st.session_state.analysis is None or st.session_state.get("_analysis_key") != analysis_key:
    st.session_state.chat = []          # new document -> fresh chat
    st.session_state.letter = None
    try:
        with st.status("CivicLens is reading your artifact...", expanded=True) as status:
            st.write("Reading document structure and visual context...")
            st.write("Extracting dates, actions, and key details...")
            st.session_state.analysis = analyze_artifact(
                image_b64, mode, language, simplify, voice_query=spoken)
            st.session_state._analysis_key = analysis_key
            status.update(label="Analysis ready", state="complete", expanded=False)
    except ModelTimeout:
        st.error("The analysis service took too long to respond. Please try again.")
        st.stop()
    except (requests.exceptions.RequestException, KeyError, IndexError, ValueError, json.JSONDecodeError) as error:
        st.error(f"CivicLens could not complete the analysis. Check GEMMA_4_ENDPOINT or start the local mock server. Details: {error}")
        st.stop()

analysis = st.session_state.analysis

# record in session history once per artifact+language
if analysis_key not in st.session_state:
    st.session_state.history.append({
        "ts": dt.datetime.now().strftime("%H:%M"),
        "title": analysis.get("title") or analysis.get("category", "Analysis"),
        "category": analysis.get("category", ""),
        "urgency": analysis.get("urgency", ""),
        "summary": analysis.get("summary", ""),
    })
    st.session_state[analysis_key] = True

address = st.text_input(
    "Optional: address / landmark of the issue or document holder",
    value=st.session_state.get("address", ""),
    key="address",
    placeholder="e.g. 3rd Cross, Jayanagar, Bengaluru",
)

# ---------- tabs ----------

tab_summary, tab_dates, tab_actions, tab_chat, tab_report = st.tabs(
    ["📋 Summary", "📅 Key Dates", "✅ Actions", "💬 Chat", "🧾 Report"])

# ===== Summary tab =====
with tab_summary:
    left, right = st.columns([1.2, 0.8], gap="large")
    with left:
        category = html.escape(str(analysis.get("category", "Community update")))
        urgency = html.escape(str(analysis.get("urgency", "Medium")).title())
        uclass = re.sub(r"[^a-z]", "", urgency.lower()) or "medium"
        title = html.escape(str(analysis.get("title") or "Civic information summary"))
        st.markdown('<div class="section-kicker">02 / Understand</div>', unsafe_allow_html=True)
        st.markdown('<div class="result-card">', unsafe_allow_html=True)
        st.markdown(
            f'<span class="badge badge-category">{category}</span> '
            f'<span class="badge badge-{uclass}">{urgency} urgency</span>'
            f'{conf_badge("summary", analysis)}',
            unsafe_allow_html=True)
        st.markdown(f'<h2 class="result-title">{title}</h2>', unsafe_allow_html=True)
        st.markdown("<h4>In plain language</h4>", unsafe_allow_html=True)
        st.write(analysis.get("summary", ""))
        details = analysis.get("key_details") or {}
        if details:
            st.markdown("<h4>Key details</h4>", unsafe_allow_html=True)
            st.markdown('<div class="metric-grid">', unsafe_allow_html=True)
            for label, value in details.items():
                st.markdown(
                    f'<div class="metric"><div class="metric-label">{html.escape(str(label).replace("_", " "))}{conf_badge(label, analysis)}</div>'
                    f'<div class="metric-value">{html.escape(str(value))}</div></div>',
                    unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        if analysis.get("glossary"):
            st.markdown("<h4>Glossary (simple words)</h4>", unsafe_allow_html=True)
            for term, meaning in analysis["glossary"].items():
                st.markdown(
                    f'<div class="check-item"><strong>{html.escape(str(term))}</strong> — {html.escape(str(meaning))}</div>',
                    unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        render_confidence(analysis)
    with right:
        st.markdown('<div class="section-kicker">Artifact preview</div>', unsafe_allow_html=True)
        st.image(bytes_data, width="stretch")
        st.caption(f"{uploaded_file.name} · {len(bytes_data) / 1024:.0f} KB · {mode}")

        # Text-to-speech
        st.markdown('<div class="section-kicker">Listen</div>', unsafe_allow_html=True)
        if st.button("🔊 Listen to summary", use_container_width=True):
            try:
                from gtts import gTTS
                tts_lang = LANGUAGES[language]
                buf_key = f"tts::{tts_lang}::{hash(analysis.get('summary', ''))}"
                if buf_key not in st.session_state.tts_cache:
                    import io
                    buf = io.BytesIO()
                    gTTS(text=analysis.get("summary", "")[:4500], lang=tts_lang).write_to_fp(buf)
                    st.session_state.tts_cache[buf_key] = buf.getvalue()
                st.audio(st.session_state.tts_cache[buf_key], format="audio/mp3")
            except Exception as tts_err:
                st.warning(f"Text-to-speech unavailable ({tts_err}). gTTS needs an internet connection.")

# ===== Key Dates tab =====
with tab_dates:
    dates = analysis.get("key_dates") or []
    if not dates:
        st.markdown('<div class="empty-state"><strong>No dates detected</strong>The model did not find explicit dates or deadlines in this artifact.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="result-card">', unsafe_allow_html=True)
        st.markdown("<h4>Key dates & deadlines</h4>", unsafe_allow_html=True)
        st.markdown('<div class="metric-grid">', unsafe_allow_html=True)
        for d in dates:
            label = html.escape(str(d.get("label", "Deadline")))
            value = str(d.get("date", ""))
            try:
                parsed = dt.date.fromisoformat(value[:10])
                days = (parsed - dt.date.today()).days
                value = f"{parsed.strftime('%d %b %Y')} · {'days left: ' + str(days) if days >= 0 else 'passed'}"
            except ValueError:
                pass
            st.markdown(
                f'<div class="metric"><div class="metric-label">{label}</div>'
                f'<div class="metric-value">{html.escape(value)}</div></div>',
                unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        ics = build_ics(dates, title=str(analysis.get("title") or "CivicLens"))
        st.download_button("📅 Add to calendar (.ics)", ics, file_name="civiclens-deadlines.ics",
                           mime="text/calendar", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.caption("The .ics file adds each parsed deadline with a reminder one day before.")

# ===== Actions tab =====
with tab_actions:
    if analysis.get("form_fields") or analysis.get("required_documents"):
        st.markdown('<div class="result-card"><h4>Form helper — what each field means</h4>', unsafe_allow_html=True)
        for f in analysis.get("form_fields") or []:
            st.markdown(
                f'<div class="check-item"><strong>{html.escape(str(f.get("field")))}</strong> — {html.escape(str(f.get("explanation")))}</div>',
                unsafe_allow_html=True)
        st.markdown("<h4>Documents to bring</h4>", unsafe_allow_html=True)
        for doc in analysis.get("required_documents") or []:
            st.checkbox(html.escape(str(doc)), key=f"doc::{hash(doc)}")
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown('<div class="section-kicker">04 / Act</div>', unsafe_allow_html=True)
    st.markdown('<div class="result-card">', unsafe_allow_html=True)
    st.markdown("<h4>Next steps</h4>", unsafe_allow_html=True)
    items = analysis.get("action_items") or []
    if items:
        for item in items:
            st.markdown(f'<div class="check-item">{html.escape(str(item))}</div>', unsafe_allow_html=True)
    else:
        st.caption("No action items were returned for this artifact.")
    st.markdown("</div>", unsafe_allow_html=True)

# ===== Chat tab =====
with tab_chat:
    st.markdown('<div class="section-kicker">Ask follow-up questions</div>', unsafe_allow_html=True)
    starters = suggested_questions(analysis)
    cols = st.columns(3)
    for col, question in zip(cols, starters):
        if col.button(question[:44] + ("…" if len(question) > 44 else ""),
                      key=f"starter::{hash(question)}", use_container_width=True):
            st.session_state.chat.append({"role": "user", "content": question})
            st.rerun()

    for message in st.session_state.chat:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    if question := st.chat_input("Ask about this document, e.g. 'what do I do first?'"):
        st.session_state.chat.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    answer = chat_turn(image_b64, analysis, question, language, st.session_state.chat[:-1])
                    st.session_state.chat.append({"role": "assistant", "content": answer["reply"]})
                    st.write(answer["reply"])
                except ModelTimeout:
                    st.error("The model took too long to answer. Please retry.")
                except (requests.exceptions.RequestException, KeyError, IndexError, ValueError, json.JSONDecodeError) as err:
                    st.error(f"Chat failed: {err}")

# ===== Report tab =====
with tab_report:
    if mode == "Civic Issue Photo":
        st.markdown('<div class="section-kicker">Civic issue report</div>', unsafe_allow_html=True)
        report = make_report(analysis, address)
        colA, colB = st.columns(2)
        with colA:
            report["title"] = st.text_input("Complaint title", value=report["title"], key="rep_title")
            report["issue_type"] = st.text_input("Issue type", value=report["issue_type"], key="rep_type")
            report["severity"] = st.select_slider("Severity", options=["Minor", "Major"],
                                                  value=report["severity"], key="rep_sev")
        with colB:
            report["authority"] = st.text_input("Suggested authority / department", value=report["authority"], key="rep_auth")
            report["urgency"] = st.select_slider("Urgency", options=["Low", "Medium", "High"],
                                                 value=report["urgency"], key="rep_urg")
            report["location"] = st.text_input("Location", value=address or report["location"], key="rep_loc")
        report["description"] = st.text_area("Description", value=report["description"], height=130, key="rep_desc")
        st.session_state.report = report
    else:
        st.caption("The complaint report generator is designed for civic issue photos. Switch the mode to 'Civic Issue Photo' and upload a photo to use it.")

    # Letter drafter
    st.markdown('<div class="section-kicker">Complaint letter</div>', unsafe_allow_html=True)
    if st.button("✉️ Draft complaint letter"):
        source = st.session_state.report or make_report(analysis, address)
        st.session_state.letter = draft_letter(source)
    if st.session_state.get("letter"):
        letter = st.text_area("Edit your letter", value=st.session_state.letter, height=320, key="letter_edit")
        lcol1, lcol2, lcol3 = st.columns(3)
        with lcol1:
            st.download_button("⬇️ Download .txt", letter, file_name="complaint-letter.txt",
                               mime="text/plain", use_container_width=True)
        with lcol2:
            try:
                from io import BytesIO
                pdf = build_pdf(
                    {"summary": letter, "category": "", "urgency": "", "key_details": {},
                     "key_dates": [], "action_items": [], "glossary": {},
                     "required_documents": []},
                    letter=None, title="Complaint Letter")
                st.download_button("⬇️ Download .pdf", pdf, file_name="complaint-letter.pdf",
                                   mime="application/pdf", use_container_width=True)
            except Exception as pdf_err:
                st.caption(f"PDF export unavailable: {pdf_err}")
        with lcol3:
            try:
                import pyperclip
                if st.button("📋 Copy letter", use_container_width=True):
                    try:
                        pyperclip.copy(letter)
                        st.success("Copied to clipboard.")
                    except pyperclip.PyperclipException:
                        st.info("Clipboard not available here — use Download instead.")
            except ImportError:
                st.caption("Install pyperclip to enable the copy button.")

    # Full PDF report
    st.markdown('<div class="section-kicker">Export full report</div>', unsafe_allow_html=True)
    if st.button("📄 Export report as PDF"):
        try:
            pdf_bytes = build_pdf(analysis, letter=st.session_state.get("letter"))
            st.session_state["_pdf"] = pdf_bytes
        except Exception as err:
            st.error(f"PDF export failed: {err}")
            st.download_button("⬇️ Download as .txt instead",
                               build_text(analysis, st.session_state.get("letter")),
                               file_name="civiclens-report.txt", mime="text/plain")
    if st.session_state.get("_pdf"):
        st.download_button("⬇️ Download PDF report", st.session_state["_pdf"],
                           file_name="civiclens-report.pdf", mime="application/pdf")

st.markdown(f'<div style="text-align:center; color:#718b8e; font-size:.78rem; padding:2.5rem 0 1rem;">{DISCLAIMER} Powered by Gemma 4 &amp; AWS.</div>', unsafe_allow_html=True)
