"""The main application entry point for the GitHub Policy Dashboard."""

import streamlit as st
from src.refresh_data import refresh_data

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

st.sidebar.button(
    "Refresh Dataset",
    key="refresh_dataset",
    on_click=refresh_data,
    help="Click to refresh the dataset from GitHub. This may take a few minutes.",
    icon="🔄",
)

pg.run()
