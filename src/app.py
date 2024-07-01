import boto3.resources
import boto3.resources.factory
import boto3.session
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

import json

import boto3
from botocore.exceptions import ClientError

# st.set_page_config(layout="wide")

def get_table_from_s3(s3, bucket_name: str, object_name: str, filename: str) -> pd.DataFrame | str:
    try:
        s3.download_file(bucket_name, object_name, filename)
    except ClientError as e:
        return (f"An error occurred when getting {filename} data: {e}")
    
    with open(filename, "r") as f:
        file_json = json.load(f)

    return pd.json_normalize(file_json)

@st.cache_data
def load_data():
    bucket_name = "sdp-sandbox-github-audit-dashboard"

    session = boto3.Session(profile_name="ons_sdp_sandbox")
    s3 = session.client("s3")

    df_repositories = get_table_from_s3(s3, bucket_name, "repositories.json", "repositories.json")
    df_secret_scanning = get_table_from_s3(s3, bucket_name, "secret_scanning.json", "secret_scanning.json")
    df_dependabot = get_table_from_s3(s3, bucket_name, "dependabot.json", "dependabot.json")

    return df_repositories, df_secret_scanning, df_dependabot

df_repositories, df_secret_scanning, df_dependabot = load_data()


# Title of the dashboard
st.title("GitHub Audit Dashboard")

repository_tab, slo_tab = st.tabs(["Repository Analysis", "SLO Analysis"])

with repository_tab:
    st.header("Repository Analysis")
    
    rules = df_repositories.columns.to_list()[3:]

    for i in range(len(rules)):
        rules[i] = rules[i].replace("checklist.", "")

    df_repositories.columns = ["repository", "repository_type", "url"] + rules

    if "selected_rules" not in st.session_state:
        st.session_state["selected_rules"] = rules

    # Preset Buttons
    
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Security Preset", use_container_width=True):
            st.session_state["selected_rules"] = rules[:3] + [rules[6]] + [rules[8]]

    with col2:
        if st.button("Policy Preset", use_container_width=True):
            st.session_state["selected_rules"] = rules[0:6] + [rules[8]]

    selected_rules = st.multiselect("Select rules", rules, st.session_state["selected_rules"])

    if len(selected_rules) != 0:
        rules_to_exclude = []

        for rule in rules:
            if rule not in selected_rules:
                rules_to_exclude.append(rule)

        df_repositories = df_repositories.drop(columns=rules_to_exclude)

        df_repositories["is_compliant"] = df_repositories.any(axis="columns", bool_only=True)
        df_repositories["is_compliant"] = df_repositories["is_compliant"].apply(lambda x: not x)

        df_repositories["rules_broken"] = df_repositories[selected_rules].sum(axis="columns")

        df_repositories = df_repositories.sort_values(by=["rules_broken", "repository"], ascending=[False, True])

        st.subheader("Repository Compliance")

        st.write("Checking for the following rules:")

        col1, col2 = st.columns(2)

        for i in range(0, len(selected_rules)):
            if i % 2 == 0:
                with col1:
                    st.write(f"- {selected_rules[i].replace('_', ' ')}")
            else:
                with col2:
                    st.write(f"- {selected_rules[i].replace('_', ' ')}")

        st.divider()

        col1, col2 = st.columns(2)

        df_compliance = df_repositories["is_compliant"].value_counts().reset_index()

        df_compliance["is_compliant"] = df_compliance["is_compliant"].apply(lambda x: "Compliant" if x else "Non-Compliant")

        df_compliance.columns = ["Compliance", "Number of Repositories"]

        with col1:
            fig = px.pie(df_compliance, values="Number of Repositories", names="Compliance")

            st.plotly_chart(fig)

        with col2:
            st.metric("Compliant Repositories", df_compliance.loc[df_compliance["Compliance"] == "Compliant", "Number of Repositories"])
            st.metric("Non-Compliant Repositories", df_compliance.loc[df_compliance["Compliance"] == "Non-Compliant", "Number of Repositories"])
            st.metric("Average Rules Broken", int(df_repositories["rules_broken"].mean().round(0)))

            rule_frequency = df_repositories[selected_rules].sum()
            st.metric("Most Common Rule Broken", rule_frequency.idxmax().replace("_", " "))

        st.subheader("Non-Compliant Repositories")

        selected_repo = st.dataframe(
            df_repositories[["repository", "repository_type", "rules_broken"]].loc[df_repositories["is_compliant"] == 0],
            on_select="rerun",
            selection_mode=["single-row"],
            use_container_width=True,
            hide_index=True
        )

        if len(selected_repo["selection"]["rows"]) > 0:
            selected_repo = selected_repo["selection"]["rows"][0]

            selected_repo = df_repositories.iloc[selected_repo]

            failed_checks = selected_repo[3:-2].loc[selected_repo[3:-2] == 1]

            col1, col2 = st.columns([0.8, 0.2])

            col1.subheader(f"{selected_repo["repository"]} ({selected_repo["repository_type"].capitalize()})")
            col2.write(f"[Go to Repository]({selected_repo['url']})")

            st.subheader("Rules Broken:")      

            for check in failed_checks.index:
                st.write(f"- {check.replace('_', ' ')}")  

    else:
        st.write("Please select at least one rule.")