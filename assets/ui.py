import pathlib
import streamlit as st

def inject_css():
    css = pathlib.Path("assets/style.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

def kpi(title: str, value: str, sub: str = "", badge: str = ""):
    st.markdown(
        f"""
        <div class="card">
          <div class="title">{title}</div>
          <div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-end;">
            <div class="value">{value}</div>
            {f'<div class="badge">{badge}</div>' if badge else ''}
          </div>
          {f'<div class="sub">{sub}</div>' if sub else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )

def section(title: str, subtitle: str = ""):
    st.markdown(f"## {title}")
    if subtitle:
        st.caption(subtitle)
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
