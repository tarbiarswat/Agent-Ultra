import streamlit as st
# --- make project root importable ---
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path: sys.path.insert(0, ROOT)
# ------------------------------------

from app.main import run

st.set_page_config(page_title="Local Agent", layout="wide")
st.title("Local Agent (fully on-device)")

goal = st.text_area("Goal", "Open https://example.com, read the page, then say Done.")
if st.button("Run"):
    state = run(goal)
    for i, s in enumerate(state.steps, 1):
        with st.expander(f"Step {i}: {s.action}"):
            st.write("Thought:", s.thought)
            st.json({"action": s.action, "args": s.args})
            st.write("Result:", s.result)
