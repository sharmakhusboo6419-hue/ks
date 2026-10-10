import base64
import html
import json
import os
import re

import requests
import streamlit as st


st.set_page_config(
    page_title="CivicLens | Clear civic action",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

GEMMA_4_ENDPOINT = os.environ.get(
    "GEMMA_4_ENDPOINT",
    "http://localhost:8000/v1/chat/completions",
)
SUPPORTED_TYPES = ["jpg", "jpeg", "png"]
MODES = {
    "Public Notice": "public notice, announcement, deadline, or policy document",
    "Municipal Form": "municipal form, application, benefit, fee, or required paperwork",
    "Civic Issue Photo": "street-level civic issue such as a pothole, leak, outage, or damaged infrastructure",
}

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
.block-container { max-width: 1240px; padding: 3.2rem 4rem 2rem; }
h1, h2, h3, .hero-title { font-family: 'Space Grotesk', sans-serif !important; letter-spacing: -0.02em; }
h1 { font-size: clamp(2.4rem, 5vw, 4.6rem) !important; line-height: 1.02 !important; }
h2 { font-size: 1.5rem !important; }
p, label, .stCaption { color: var(--muted); }
.hero { padding: 0 0 2.4rem; }
.eyebrow { color: var(--teal); font-size: .76rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; }
.hero-title { background: linear-gradient(100deg, #f3f8f7 15%, #68dec9 60%, #77aaff 100%); -webkit-background-clip: text; background-clip: text; color: transparent; margin: .35rem 0 .8rem; }
.hero-copy { font-size: 1.13rem; line-height: 1.65; max-width: 680px; }
.hero-mark { display: inline-flex; align-items: center; justify-content: center; width: 2rem; height: 2rem; margin-right: .55rem; border: 1px solid rgba(85,214,194,.4); border-radius: 10px; background: rgba(85,214,194,.12); }
.workflow { display: grid; grid-template-columns: repeat(4, 1fr); gap: .65rem; margin: .5rem 0 2.2rem; }
.workflow-step { border-top: 1px solid var(--line); padding: .8rem .2rem 0; color: var(--muted); font-size: .85rem; }
.workflow-step strong { display: block; color: var(--ink); font-size: .95rem; margin-bottom: .2rem; }
.workflow-step span { color: var(--teal); font-weight: 700; margin-right: .35rem; }
.section-kicker { color: var(--muted); font-size: .77rem; letter-spacing: .12em; text-transform: uppercase; font-weight: 700; margin-bottom: .8rem; }
.upload-card, .result-card { background: var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: 1.35rem; box-shadow: 0 18px 60px rgba(0,0,0,.16); }
.upload-card { min-height: 225px; display: flex; flex-direction: column; justify-content: center; }
.upload-icon { color: var(--teal); font-size: 2rem; margin-bottom: .6rem; }
.upload-card h3 { margin: 0 0 .35rem; font-size: 1.25rem; }
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


def parse_plain_text(text: str) -> dict:
    """Keep plain-text model responses useful when tool calling is unavailable."""
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    return {
        "category": "Community Update",
        "title": "Civic information summary",
        "summary": cleaned or "The model returned an empty response.",
        "action_items": ["Verify the details with the official source before acting."],
        "key_details": {},
        "urgency": "Medium",
    }


def normalize_result(raw: dict | str) -> dict:
    if isinstance(raw, str):
        return parse_plain_text(raw)
    data = dict(raw)
    data["summary"] = data.get("summary") or data.get("content") or "No summary was returned."
    data["action_items"] = data.get("action_items") or data.get("action_steps") or []
    data["key_details"] = data.get("key_details") or {
        key: data.get(key)
        for key in ("deadline", "location", "fee")
        if data.get(key)
    }
    data["urgency"] = str(data.get("urgency", "Medium")).title()
    return data


def request_analysis(image_b64: str, mode: str, language: str, detail_level: str) -> dict:
    tools = [{
        "type": "function",
        "function": {
            "name": "display_civic_data",
            "description": "Parse civic information into clear actions for residents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"}, "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "action_steps": {"type": "array", "items": {"type": "string"}},
                    "key_details": {"type": "object"}, "urgency": {"type": "string"},
                },
                "required": ["category", "title", "summary", "action_steps", "urgency"],
            },
        },
    }]
    prompt = (
        f"Analyze this {MODES[mode]}. Return a display_civic_data tool call. "
        f"Write the response in {language}. Detail level: {detail_level}. "
        "Include dates, deadlines, locations, fees, or missing details in key_details."
    )
    payload = {
        "model": "google/gemma-4-12b-it",
        "messages": [
            {"role": "system", "content": "You are a multimodal community intelligence assistant. Turn complex civic material into plain, actionable guidance."},
            {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}, {"type": "text", "text": prompt}]},
        ],
        "tools": tools,
        "tool_choice": "auto",
    }
    response = requests.post(GEMMA_4_ENDPOINT, json=payload, headers={"Content-Type": "application/json"}, timeout=90)
    response.raise_for_status()
    message = response.json()["choices"][0]["message"]
    tool_calls = message.get("tool_calls", [])
    if tool_calls:
        return normalize_result(json.loads(tool_calls[0]["function"]["arguments"]))
    return normalize_result(message.get("content", ""))


