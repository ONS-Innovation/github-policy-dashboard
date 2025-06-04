"""The Secret Scanning Analysis Page for the GitHub Policy Dashboard."""

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
    filename="secret_scanning.json"
)

df_secret_scanning = collection.load_secret_scanning(
    _s3=s3,
    bucket=env["bucket_name"]
)

if df_secret_scanning is None:
    st.error("Error loading secret scanning data. Please check the S3 bucket and file.")


rest = utils.get_rest_interface(
    _secret_manager=secret_manager,
    secret_name=env["secret_name"],
    org=env["org"],
    client_id=env["client_id"]
)

df_secret_scanning = fmt.add_repository_type(
    df_secret_scanning=df_secret_scanning,
    _secret_manager=secret_manager,
    secret_name=env["secret_name"],
    org=env["org"],
    client_id=env["client_id"],
)


st.logo("./src/branding/ONS_Logo_Digital_Colour_Landscape_Bilingual_RGB.svg")

col1, col2 = st.columns([0.6, 0.4], vertical_alignment="bottom")

with col1:
    st.title(":blue-background[GitHub Policy Dashboard]")
with col2:
    st.html(f"<p style='text-align: right; font-size: x-large;'><b>Last Updated:</b> {last_modified}</p>")
    
st.header(":blue-background[Secret Scanning Analysis 🔍]")

st.write("Alerts open for more than 5 days.")

if len(df_secret_scanning) == 0:
    st.write("No secret scanning alerts found.")
    st.stop()

with st.form("Secret Scanning Filters"):
    col1, col2 = st.columns(2)

    start_date = col1.date_input("Start Date", pd.to_datetime(df_secret_scanning["Creation Date"].min()), key="start_date_secrets")
    end_date = col2.date_input("End Date", (datetime.datetime.now() + datetime.timedelta(days=1)).date(), key="end_date_secrets")

    st.caption(
        "**Please Note:** The above date range is used to filter the creation date of secret scanning alerts."
    )

    type_list = df_secret_scanning["Repository Type"].unique().tolist()
    selected_types = st.multiselect(
        "Repository Type",
        type_list,
        default=type_list,
        key="repo_type_secrets"
    )

    st.form_submit_button("Apply Filters", use_container_width=True)

if end_date < start_date:
    st.error("End date cannot be earlier than start date.")
    st.stop()

df_secret_scanning = fmt.filter_secret_scanning(
    df_secret_scanning=df_secret_scanning,
    start_date=start_date,
    end_date=end_date,
    types_to_exclude= [t for t in type_list if t not in selected_types],
)

if df_secret_scanning.empty:
    st.write("No secret scanning alerts found for the selected filters.")
    st.stop()

total_secret_alerts = df_secret_scanning["Alert Age (Days)"].count()
oldest_alert = df_secret_scanning["Alert Age (Days)"].max()
total_repositories = df_secret_scanning["Repository"].nunique()
alerts_per_repository = total_secret_alerts / total_repositories

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Alerts", total_secret_alerts, border=True)
col2.metric("Oldest Alert", oldest_alert, border=True)
col3.metric("Number of Repositories", total_repositories, border=True)
col4.metric("Average Alerts per Repository", round(alerts_per_repository, 2), border=True)

df_grouped_secrets = fmt.group_secret_scanning_by_repository(
    df_secret_scanning=df_secret_scanning,
)

# Get repository with most alerts from df_grouped_secrets
most_alerts_repo = df_grouped_secrets["Total Alerts"].idxmax()
most_alerts_count = df_grouped_secrets["Total Alerts"].max()

col1, col2 = st.columns([0.7, 0.3])

col1.metric("Repository with Most Alerts", most_alerts_repo, border=True)
col2.metric("Number of Repository Alerts", most_alerts_count, border=True)

# Pie chart showing the number of alerts by repository

fig = px.pie(
    df_grouped_secrets.reset_index(),
    values="Total Alerts",
    names="Repository",
    title="Total Alerts by Repository",
)

st.plotly_chart(fig)

st.dataframe(
    df_secret_scanning, 
    use_container_width=True, 
    hide_index=True,
    column_config={
        "URL": st.column_config.LinkColumn()
    }
)
