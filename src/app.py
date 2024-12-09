import json
import os
from datetime import datetime, timedelta

import boto3
import boto3.resources
import boto3.resources.factory
import boto3.session
import pandas as pd
import plotly.express as px
import streamlit as st
from botocore.exceptions import ClientError

import github_api_toolkit

org = os.getenv("GITHUB_ORG")
client_id = os.getenv("GITHUB_APP_CLIENT_ID")

# AWS Secret Manager Secret Name for the .pem file
secret_name = os.getenv("AWS_SECRET_NAME")
secret_reigon = os.getenv("AWS_DEFAULT_REGION")

account = os.getenv("AWS_ACCOUNT_NAME")
bucket_name = f"{account}-policy-dashboard"

st.set_page_config(
    page_title="GitHub Audit Dashboard",
    page_icon="./src/branding/ONS-symbol_digital.svg",
    layout="wide",
)
st.logo("./src/branding/ONS_Logo_Digital_Colour_Landscape_Bilingual_RGB.svg")

session = boto3.Session()

@st.cache_resource
def get_s3_client() -> boto3.client:
    s3 = session.client("s3")
    return s3

@st.cache_resource
def get_secret_manager_client() -> boto3.client:
    secret_manager = session.client("secretsmanager", secret_reigon)
    return secret_manager

def get_table_from_s3(s3, bucket_name: str, object_name: str) -> pd.DataFrame | str:
    """Gets a JSON file from an S3 bucket and returns it as a Pandas DataFrame.

    Args:
        s3: A boto3 S3 client.
        bucket_name: The name of the S3 bucket.
        object_name: The name of the object in the S3 bucket.

    Returns:
        A Pandas DataFrame containing the data from the JSON file.
        or
        A string containing an error message.
    """
    try:
        response = s3.get_object(Bucket=bucket_name, Key=object_name)
    except ClientError as e:
        return f"An error occurred when getting {object_name} data: {e}"

    json_data = json.loads(response["Body"].read().decode("utf-8"))

    return pd.json_normalize(json_data)


@st.cache_data
def load_data(load_date: datetime.date):
    """Loads the data from the S3 bucket and returns it as a Pandas DataFrame.

    This function is cached using Streamlit's @st.cache_data decorator.

    Args:
        load_date (date): The date and time the data was loaded.
    """
    s3 = get_s3_client()

    df_repositories = get_table_from_s3(s3, bucket_name, "repositories.json")
    df_secret_scanning = get_table_from_s3(s3, bucket_name, "secret_scanning.json")
    df_dependabot = get_table_from_s3(s3, bucket_name, "dependabot.json")

    # Remove Secret from df_secret_scanning
    df_secret_scanning["secret"] = df_secret_scanning["secret"].apply(lambda x: x.split(" - ")[0])

    # Add Repository Type to Dependabot and Secret Scanning
    df_dependabot.insert(1, "Type", "")
    df_secret_scanning.insert(1, "Type", "")

    for i in range(0, len(df_dependabot)):
        df_dependabot.loc[i, "Type"] = df_repositories.loc[df_repositories["name"] == df_dependabot.loc[i, "repo"]].type.values[0]

    for i in range(0, len(df_secret_scanning)):
        df_secret_scanning.loc[i, "Type"] = df_repositories.loc[df_repositories["name"] == df_secret_scanning.loc[i, "repo"]].type.values[0]

    return df_repositories, df_secret_scanning, df_dependabot


@st.cache_data
def load_file(filename: str) -> dict:
    """Loads a JSON file and returns it as a dictionary.

    This function is cached using Streamlit's @st.cache_data decorator.

    Args:
        filename (str): The path of the JSON file to load.

    Returns:
        dict: The JSON file loaded as a dictionary.
    """
    with open(filename) as f:
        file_json = json.load(f)

    return file_json


loading_date = datetime.now()

# Rounds loading_date to the nearest 10 minutes
# This means the cached data will refresh every 10 minutes

loading_date = loading_date.strftime("%Y-%m-%d %H:%M")
loading_date = loading_date[:-1] + "0"