def render_results(data: dict) -> None:
    category = html.escape(str(data.get("category", "Community update")))
    urgency = html.escape(str(data.get("urgency", "Medium")).title())
    urgency_class = re.sub(r"[^a-z]", "", urgency.lower()) or "medium"
    title = html.escape(str(data.get("title", "Civic information summary")))
    st.markdown('<div class="section-kicker">02 / Understand</div>', unsafe_allow_html=True)
    st.markdown('<div class="result-card">', unsafe_allow_html=True)
    st.markdown(f'<span class="badge badge-category">{category}</span> <span class="badge badge-{urgency_class}">{urgency} urgency</span>', unsafe_allow_html=True)
    st.markdown(f'<h2 class="result-title">{title}</h2>', unsafe_allow_html=True)
    st.markdown("<h4>In plain language</h4>", unsafe_allow_html=True)
    st.write(data.get("summary", "No summary was returned."))

    details = data.get("key_details", {})
    if details:
        st.markdown("<h4>Key details</h4>", unsafe_allow_html=True)
        st.markdown('<div class="metric-grid">', unsafe_allow_html=True)
        for label, value in details.items():
            safe_label = html.escape(str(label).replace("_", " "))
            safe_value = html.escape(str(value))
            st.markdown(f'<div class="metric"><div class="metric-label">{safe_label}</div><div class="metric-value">{safe_value}</div></div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<h4>Next steps</h4>", unsafe_allow_html=True)
    for item in data.get("action_items", []):
        st.markdown(f'<div class="check-item">{html.escape(str(item))}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


with st.sidebar:
    st.markdown("## CivicLens")
    st.caption("Settings for this analysis")
    language = st.selectbox("Output language", ["English", "Spanish", "Hindi", "French"], index=0)
    detail_level = st.select_slider("Detail level", options=["Essential", "Balanced", "Thorough"], value="Balanced")
    st.divider()
    st.markdown("### How it works")
    st.markdown("**1. Upload** a notice, form, or issue photo.\n\n**2. Analyze** the visual context with Gemma 4.\n\n**3. Understand** the important details in plain language.\n\n**4. Act** with clear next steps.")
    st.divider()
    st.caption("AI-generated guidance should be verified with official sources.")

st.markdown('<div class="hero"><div class="eyebrow"><span class="hero-mark">🏛️</span> Civic clarity, one upload away</div><h1 class="hero-title">Make civic information easier to act on.</h1><p class="hero-copy">Turn confusing civic documents and street-level issues into clear, actionable insight for your community.</p></div>', unsafe_allow_html=True)
st.markdown('<div class="workflow"><div class="workflow-step"><strong><span>01</span> Upload</strong>Share a civic artifact</div><div class="workflow-step"><strong><span>02</span> Analyze</strong>Read the visual context</div><div class="workflow-step"><strong>03 <span style="color: var(--teal)">Understand</span></strong>See plain-language guidance</div><div class="workflow-step"><strong><span>04</span> Act</strong>Know what to do next</div></div>', unsafe_allow_html=True)

mode = st.radio("What are you sharing?", list(MODES), horizontal=True, label_visibility="collapsed")
st.markdown('<div class="section-kicker">01 / Upload</div>', unsafe_allow_html=True)
st.markdown('<div class="upload-card"><div class="upload-icon">＋</div><h3>Drop a notice, form, or photo here</h3><p>Choose a clear image so CivicLens can read the details that matter.</p><div><span class="detail-pill">JPG</span> <span class="detail-pill">JPEG</span> <span class="detail-pill">PNG</span></div><div class="privacy">Privacy note: your image is sent only to the configured analysis endpoint.</div></div>', unsafe_allow_html=True)
uploaded_file = st.file_uploader("Upload civic artifact", type=SUPPORTED_TYPES, label_visibility="collapsed")

if uploaded_file is None:
    st.markdown('<div class="empty-state"><strong>Your analysis will appear here</strong>Upload an image above to turn the next civic question into a clear plan.</div>', unsafe_allow_html=True)
else:
    bytes_data = uploaded_file.getvalue()
    image_b64 = base64.b64encode(bytes_data).decode("utf-8")
    left, right = st.columns([0.92, 1.08], gap="large")
    with left:
        st.markdown('<div class="section-kicker">Artifact preview</div>', unsafe_allow_html=True)
        st.image(bytes_data, width="stretch")
        st.caption(f"{uploaded_file.name} · {len(bytes_data) / 1024:.0f} KB · {mode}")
    with right:
        st.markdown('<div class="section-kicker">02 / Analyze</div>', unsafe_allow_html=True)
        if st.button("Analyze and reveal next steps", type="primary", use_container_width=True):
            with st.status("CivicLens is reading your artifact...", expanded=True) as status:
                st.write("Reading document structure and visual context...")
                st.write("Extracting dates, places, fees, and required actions...")
                try:
                    st.session_state.analysis = request_analysis(image_b64, mode, language, detail_level)
                    status.update(label="Analysis ready", state="complete", expanded=False)
                except requests.exceptions.RequestException as error:
                    status.update(label="Analysis endpoint unavailable", state="error", expanded=True)
                    st.error(f"CivicLens could not reach the analysis service. Check GEMMA_4_ENDPOINT or start the local mock server. Details: {error}")
                except (KeyError, IndexError, json.JSONDecodeError, ValueError) as error:
                    status.update(label="The response could not be understood", state="error", expanded=True)
                    st.error(f"The model returned an unexpected response: {error}")

if "analysis" in st.session_state:
    st.divider()
    result_left, result_right = st.columns([1.35, .65], gap="large")
    with result_left:
        render_results(st.session_state.analysis)
    with result_right:
        st.markdown('<div class="section-kicker">04 / Act</div>', unsafe_allow_html=True)
        st.markdown('<div class="result-card"><h4>Take it with you</h4><p>Keep a plain-text copy of this guidance for your records or community group.</p></div>', unsafe_allow_html=True)
        summary = st.session_state.analysis.get("summary", "")
        download_text = f"{st.session_state.analysis.get('title', 'CivicLens summary')}\n\n{summary}\n\nNext steps:\n" + "\n".join(f"- {item}" for item in st.session_state.analysis.get("action_items", []))
        st.download_button("Download summary", download_text, file_name="civiclens-summary.txt", mime="text/plain", use_container_width=True)
        st.code(summary, language=None)

st.markdown('<div style="text-align:center; color:#718b8e; font-size:.78rem; padding:3rem 0 1rem;">Powered by Gemma 4 &amp; AWS · AI-generated results should be verified with official sources.</div>', unsafe_allow_html=True)