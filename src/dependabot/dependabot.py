import streamlit as st

last_modified = "2023-10-01 @ 06:00"  # Placeholder for the last modified date

st.logo("./src/branding/ONS_Logo_Digital_Colour_Landscape_Bilingual_RGB.svg")

col1, col2 = st.columns([0.6, 0.4], vertical_alignment="bottom")

with col1:
    st.title(":blue-background[GitHub Policy Dashboard]")
with col2:
    st.html(f"<p style='text-align: right; font-size: x-large;'><b>Last Updated:</b> {last_modified}</p>")
     
st.header("Dependabot Analysis 🤖")
