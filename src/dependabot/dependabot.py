"""The Dependabot Analysis Page for the GitHub Policy Dashboard."""

import streamlit as st
import boto3
import datetime
import pandas as pd
import plotly.express as px

import utilities as utils
import dependabot.collection as collection
import dependabot.formatting as fmt

env = utils.get_environment_variables()

session = boto3.Session()
s3 = session.client("s3")
secret_manager = session.client("secretsmanager", region_name=env["secret_region"])


last_modified = utils.get_last_modified(
    s3=s3,
    bucket=env["bucket_name"],
    filename="dependabot.json"
)

df_dependabot = collection.load_dependabot(
    _s3=s3,
    bucket=env["bucket_name"]
)

if df_dependabot is None:
    st.error("Error loading Dependabot data. Please check the S3 bucket and file.")
    st.stop()


rest = utils.get_rest_interface(
    _secret_manager=secret_manager,
    secret_name=env["secret_name"],
    org=env["org"],
    client_id=env["client_id"]
)

df_dependabot = fmt.add_repository_information(
    df_dependabot=df_dependabot,
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
     
st.header(":blue-background[Dependabot Analysis 🤖]")

st.write("Alerts open for more than 5 days (Critical), 15 days (High), 60 days (Medium), 90 days (Low).")

if len(df_dependabot) == 0:
    st.write("No dependabot alerts breaking the policy.")
    st.stop()

with st.form("Dependabot Filters"):
    st.subheader(":blue-background[Alert Filters]")

    col1, col2 = st.columns(2)

    start_date = col1.date_input("Start Date", pd.to_datetime(df_dependabot["Creation Date"].min()), key="start_date_dependabot")
    end_date = col2.date_input("End Date", (datetime.datetime.now() + datetime.timedelta(days=1)).date(), key="end_date_dependabot")
    
    st.caption(
        "**Please Note:** The above date range is used to filter the creation date of dependabot alerts."
    )

    severity_list = ["Critical", "High", "Medium", "Low"]
    selected_severities = st.multiselect("Select Severities", severity_list, severity_list)

    col1, col2 = st.columns([0.6, 0.4])

    type_list = ["Public", "Internal", "Private"]
    selected_types = col1.multiselect(
        "Repository Type",
        type_list,
        default=type_list,
        key="repo_type_dependabot"
    )

    archived_list = ["All", "Archived", "Not Archived"]
    archived_status = col2.selectbox(
        "Archived Status",
        archived_list,
        index=0,
        key="archived_status_dependabot"
    )

    st.form_submit_button("Apply Filters", use_container_width=True)

if end_date < start_date:
    st.error("End date cannot be earlier than start date.")
    st.stop()

if len(selected_severities) == 0:
    st.error("Please select at least one severity.")
    st.stop()

if len(selected_types) == 0:
    st.error("Please select at least one repository type.")
    st.stop()

df_dependabot = fmt.filter_dependabot(
    df_dependabot=df_dependabot,
    start_date=start_date,
    end_date=end_date,
    severities_to_exclude=[s for s in severity_list if s not in selected_severities],
    types_to_exclude=[t for t in type_list if t not in selected_types],
    archived_status=archived_status,
)

df_dependabot = fmt.add_dependabot_calculations(
    df_dependabot=df_dependabot,
)

if len(df_dependabot) == 0:
    st.write("No dependabot alerts matching the selected filters.")
    st.stop()

total_dependabot_alerts = df_dependabot["Creation Date"].count()
oldest_dependabot_alert = (datetime.datetime.now() - df_dependabot["Creation Date"].min()).days
worst_severity_dependabot = df_dependabot.loc[df_dependabot["Severity Numeric"].idxmax(), "Severity"]
number_of_repositories = df_dependabot["Repository"].nunique()

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Alerts", total_dependabot_alerts, border=True)
col2.metric("Oldest Alert", oldest_dependabot_alert, border=True)
col3.metric("Worst Severity", worst_severity_dependabot, border=True)
col4.metric("Number of Repositories", number_of_repositories, border=True)

total_critical_alerts = df_dependabot.loc[df_dependabot["Severity"] == "Critical"].shape[0]
total_high_alerts = df_dependabot.loc[df_dependabot["Severity"] == "High"].shape[0]
total_medium_alerts = df_dependabot.loc[df_dependabot["Severity"] == "Medium"].shape[0]
total_low_alerts = df_dependabot.loc[df_dependabot["Severity"] == "Low"].shape[0]

col1, col2, col3, col4 = st.columns(4)

col1.metric("Critical Alerts", total_critical_alerts, border=True)
col2.metric("High Alerts", total_high_alerts, border=True)
col3.metric("Medium Alerts", total_medium_alerts, border=True)
col4.metric("Low Alerts", total_low_alerts, border=True)

df_dependabot_grouped_severity = fmt.group_dependabot_by_severity(
    df_dependabot=df_dependabot,
)

fig = px.pie(
    df_dependabot_grouped_severity.reset_index(),
    values="Count",
    names="Severity",
    title="Total Alerts by Severity",
)

st.plotly_chart(fig)

df_dependabot_grouped_repository = fmt.group_dependabot_by_repository(
    df_dependabot=df_dependabot,
)

selected_repo = st.dataframe(
    df_dependabot_grouped_repository.reset_index(),
    use_container_width=True, 
    hide_index=True,
    column_config={
        "URL": st.column_config.LinkColumn()
    },
    selection_mode="single-row",
    on_select="rerun"
)

if len(selected_repo["selection"]["rows"]) > 0:

    with st.spinner("Loading Repository Information..."):

        selected_repo = selected_repo["selection"]["rows"][0]
        selected_repo = df_dependabot_grouped_repository.reset_index().iloc[selected_repo]["Repository"]
        selected_repo = df_dependabot.loc[df_dependabot["Repository"] == selected_repo].iloc[0]

        repo_name = selected_repo["Repository"]
        repo_type = selected_repo["Repository Type"]
        repo_url = selected_repo["URL"]

        col1, col2 = st.columns([0.8, 0.2])

        col1.subheader(
            f":blue-background[{repo_name} ({repo_type})]"
        )

        col2.write(f"[Go to Repository]({repo_url})")

        col1, col2, col3 = st.columns(3)

        df_selected_dependabot = df_dependabot.loc[df_dependabot["Repository"] == repo_name]

        oldest_alert = (datetime.datetime.now() - df_dependabot.loc[df_dependabot["Repository"] == repo_name, "Creation Date"].min()).days
        worst_severity = df_selected_dependabot.loc[df_selected_dependabot["Severity Numeric"].idxmax(), "Severity"]

        col1.metric("Oldest Alert (Days)", oldest_alert, border=True)
        col2.metric("Worst Severity", worst_severity, border=True)
        col3.metric("Total Alerts", df_selected_dependabot.count()[0], border=True)

        col1, col2, col3, col4 = st.columns(4)

        selected_critical_alerts = df_selected_dependabot.loc[df_selected_dependabot["Severity"] == "Critical"].shape[0]
        selected_high_alerts = df_selected_dependabot.loc[df_selected_dependabot["Severity"] == "High"].shape[0]
        selected_medium_alerts = df_selected_dependabot.loc[df_selected_dependabot["Severity"] == "Medium"].shape[0]
        selected_low_alerts = df_selected_dependabot.loc[df_selected_dependabot["Severity"] == "Low"].shape[0]

        col1.metric("Critical Alerts", selected_critical_alerts, border=True)
        col2.metric("High Alerts", selected_high_alerts, border=True)
        col3.metric("Medium Alerts", selected_medium_alerts, border=True)
        col4.metric("Low Alerts", selected_low_alerts, border=True)

        df_alerts_pie = fmt.group_dependabot_by_severity(
            df_dependabot=df_selected_dependabot,
        )

        fig = px.pie(
            df_alerts_pie.reset_index(),
            values="Count",
            names="Severity",
            title=f"Total Alerts by Severity for {selected_repo['Repository']}",
        )

        st.plotly_chart(fig)
        
else:
    st.caption("Select a repository for more information.")
