"""Prompt builders for CivicLens.

Kept separate from app.py so the model-facing text lives in one place.
The model is asked (via tool calling) to return structured JSON with the
fields below; parsers.py validates the response and falls back safely.
"""
import json

MODES = {
    "Public Notice": "public notice, announcement, deadline, or policy document",
    "Municipal Form": "municipal form, application, benefit, fee, or required paperwork",
    "Civic Issue Photo": "street-level civic issue such as a pothole, garbage, streetlight outage, water leak, or damaged infrastructure",
}

LANGUAGES = {
    "English": "en",
    "Hindi": "hi",
    "Kannada": "kn",
    "Tamil": "ta",
    "Telugu": "te",
    "Marathi": "mr",
}

# All fields the model should populate. parsers.py guarantees every key exists
# even if the model omits some.
ANALYSIS_FIELDS = [
    "category", "urgency", "summary",
    "key_details",            # dict[str, str]: deadline, location, fee, office, ...
    "key_dates",              # list[dict]: {"label": str, "date": "YYYY-MM-DD" or free text}
    "action_items",           # list[str]
    "glossary",               # dict[str, str]: jargon -> plain-language definition
    "form_fields",            # list[dict]: {"field": str, "explanation": str} (forms only)
    "required_documents",     # list[str] (forms only)
    "suggested_authority",    # str (photo issues: department to complain to)
    "confidence",             # dict[str, float]: field name -> 0..1
]

CHAT_FIELDS = ["reply", "action_items", "confidence"]


def analysis_prompt(mode: str, language: str, simplify: bool, voice_query: str = "") -> str:
    """Prompt for the first analysis of an uploaded artifact."""
    extra = ""
    if voice_query:
        extra += f'\nThe citizen also asks (spoken/typed): "{voice_query}". Address it in the summary and action items.'
    if simplify:
        extra += (
            "\nSIMPLIFY MODE: write the summary at a 6th-grade reading level, "
            "short sentences, no jargon. Put any technical term you could not avoid "
            "in glossary with a one-line plain definition."
        )
    fields = ", ".join(ANALYSIS_FIELDS)
    return (
        f"Analyze this {MODES[mode]} and return a display_civic_data tool call.\n"
        f"Write all human-readable text (summary, action_items, key_details, "
        f"glossary, form_fields, required_documents) in {language}.\n"
        "Use ISO dates (YYYY-MM-DD) in key_dates where a real date is visible; "
        "otherwise use free text. Set confidence per field between 0 and 1 based "
        "on how clearly you can read it; use < 0.6 for anything uncertain."
        f" Populate form_fields and required_documents only for municipal forms, "
        f"and suggested_authority only for civic issue photos."
        f"{extra}\n"
        f"Required top-level fields: {fields}."
    )


def chat_prompt(question: str, language: str) -> str:
    """Prompt for a follow-up chat turn. The image + first analysis stay in context."""
    return (
        f"The citizen asks: {question}\n"
        "Answer using the uploaded image and the earlier analysis shown in this "
        f"conversation. Reply in {language}. Return a display_civic_data tool call "
        f"with fields: {', '.join(CHAT_FIELDS)}. Put your answer in 'reply', any new "
        "action items in 'action_items', and your certainty in 'confidence.reply'."
    )


def suggested_questions(analysis: dict) -> list[str]:
    """Three starter questions derived from the first analysis (no extra model call)."""
    questions = []
    dates = analysis.get("key_dates") or []
    if dates:
        label = dates[0].get("label") or "the deadline"
        questions.append(f"What exactly is {label} and what happens if I miss it?")
    docs = analysis.get("required_documents") or []
    if docs:
        questions.append("What documents do I need and where do I get them?")
    if analysis.get("suggested_authority"):
        questions.append(f"How do I complain to {analysis['suggested_authority']}?")
    questions += [
        "Explain this in one simple sentence.",
        "What is the single most urgent thing for me to do?",
    ]
    seen, out = set(), []
    for q in questions:
        if q not in seen:
            seen.add(q)
            out.append(q)
        if len(out) == 3:
            break
    return out


def payload_for(image_b64: str, prompt: str, chat_history: list | None = None) -> dict:
    """OpenAI-compatible multimodal payload with the display_civic_data tool."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are a multimodal community intelligence assistant. Turn complex "
                "civic material into plain, actionable guidance. Always answer by "
                "calling the display_civic_data tool."
            ),
        }
    ]
    for turn in chat_history or []:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            {"type": "text", "text": prompt},
        ],
    })
    return {
        "model": "google/gemma-4-12b-it",
        "messages": messages,
        "tools": [{
            "type": "function",
            "function": {
                "name": "display_civic_data",
                "description": "Return structured civic information for the resident.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "urgency": {"type": "string"},
                        "summary": {"type": "string"},
                        "key_details": {"type": "object"},
                        "key_dates": {
                            "type": "array",
                            "items": {"type": "object", "properties": {
                                "label": {"type": "string"}, "date": {"type": "string"}}},
                        },
                        "action_items": {"type": "array", "items": {"type": "string"}},
                        "glossary": {"type": "object"},
                        "form_fields": {
                            "type": "array",
                            "items": {"type": "object", "properties": {
                                "field": {"type": "string"}, "explanation": {"type": "string"}}},
                        },
                        "required_documents": {"type": "array", "items": {"type": "string"}},
                        "suggested_authority": {"type": "string"},
                        "confidence": {"type": "object"},
                    },
                    "required": ["category", "summary", "action_items", "urgency"],
                },
            },
        }],
        "tool_choice": "auto",
    }
