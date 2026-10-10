"""Custom Streamlit component: browser voice recognition (Web Speech API).

Returns the recognized transcript to Python via Streamlit.setComponentValue,
so the Streamlit app can use dictated speech as extra context for the
Gemma 4 analysis prompt — mirroring the voice feature in server/index.html.
"""
import os

import streamlit.components.v1 as components

_component = components.declare_component(
    "voice_input",
    path=os.path.join(os.path.dirname(__file__), "components"),
)


def voice_input(key: str = "voice") -> str | None:
    """Render the mic + transcript component.

    Returns the current transcript (str) while the user speaks, or None if
    nothing has been dictated yet. The value persists in the component state
    until the page reloads.
    """
    return _component(key=key, default=None)