df_repositories, df_secret_scanning, df_dependabot = load_data(loading_date)
rulemap = load_file("rulemap.json")

if type(df_repositories) == str:
    st.error(df_repositories)
    st.stop()

if type(df_secret_scanning) == str:
    st.error(df_secret_scanning)
    st.stop()

if type(df_dependabot) == str:
    st.error(df_dependabot)
    st.stop()


col1, col2 = st.columns([0.8, 0.2])

col1.title(":blue-background[GitHub Audit Dashboard]")

col2.image("./src/branding/ONS_Logo_Digital_Colour_Landscape_Bilingual_RGB.png")


# Tabs for Repository Analysis and SLO Analysis Sections
repository_tab, slo_tab = st.tabs(["Repository Analysis", "SLO Analysis"])

# Repository Analysis Section

with repository_tab:
    st.header(":blue-background[Repository Analysis]")

    # Gets the rules from the repository DataFrame
    rules = df_repositories.columns.to_list()[4:]

    # Cleans the rules to remove the "checklist." prefix
    for i in range(len(rules)):
        rules[i] = rules[i].replace("checklist.", "")

    # Renames the columns of the DataFrame
    df_repositories.columns = ["repository", "repository_type", "url", "created_at"] + rules
    # Uses streamlit's session state to store the selected rules
    # This is so that selected rules persist with other inputs (i.e the preset buttons)
    if "selected_rules" not in st.session_state:
        st.session_state["selected_rules"] = []

        for rule in rulemap:
            st.session_state["selected_rules"].append(rule["name"])

    # Preset Buttons

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Security Preset", use_container_width=True):
            st.session_state["selected_rules"] = []

            for rule in rulemap:
                if rule["is_security_rule"]:
                    st.session_state["selected_rules"].append(rule["name"])

    with col2:
        if st.button("Policy Preset", use_container_width=True):
            st.session_state["selected_rules"] = []

            for rule in rulemap:
                if rule["is_policy_rule"]:
                    st.session_state["selected_rules"].append(rule["name"])

    selected_rules = st.multiselect("Select rules", rules, st.session_state["selected_rules"])

    repository_type = st.selectbox(
        "Repository Type",
        ["all", "public", "private", "internal"],
        key="repos_repo_type",
    )

    # Date input for filtering repositories
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", pd.to_datetime(df_repositories["created_at"].min()), key="start_date_repo")
    with col2:
        end_date = st.date_input("End Date", (datetime.now() + timedelta(days=1)).date(), key="end_date_repo")

    if end_date < start_date:
        st.error("End date cannot be before start date.")
        st.stop()

    # If any rules are selected, populate the rest of the dashboard
    if len(selected_rules) != 0:
        rules_to_exclude = []

        for rule in rules:
            if rule not in selected_rules:
                rules_to_exclude.append(rule)

        # Remove the columns for rules that aren't selected
        df_repositories = df_repositories.drop(columns=rules_to_exclude)

        # Filter the DataFrame by the selected repository type
        if repository_type != "all":
            df_repositories = df_repositories.loc[df_repositories["repository_type"] == repository_type]

        # Filter the DataFrame by the selected date range
        df_repositories["created_at"] = pd.to_datetime(df_repositories["created_at"], errors="coerce").dt.tz_localize(
            None
        )
        df_repositories = df_repositories.loc[
            (df_repositories["created_at"] >= pd.to_datetime(start_date))
            & (df_repositories["created_at"] <= pd.to_datetime(end_date))
        ]

        # Create a new column to check if the repository is compliant or not
        # If any check is True, the repository is non-compliant
        df_repositories["is_compliant"] = df_repositories.any(axis="columns", bool_only=True)
        df_repositories["is_compliant"] = df_repositories["is_compliant"].apply(lambda x: not x)

        # Create a new column to count the number of rules broken
        df_repositories["rules_broken"] = df_repositories[selected_rules].sum(axis="columns")

        # Sort the DataFrame by the number of rules broken and the repository name
        df_repositories = df_repositories.sort_values(by=["rules_broken", "repository"], ascending=[False, True])

        # Rename the columns of the DataFrame
        df_repositories.columns = (
            ["Repository", "Repository Type", "URL", "Created At"] + selected_rules + ["Is Compliant", "Rules Broken"]
        )

        st.subheader(":blue-background[Repository Compliance]")

        # If there are no repositories within the selected time range, display an error message
        if df_repositories.empty:
            st.error("Nothing within that time range.")
            st.stop()

        # Display the rules that are being checked

        with st.expander("See Selected Rules"):
            st.write("Checking for the following rules:")

            col1a, col1b = st.columns(2)
            for i in range(0, len(selected_rules)):
                if i % 2 == 0:
                    col1a.write(f"- {selected_rules[i].replace('_', ' ').title()}")
                else:
                    col1b.write(f"- {selected_rules[i].replace('_', ' ').title()}")

        with st.expander("See Rule Descriptions"):
            st.subheader("Rule Descriptions")
            for rule in rulemap:
                st.write(f"- {rule['name'].replace('_', ' ').title()}: {rule['description']}")

            st.caption(
                "**Note:** All rules are interpreted from ONS' [GitHub Usage Policy](https://officenationalstatistics.sharepoint.com/sites/ONS%5FDDaT%5FCommunities/Software%20Engineering%20Policies/Forms/AllItems.aspx?id=%2Fsites%2FONS%5FDDaT%5FCommunities%2FSoftware%20Engineering%20Policies%2FSoftware%20Engineering%20Policies%2FApproved%2FPDF%2FGitHub%20Usage%20Policy%2Epdf&parent=%2Fsites%2FONS%5FDDaT%5FCommunities%2FSoftware%20Engineering%20Policies%2FSoftware%20Engineering%20Policies%2FApproved%2FPDF)."
            )

        st.divider()

        col1, col2 = st.columns(2)

        # Create a dataframe summarising the compliance of the repositories
        df_compliance = df_repositories["Is Compliant"].value_counts().reset_index()

        df_compliance["Is Compliant"] = df_compliance["Is Compliant"].apply(
            lambda x: "Compliant" if x else "Non-Compliant"
        )

        df_compliance.columns = ["Compliance", "Number of Repositories"]

        # Create a pie chart to show the compliance of the repositories
        with col1:
            fig = px.pie(df_compliance, values="Number of Repositories", names="Compliance")

            st.plotly_chart(fig)

        # Display metrics for the compliance of the repositories
        with col2:
            compliant_repositories = df_compliance.loc[
                df_compliance["Compliance"] == "Compliant", "Number of Repositories"
            ]

            if len(compliant_repositories) == 0:
                compliant_repositories = 0

            noncompliant_repositories = df_compliance.loc[
                df_compliance["Compliance"] == "Non-Compliant", "Number of Repositories"
            ]

            if len(noncompliant_repositories) == 0:
                noncompliant_repositories = 0

            st.metric("Compliant Repositories", compliant_repositories)
            st.metric("Non-Compliant Repositories", noncompliant_repositories)
            avg_rules_broken = df_repositories["Rules Broken"].mean()
            if pd.notna(avg_rules_broken):
                avg_rules_broken = int(avg_rules_broken.round(0))
            else:
                avg_rules_broken = 0

            st.metric(
                "Average Rules Broken",
                avg_rules_broken,
            )

            rule_frequency = df_repositories[selected_rules].sum()
            st.metric(
                "Most Common Rule Broken",
                rule_frequency.idxmax().replace("_", " ").title(),
            )

        # Display the repositories that are non-compliant
        st.subheader(":blue-background[Non-Compliant Repositories]")

        selected_repo = st.dataframe(
            df_repositories[["Repository", "Repository Type", "Rules Broken"]].loc[
                df_repositories["Is Compliant"] == 0
            ],
            on_select="rerun",
            selection_mode=["single-row"],
            use_container_width=True,
            hide_index=True,
        )

        # If a non-compliant repository is selected, display the rules that are broken
        if len(selected_repo["selection"]["rows"]) > 0:

            with st.spinner("Loading Repository Information..."):

                selected_repo = selected_repo["selection"]["rows"][0]

                selected_repo = df_repositories.iloc[selected_repo]

                failed_checks = selected_repo[4:-2].loc[selected_repo[4:-2] == 1]

                # Get Point of Contact List
                secret_manager = get_secret_manager_client()

                secret = secret_manager.get_secret_value(SecretId=secret_name)["SecretString"]

                token = github_api_toolkit.get_token_as_installation(org, secret, client_id)

                ql = github_api_toolkit.github_graphql_interface(token[0])

                points_of_contact_main = ql.get_repository_email_list(org, selected_repo["Repository"], "main")
                points_of_contact_master = ql.get_repository_email_list(org, selected_repo["Repository"], "master")

                points_of_contact = points_of_contact_main + points_of_contact_master

                col1, col2 = st.columns([0.8, 0.2])

                col1.subheader(
                    f":blue-background[{selected_repo["Repository"]} ({selected_repo["Repository Type"].capitalize()})]"
                )
                col2.write(f"[Go to Repository]({selected_repo['URL']})")

                st.subheader("Rules Broken:")

                for check in failed_checks.index:
                    st.write(f"- {check.replace('_', ' ').title()}")

                st.subheader("Point of Contact:")

                if len(points_of_contact) > 0:
                    st.write("The following people are responsible for this repository:")
                    
                    for contact in points_of_contact:
                        st.write(f"- {contact}")
                    
                    st.write("Please contact them to resolve the issues.")
                
                    mail_link = (
                                    f"mailto:{','.join(points_of_contact)}"
                                    f"?subject={selected_repo['Repository']}%20-%20GitHub%20Usage%20Policy%20Recommendations"
                                    f"&body=Hello%2C%0A%0AWe%20have%20identified%20some%20issues%20with%20your%20repository%20-%20{selected_repo['Repository']}%20-%20which%20breach%20parts%20of%20the%20GitHub%20Usage%20Policy.%0A"
                                    "Please%20review%20the%20following%20rules%20and%20take%20the%20necessary%20actions%20to%20resolve%20them.%0A%0A"
                                    f"-%20{',%0A-%20'.join(failed_checks.index).replace('_', '%20').title()}%0A%0A"
                                    "If%20you%20have%20any%20questions%20or%20need%20further%20assistance%2C%20please%20reply%20to%20this%20email.%0A"
                                )

                    st.html(
                        f'<a href="{mail_link}"><button>Email Points of Contact</button></a>'
                    )

                    st.caption("Please Note: The email addresses are separated with a comma following the RFC 6068 standard. To use this link in Microsoft Outlook, you may need to replace the commas with semicolons or enable commas to be used as the recipient seperator.")

                    with st.expander("Instructions for Microsoft Outlook Comma Seperator"):
                        st.write("To enable this feature in Microsoft Outlook, follow these steps:")
                        st.write("1. Navigate to File > Options > Mail.")
                        st.write("2. Under the Send messages section, there is a checkbox for 'Commas can be used to separate multiple message recipients'.")
                        st.write("3. Check this box and click OK.")
                        st.write("Now you can use the mailto link in Microsoft Outlook.")

                        st.write("For more information, please refer to [this](https://www.lifewire.com/commas-to-separate-email-recipients-1173680) article.")

                else:
                    st.write("No point of contact available.")
        else:
            st.caption("Select a repository for more information.")

    # If no rules are selected, prompt the user to select at least one rule
    else:
        st.write("Please select at least one rule.")

