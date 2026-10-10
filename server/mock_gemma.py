"""Mock Gemma 4 OpenAI-compatible server for local UI testing.

Simulates the /v1/chat/completions endpoint on port 8000 with tool calling,
so client/app.py can be tested without a GPU or real Gemma 4 deployment.

Start:  python server/mock_gemma.py
Stop:   pkill -f mock_gemma.py
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8000

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


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/v1/models":
            body = {"object": "list", "data": [{"id": "google/gemma-4-12b-it", "object": "model"}]}
            self._json(200, body)
        elif self.path == "/healthz":
            self._json(200, {"status": "ok", "mock": True})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid JSON"})
            return

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
        body = {
            "id": "chatcmpl-mock-1",
            "object": "chat.completion",
            "model": payload.get("model", "google/gemma-4-12b-it"),
            "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls"}],
        }
        self._json(200, body)

    def _json(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt, *args):
        print(f"[mock_gemma] {fmt % args}")


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[mock_gemma] listening on http://localhost:{PORT} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[mock_gemma] stopped")
