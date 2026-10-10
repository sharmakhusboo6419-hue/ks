import streamlit as st
import requests
import json
import base64

st.set_page_config(page_title="CivicLens — Community Intelligence", layout="wide")

st.title("CivicLens: Multimodal Community Intelligence Engine")
st.caption("Powered by Google Gemma 4 & AWS Cloud Resources")

GEMMA_4_ENDPOINT = "http://localhost:8000/v1/chat/completions"

uploaded_file = st.file_uploader("Upload a public notice, municipal form, or photo of a civic issue...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    bytes_data = uploaded_file.getvalue()
    image_b64 = base64.b64encode(bytes_data).decode('utf-8')
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Uploaded Artifact")
        st.image(bytes_data, use_column_width=True)
        
    with col2:
        st.subheader("Gemma 4 Actionable Analysis")
        
        if st.button("Process & Extract Community Actions"):
            with st.spinner("Analyzing visual context & layout with Gemma 4..."):
                tools = [{
                    "type": "function",
                    "function": {
                        "name": "display_civic_data",
                        "description": "Parse civic information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "category": {"type": "string"},
                                "title": {"type": "string"},
                                "summary": {"type": "string"},
                                "action_steps": {"type": "array", "items": {"type": "string"}},
                                "urgency": {"type": "string"}
                            },
                            "required": ["category", "title", "summary", "action_steps", "urgency"]
                        }
                    }
                }]
                
                payload = {
                    "model": "google/gemma-4-12b-it",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a multimodal community intelligence assistant. Process visual inputs and trigger display_civic_data with simplified citizen actions."
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                                {"type": "text", "text": "Extract actionable instructions from this image."}
                            ]
                        }
                    ],
                    "tools": tools,
                    "tool_choice": "auto"
                }
                
                try:
                    res = requests.post(GEMMA_4_ENDPOINT, json=payload, headers={"Content-Type": "application/json"})
                    result = res.json()
                    
                    tool_calls = result['choices'][0]['message'].get('tool_calls', [])
                    if tool_calls:
                        data = json.loads(tool_calls[0]['function']['arguments'])
                        
                        st.success(f"**Category:** {data.get('category', 'Notice')}")
                        st.markdown(f"### {data.get('title')}")
                        st.write(data.get('summary'))
                        
                        st.markdown("#### Actionable Steps for Citizens:")
                        for idx, step in enumerate(data.get('action_steps', []), 1):
                            st.markdown(f"**{idx}.** {step}")
                            
                        st.warning(f"**Urgency Level:** {data.get('urgency')}")
                    else:
                        st.write(result['choices'][0]['message']['content'])
                except Exception as e:
                    st.error(f"Error connecting to Gemma 4 Endpoint: {str(e)}")