# SLO Analysis Section

with slo_tab:
    st.header(":blue-background[SLO Analysis]")

    st.subheader(":blue-background[Secret Scanning Alerts]")
    st.write("Alerts open for more than 5 days.")

    col1, col2 = st.columns(2)
    with col1:
        start_date_slo = st.date_input(
            "Start Date", pd.to_datetime(df_secret_scanning["created_at"].min()), key="start_date_slo"
        )
    with col2:
        end_date_slo = st.date_input("End Date", datetime.now().date() + timedelta(days=1), key="end_date_slo")

    if end_date_slo < start_date_slo:
        st.error("End date cannot be before start date.")
        st.stop()

    # Filter the secret scanning alerts by the selected date range
    df_secret_scanning["created_at"] = pd.to_datetime(df_secret_scanning["created_at"], errors="coerce").dt.tz_localize(
        None
    )
    df_secret_scanning = df_secret_scanning.loc[
        (df_secret_scanning["created_at"] >= pd.to_datetime(start_date_slo))
        & (df_secret_scanning["created_at"] <= pd.to_datetime(end_date_slo))
    ]

    # Filter the dependabot alerts by the selected date range
    df_dependabot["created_at"] = pd.to_datetime(df_dependabot["created_at"], errors="coerce").dt.tz_localize(None)
    df_dependabot = df_dependabot.loc[
        (df_dependabot["created_at"] >= pd.to_datetime(start_date_slo))
        & (df_dependabot["created_at"] <= pd.to_datetime(end_date_slo))
    ]

    # Rename the columns of the DataFrame
    df_secret_scanning.columns = ["Repository Name", "Type", "Created At", "Secret Type", "Link"]

    # Group the DataFrame by the repository name and the type
    df_secret_scanning_grouped = df_secret_scanning.groupby(["Repository Name", "Type"]).count().reset_index()

    # Rename the columns of the grouped DataFrame
    df_secret_scanning_grouped.columns = [
        "Repository Name",
        "Type",
        "Created At",
        "Number of Secrets",
        "Link",
    ]

    col1, col2 = st.columns([0.8, 0.2])

    with col1:
        selected_secret = st.dataframe(
            df_secret_scanning_grouped[["Repository Name", "Type", "Number of Secrets"]],
            use_container_width=True,
            on_select="rerun",
            selection_mode=["single-row"],
            hide_index=True,
        )

    with col2:
        st.metric("Total Alerts", df_secret_scanning_grouped["Number of Secrets"].sum())

    # If an alert is selected, display the secrets that are open
    if len(selected_secret["selection"]["rows"]) > 0:
        selected_secret = selected_secret["selection"]["rows"][0]

        selected_secret = df_secret_scanning_grouped.iloc[selected_secret]

        st.subheader(f":blue-background[{selected_secret['Repository Name']} ({selected_secret['Type']})]")

        st.dataframe(
            df_secret_scanning.loc[df_secret_scanning["Repository Name"] == selected_secret["Repository Name"]][
                [
                    "Repository Name",
                    "Type",
                    "Created At",
                    "Secret Type",
                    "Link"
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={"Link": st.column_config.LinkColumn("Link", display_text="Go to Alert")},
        )
    else:
        st.caption("Select a repository for more information.")

    st.divider()

    st.subheader(":blue-background[Dependabot Alerts]")
    # Rename the columns of the DataFrame
    df_dependabot.columns = [
        "Repository Name",
        "Type",
        "Created At",
        "Dependency",
        "Advisory",
        "Severity",
        "Days Open",
        "Link",
    ]
    max_days_open = 0 if df_dependabot["Days Open"].empty else int(df_dependabot["Days Open"].max())

    if max_days_open == 0:
        st.error("There are no alerts within the selected date range.")
        st.stop()
    st.write("Alerts open for more than 5 days (Critical), 15 days (High), 60 days (Medium), 90 days (Low).")

    col1, col2 = st.columns([0.7, 0.3])

    severity = col1.multiselect(
        "Alert Severity",
        ["critical", "high", "medium", "low"],
        ["critical", "high", "medium", "low"],
    )
    repo_type = col2.selectbox(
        "Repository Type",
        ["all", "public", "private", "internal"],
        key="dependabot_repo_type",
    )

    minimum_days = st.slider("Minimum Days Open", 0, max_days_open, 0)

    # If any severity levels are selected, populate the rest of the dashboard
    if len(severity) > 0:
        # Filter the DataFrame by the selected severity levels and the minimum days open
        df_dependabot = df_dependabot.loc[
            df_dependabot["Severity"].isin(severity) & (df_dependabot["Days Open"] >= minimum_days)
        ]

        # Filter the DataFrame by the selected repository type
        if repo_type != "all":
            df_dependabot = df_dependabot.loc[df_dependabot["Type"] == repo_type]

        # Map the severity to a weight for sorting
        df_dependabot["Severity Weight"] = df_dependabot["Severity"].map(
            {"critical": 4, "high": 3, "medium": 2, "low": 1}
        )

        # Group the DataFrame by the repository name and the type
        df_dependabot_grouped = (
            df_dependabot.groupby(["Repository Name", "Type"])
            .agg({"Dependency": "count", "Severity Weight": "max", "Days Open": "max"})
            .reset_index()
        )

        # Create a new column to map the severity weight to a severity level for the grouped data
        df_dependabot_grouped["Severity"] = df_dependabot_grouped["Severity Weight"].map(
            {4: "Critical", 3: "High", 2: "Medium", 1: "Low"}
        )

        # Rename the columns of the grouped DataFrame
        df_dependabot_grouped.columns = [
            "Repository Name",
            "Type",
            "Number of Alerts",
            "Severity Weight",
            "Max Days Open",
            "Max Severity",
        ]

        # Sort the grouped DataFrame by the severity weight and the days open
        df_dependabot_grouped.sort_values(
            by=["Severity Weight", "Max Days Open"],
            ascending=[False, False],
            inplace=True,
        )

        col1, col2 = st.columns([0.7, 0.3])

        with col1:
            # Create a dataframe summarising the alerts by severity
            df_dependabot_severity_grouped = (
                df_dependabot.groupby("Severity").count().reset_index()[["Severity", "Repository Name"]]
            )
            df_dependabot_severity_grouped.columns = ["Severity", "Number of Alerts"]

            # Create a pie chart to show the alerts by severity
            fig = px.pie(
                df_dependabot_severity_grouped,
                names="Severity",
                values="Number of Alerts",
                title="Number of Alerts by Severity",
            )

            st.plotly_chart(fig)

        with col2:
            st.metric("Total Alerts", df_dependabot_grouped["Number of Alerts"].sum())
            st.metric(
                "Average Days Open",
                int(df_dependabot_grouped["Max Days Open"].mean().round(0)),
            )

            st.metric(
                "Number of Repositories",
                df_dependabot_grouped["Repository Name"].count(),
            )
            st.metric(
                "Avg. Alerts per Repository",
                int(df_dependabot_grouped["Number of Alerts"].mean().round(0)),
            )

        selected_repo = st.dataframe(
            df_dependabot_grouped[
                [
                    "Repository Name",
                    "Type",
                    "Number of Alerts",
                    "Max Severity",
                    "Max Days Open",
                ]
            ],
            use_container_width=True,
            on_select="rerun",
            selection_mode=["single-row"],
            hide_index=True,
        )

        # If a repository is selected, display the alerts that are open for that repository
        if len(selected_repo["selection"]["rows"]) > 0:
            selected_repo = selected_repo["selection"]["rows"][0]

            selected_repo = df_dependabot_grouped.iloc[selected_repo]

            st.subheader(f":blue-background[{selected_repo['Repository Name']} ({selected_repo['Type']})]")

            st.dataframe(
                # Get the alerts for the selected repository, sort by severity weight and days open and display the columns
                df_dependabot.loc[df_dependabot["Repository Name"] == selected_repo["Repository Name"]].sort_values(
                    by=["Severity Weight", "Days Open"], ascending=[False, False]
                )[
                    [
                        "Repository Name",
                        "Dependency",
                        # "Advisory",
                        "Severity",
                        "Days Open",
                        "Link",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
                column_config={"Link": st.column_config.LinkColumn("Link", display_text="Go to Alert")},
            )

        else:
            st.caption("Select a repository for more information.")

    # If no severity levels are selected, prompt the user to select at least one severity level
    else:
        st.write("Please select at least one severity level.")
