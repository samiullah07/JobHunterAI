import streamlit as st

st.set_page_config(
    page_title="AI Job Hunter",
    page_icon="🎯",
    layout="wide",
)

st.sidebar.title("AI Job Hunter")
st.sidebar.markdown("Your autonomous job-hunting assistant")
st.sidebar.divider()

st.title("Welcome to AI Job Hunter")
st.markdown("""
This tool helps you find jobs, generate tailored CVs and cover letters, and apply.

**How to use it:**
1. **My Profile** — enter your details (name, skills, experience)
2. **Browse Jobs** — see all discovered jobs, generate a tailored CV for any of them
3. **Review Queue** — review and approve your applications
4. **My Applications** — get apply links and download your CV/cover letters

Use the sidebar to navigate between pages.
""")