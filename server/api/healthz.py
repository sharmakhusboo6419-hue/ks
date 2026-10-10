"""GET /healthz — Vercel Python serverless function."""
import json


def handler(event, context):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "ok", "mock": True}),
    }
