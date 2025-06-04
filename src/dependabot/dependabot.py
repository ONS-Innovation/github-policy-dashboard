"""The Dependabot Analysis Page for the GitHub Policy Dashboard."""

import streamlit as st
import boto3
import datetime
import pandas as pd
import plotly.express as px

import utilities as utils
import secret_scanning.collection as collection
import secret_scanning.formatting as fmt

env = utils.get_environment_variables()

session = boto3.Session()
s3 = session.client("s3")
secret_manager = session.client("secretsmanager", region_name=env["secret_region"])


last_modified = utils.get_last_modified(
    s3=s3,
    bucket=env["bucket_name"],
    filename="dependabot.json"
)

st.logo("./src/branding/ONS_Logo_Digital_Colour_Landscape_Bilingual_RGB.svg")

col1, col2 = st.columns([0.6, 0.4], vertical_alignment="bottom")

with col1:
    st.title(":blue-background[GitHub Policy Dashboard]")
with col2:
    st.html(f"<p style='text-align: right; font-size: x-large;'><b>Last Updated:</b> {last_modified}</p>")
     
st.header(":blue-background[Dependabot Analysis 🤖]")
