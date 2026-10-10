"""Model inference layer for CivicLens.

Wraps the existing OpenAI-compatible call to Gemma 4. The original
request/response shape (multimodal messages + display_civic_data tool call)
is unchanged — this module only adds caching and error mapping.
"""
import requests
import streamlit as st

from parsers import extract_tool_args, normalize_analysis, normalize_chat
from prompts import payload_for, analysis_prompt, chat_prompt

GEMMA_4_ENDPOINT = "http://localhost:8000/v1/chat/completions"
REQUEST_TIMEOUT = 90


class ModelTimeout(Exception):
    pass


def _post(payload: dict) -> dict:
    try:
        response = requests.post(
            GEMMA_4_ENDPOINT, json=payload,
            headers={"Content-Type": "application/json"}, timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout as err:
        raise ModelTimeout("The model took too long to respond.") from err


@st.cache_data(show_spinner="Analyzing artifact with Gemma 4...")
def analyze_artifact(image_b64: str, mode: str, language: str, simplify: bool,
                     voice_query: str = "") -> dict:
    """First analysis. Cached on (image, mode, language, simplify, voice_query),
    so toggling language/simplify or re-running chat does not hit the model again
    for the same inputs."""
    payload = payload_for(image_b64, analysis_prompt(mode, language, simplify, voice_query))
    result = _post(payload)
    message = result["choices"][0]["message"]
    raw = extract_tool_args(message)
    if isinstance(raw, dict):
        return normalize_analysis(raw)
    # No tool call: fall back to plain text so the UI still shows something.
    return normalize_analysis(raw)


def chat_turn(image_b64: str, first_analysis: dict, question: str, language: str,
              history: list[dict]) -> dict:
    """Follow-up question with the image + first analysis in context.

    Not cached: the same question with different history has a different answer.
    """
    context_note = (
        f"Earlier analysis of the uploaded document: category={first_analysis.get('category')}, "
        f"urgency={first_analysis.get('urgency')}, summary: {first_analysis.get('summary', '')}"
    )
    payload = payload_for(
        image_b64,
        chat_prompt(question, language) + " Context: " + context_note,
        chat_history=list(history[-6:]),  # last 3 exchanges
    )
    result = _post(payload)
    message = result["choices"][0]["message"]
    return normalize_chat(extract_tool_args(message))
