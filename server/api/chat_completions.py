"""POST /v1/chat/completions — Vercel Python serverless function."""
import json
import os
import sys

try:
    from ._gemma_logic import build_chat_completion
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from _gemma_logic import build_chat_completion


def handler(event, context):
    try:
        payload = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "invalid JSON"}),
        }
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(build_chat_completion(payload)),
    }
