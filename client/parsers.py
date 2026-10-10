"""Response parsing, validation, and safe fallbacks for CivicLens."""
import json
import re

from prompts import ANALYSIS_FIELDS, CHAT_FIELDS


def _as_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value) -> list:
    return value if isinstance(value, list) else []


def _as_str(value) -> str:
    return value if isinstance(value, str) else ("" if value is None else str(value))


def normalize_dates(raw_dates) -> list[dict]:
    """Ensure every key_date is {'label': str, 'date': str}."""
    out = []
    for item in _as_list(raw_dates):
        if isinstance(item, dict):
            out.append({"label": _as_str(item.get("label")), "date": _as_str(item.get("date"))})
        elif isinstance(item, str):
            # Accept plain strings like "2026-01-15" or "Deadline: 15 Jan 2026"
            m = re.search(r"(\d{4}-\d{2}-\d{2})", item)
            label = re.sub(r"\s*:.*$", "", item).strip() or "Deadline"
            out.append({"label": label, "date": m.group(1) if m else item})
    return [d for d in out if d["label"] or d["date"]]


def normalize_analysis(raw) -> dict:
    """Coerce any model output (tool call args or plain text) into a safe dict.

    Never raises: missing keys get sane defaults so the UI always renders.
    """
    if isinstance(raw, str):
        raw = {"summary": raw, "content": raw}
    data = dict(_as_dict(raw))
    data["category"] = _as_str(data.get("category")) or "Community Update"
    data["urgency"] = _as_str(data.get("urgency")).title() or "Medium"
    data["summary"] = (
        _as_str(data.get("summary")) or _as_str(data.get("content"))
        or "The model returned an empty response."
    )
    data["key_details"] = {str(k): _as_str(v) for k, v in _as_dict(data.get("key_details")).items()}
    data["key_dates"] = normalize_dates(data.get("key_dates"))
    data["action_items"] = [ _as_str(x) for x in _as_list(data.get("action_items") or data.get("action_steps")) if _as_str(x) ]
    data["glossary"] = {str(k): _as_str(v) for k, v in _as_dict(data.get("glossary")).items()}
    data["form_fields"] = [
        {"field": _as_str(f.get("field")), "explanation": _as_str(f.get("explanation"))}
        for f in _as_list(data.get("form_fields")) if isinstance(f, dict)
    ]
    data["required_documents"] = [ _as_str(x) for x in _as_list(data.get("required_documents")) if _as_str(x) ]
    data["suggested_authority"] = _as_str(data.get("suggested_authority"))
    confidence = {str(k): v for k, v in _as_dict(data.get("confidence")).items()}
    try:
        data["confidence"] = {k: float(v) for k, v in confidence.items() if v is not None}
    except (TypeError, ValueError):
        data["confidence"] = {}

    # Fill any missing top-level field so downstream code never KeyErrors.
    for field in ANALYSIS_FIELDS:
        data.setdefault(field, {} if field in ("key_details", "glossary", "confidence") else
                        [] if field in ("key_dates", "action_items", "form_fields", "required_documents") else "")
    return data


def normalize_chat(raw) -> dict:
    if isinstance(raw, str):
        raw = {"reply": raw, "content": raw}
    data = dict(_as_dict(raw))
    data["reply"] = _as_str(data.get("reply")) or _as_str(data.get("content")) or "(empty response)"
    data["action_items"] = [ _as_str(x) for x in _as_list(data.get("action_items")) if _as_str(x) ]
    data["confidence"] = {str(k): v for k, v in _as_dict(data.get("confidence")).items()}
    for field in CHAT_FIELDS:
        data.setdefault(field, {} if field == "confidence" else [] if field == "action_items" else "")
    return data


def extract_tool_args(message: dict) -> dict | str:
    """Pull display_civic_data args out of an OpenAI-compatible response message.

    Returns dict when a tool call is present, otherwise the plain text content.
    Raises ValueError only on malformed JSON inside a tool call (caller decides
    whether to fall back to plain text).
    """
    tool_calls = message.get("tool_calls") or []
    if tool_calls:
        try:
            return json.loads(tool_calls[0]["function"]["arguments"])
        except (json.JSONDecodeError, KeyError, TypeError) as err:
            raise ValueError(f"Malformed tool call arguments: {err}") from err
    content = message.get("content")
    if isinstance(content, list):  # some backends echo multimodal content
        content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
    return _as_str(content)


def issue_categories() -> dict[str, str]:
    """Mapping from category keyword to a default reporting department."""
    return {
        "pothole": "Roads & Transport Department (Municipal Corporation)",
        "road": "Roads & Transport Department (Municipal Corporation)",
        "garbage": "Solid Waste Management / Sanitation Department",
        "waste": "Solid Waste Management / Sanitation Department",
        "streetlight": "Electricity / Street Lighting Department",
        "light": "Electricity / Street Lighting Department",
        "water": "Water Supply & Sewerage Board",
        "leak": "Water Supply & Sewerage Board",
        "drain": "Water Supply & Sewerage Board",
        "sewer": "Water Supply & Sewerage Board",
        "tree": "Parks & Horticulture Department",
        "signal": "Traffic Police",
    }


def suggest_authority(category: str) -> str:
    cat = (category or "").lower()
    for keyword, authority in issue_categories().items():
        if keyword in cat:
            return authority
    return "Municipal Corporation (General Grievance Cell)"


def issue_severity(urgency: str) -> str:
    return {"High": "Major", "Critical": "Major"}.get((urgency or "").title(), "Minor")
