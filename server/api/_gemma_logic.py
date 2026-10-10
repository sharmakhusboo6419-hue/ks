"""Shared logic for the mock Gemma 4 serverless functions.

Kept separate from the route handlers so each Vercel function file stays
small and the same heuristic tool-calling behavior can be reused.
"""
import json

# Simple heuristic: guess category from text, build a canned but plausible
# civic-data tool call so the Streamlit UI shows a full success path.
DEFAULT_DATA = {
    "category": "Public Notice",
    "title": "Community Notice Parsed",
    "summary": "The uploaded artifact was analyzed by the mock Gemma 4 endpoint. "
               "Replace this server with a real vLLM/SageMaker deployment for production.",
    "action_steps": [
        "Verify the notice details against official sources",
        "Share the parsed summary with your local community group",
        "Deploy a real Gemma 4 endpoint and update GEMMA_4_ENDPOINT",
    ],
    "urgency": "medium",
}

MODEL_ID = "google/gemma-4-12b-it"


def extract_text(messages):
    """Pull plain text out of the multimodal message list."""
    parts = []
    for msg in messages or []:
        content = msg.get("content")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
    return " ".join(parts)


def build_tool_call(text):
    data = dict(DEFAULT_DATA)
    text_lower = text.lower()
    if any(w in text_lower for w in ("water", "pipe", "leak", "supply")):
        data["category"], data["urgency"] = "Water Utility", "high"
    elif any(w in text_lower for w in ("road", "street", "pothole", "traffic")):
        data["category"], data["urgency"] = "Roads & Transport", "high"
    elif any(w in text_lower for w in ("electric", "power", "outage")):
        data["category"], data["urgency"] = "Electrical", "high"
    elif any(w in text_lower for w in ("health", "clinic", "hospital", "medical")):
        data["category"], data["urgency"] = "Health", "medium"
    data["title"] = f"{data['category']} Notice"
    return data


def build_chat_completion(payload):
    """Return the OpenAI-compatible chat completion body with a tool call."""
    text = extract_text(payload.get("messages"))
    data = build_tool_call(text)
    message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "call_mock_1",
            "type": "function",
            "function": {
                "name": "display_civic_data",
                "arguments": json.dumps(data),
            },
        }],
    }
    return {
        "id": "chatcmpl-mock-1",
        "object": "chat.completion",
        "model": payload.get("model", MODEL_ID),
        "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls"}],
    }
