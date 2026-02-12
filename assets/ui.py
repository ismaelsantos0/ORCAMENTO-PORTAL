import pathlib
import streamlit as st

def inject_css(path: str = "assets/style.css"):
    css = pathlib.Path(path).read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

def card(title: str, subtitle: str = "", right: str = ""):
    st.markdown(
        f"""
        <div class="portal-card">
          <div class="kpi">
            <div>
              <div class="label">{title}</div>
              <div class="small-muted">{subtitle}</div>
            </div>
            <div class="tag">{right}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
