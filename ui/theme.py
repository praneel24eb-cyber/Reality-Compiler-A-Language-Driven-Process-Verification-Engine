"""Shared visual language for the process intelligence workspace."""

from pathlib import Path

import streamlit as st


def apply_theme():
    st.html("<style>" + Path(__file__).with_name("theme.css").read_text(encoding="utf-8") + "</style>")
    with st.sidebar:
        st.html('''<div class="rc-brand"><div class="rc-mark">◈</div><div>Reality<br><b>Compiler</b></div></div>
        <div class="rc-sidebar-kicker">PROCESS INTELLIGENCE</div>''')
        st.caption("Understand the process.\nSee what’s missing.")
    st.html('''<div class="rc-topbar"><span>REALITY COMPILER <span class="rc-slash">/</span> WORKSPACE</span>
    <span class="rc-badge">Evidence-led workflows</span></div>''')
