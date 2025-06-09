"""The main application entry point for the GitHub Policy Dashboard."""

import streamlit as st

st.set_page_config(
    page_title="GitHub Policy Dashboard",
    page_icon="./src/branding/ONS-symbol_digital.svg",
    layout="wide",
)

pg = st.navigation([
    st.Page("./repositories/repositories.py", title="Repositories", icon="📦"),
    st.Page("./secret_scanning/secret_scanning.py", title="Secret Scanning", icon="🔍"),
    st.Page("./dependabot/dependabot.py", title="Dependabot", icon="🤖"),
])

pg.run()
