"""GET /v1/models — Vercel Python serverless function."""
import os
import sys

try:
    from ._gemma_logic import MODEL_ID
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from _gemma_logic import MODEL_ID


def handler(event, context):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": __import__("json").dumps(
            {"object": "list", "data": [{"id": MODEL_ID, "object": "model"}]}
        ),
    }
