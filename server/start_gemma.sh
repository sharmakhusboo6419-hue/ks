#!/bin/bash
pip install vllm huggingface_hub

# Replace with your actual Hugging Face Access Token
export HUGGING_FACE_HUB_TOKEN="hf_YOUR_HUGGINGFACE_TOKEN_HERE"

# Launch vLLM server with official Gemma 4 reasoning & tool call flags
vllm serve google/gemma-4-E4B-it \
    --tensor-parallel-size 1 \
    --max-model-len 8192 \
    --port 8000 \
    --host 0.0.0.0 \
    --enable-auto-tool-choice \
    --reasoning-parser gemma4 \
    --tool-call-parser gemma4
