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
    page_title="GitHub Policy Dashboard",
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


@st.cache_data
def load_repositories(_s3, load_date: datetime.date) -> pd.DataFrame | str:
    """Loads the repositories data from the S3 bucket and returns it as a Pandas DataFrame.

    Args:
        s3 (session.client): An S3 client.
        load_date (datetime.date): The date and time the data was loaded (this is for caching purposes).

    Returns:
        pd.DataFrame | str: The repositories data as a Pandas DataFrame. If an error occurs, a string containing the error message is returned.
    """

    # Get repositories.json from S3
    try:
        response = s3.get_object(Bucket=bucket_name, Key="repositories.json")
    except ClientError as e:
        return f"An error occurred when getting repositories data: {e}"
    
    # Convert the JSON data to a Pandas DataFrame
    json_data = json.loads(response["Body"].read().decode("utf-8"))

    df_repositories = pd.json_normalize(json_data)

    return df_repositories
    

@st.cache_data
def load_secret_scanning(_s3, load_date: datetime.date) -> pd.DataFrame | str:
    """Loads the secret scanning data from the S3 bucket and returns it as a Pandas DataFrame.

    Args:
        s3 (session.client): An S3 client.
        load_date (datetime.date): The date and time the data was loaded (this is for caching purposes).

    Returns:
        pd.DataFrame | str: The secret scanning data as a Pandas DataFrame. If an error occurs, a string containing the error message is returned.
    """

    # Get secret_scanning.json from S3
    try:
        response = s3.get_object(Bucket=bucket_name, Key="secret_scanning.json")
    except ClientError as e:
        return 0, 0, f"An error occurred when getting secret scanning data: {e}"
    
    # Convert the response to a JSON object
    json_data = json.loads(response["Body"].read().decode("utf-8"))

    # Extract key information from the JSON object (total alerts, oldest alert, and alerts for each repository)
    total_alerts = json_data.get("total_alerts", 0)
    oldest_alert = json_data.get("oldest_alert", 0)

    repositories_list = json_data.get("repositories", [])

    rows = []

    for repository in repositories_list:
        repository_name = repository
        repository_oldest_alert = repositories_list[repository].get("oldest_alert", 0)
        repository_total_alerts = repositories_list[repository].get("alert_count", 0)
        repository_link = repositories_list[repository].get("url", "N/A")

        rows.append(
            {
                "Name": repository_name,
                "Oldest Alert": repository_oldest_alert,
                "Total Alerts": repository_total_alerts,
                "Link": repository_link
            }
        )

    df_secret_scanning = pd.DataFrame(rows)

    return total_alerts, oldest_alert, df_secret_scanning


@st.cache_data
def load_dependabot(_s3, load_date: datetime.date) -> pd.DataFrame | str:
    """Loads the dependabot data from the S3 bucket and returns it as a Pandas DataFrame.

    Args:
        _s3 (session.client): An S3 client.
        load_date (datetime.date): The date and time the data was loaded (this is for caching purposes).

    Returns:
        pd.DataFrame | str: The dependabot data as a Pandas DataFrame. If an error occurs, a string containing the error message is returned.
    """

    # Get dependabot.json from S3
    try:
        response = s3.get_object(Bucket=bucket_name, Key="dependabot.json")
    except ClientError as e:
        return "N/A", 0, "N/A", f"An error occurred when getting dependabot data: {e}"
    
    # Convert the response to a JSON object
    json_data = json.loads(response["Body"].read().decode("utf-8"))

    # Extract key information from the JSON object (total alerts, oldest alert, worst_severity, and alerts for each repository)

    oldest_alert = json_data.get("oldest_alert", 0)
    worst_severity = json_data.get("worst_severity", "N/A")

    df_total_alerts = pd.json_normalize(json_data.get("total_alerts", []))

    rows = []

    for repository in json_data.get("repositories", []):
        repository_name = repository
        repository_oldest_alert = json_data["repositories"][repository].get("oldest_alert", 0)
        repository_worst_severity = json_data["repositories"][repository].get("worst_severity", "N/A")
        repository_critical_alerts = json_data["repositories"][repository]["alerts"].get("critical", 0)
        repository_high_alerts = json_data["repositories"][repository]["alerts"].get("high", 0)
        repository_medium_alerts = json_data["repositories"][repository]["alerts"].get("medium", 0)
        repository_low_alerts = json_data["repositories"][repository]["alerts"].get("low", 0)
        repository_link = json_data["repositories"][repository].get("url", "N/A")

        rows.append(
            {
                "Name": repository_name,
                "Oldest Alert": repository_oldest_alert,
                "Worst Severity": repository_worst_severity,
                "Critical Alerts": repository_critical_alerts,
                "High Alerts": repository_high_alerts,
                "Medium Alerts": repository_medium_alerts,
                "Low Alerts": repository_low_alerts,
                "Link": repository_link
            }
        )

    df_dependabot = pd.DataFrame(rows)

    return df_total_alerts, oldest_alert, worst_severity, df_dependabot


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

s3 = get_s3_client()

df_repositories = load_repositories(s3, loading_date)
total_secret_alerts, oldest_secret_alert, df_secret_scanning = load_secret_scanning(s3, loading_date)
df_total_dependabot_alerts, oldest_dependabot_alert, worst_severity_dependabot, df_dependabot = load_dependabot(s3, loading_date)

st.dataframe(df_secret_scanning)
st.dataframe(df_dependabot)
st.dataframe(df_total_dependabot_alerts)

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

col1.title(":blue-background[GitHub Policy Dashboard]")

col2.image("./src/branding/ONS_Logo_Digital_Colour_Landscape_Bilingual_RGB.png")


# Tabs for Repository Analysis and SLO Analysis Sections
repository_tab, secret_tab, dependabot_tab = st.tabs(["Repository Analysis", "Secret Scanning Analysis", "Dependabot Analysis"])

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

    st.write("Rule Presets:")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Select Security Rules", use_container_width=True):
            st.session_state["selected_rules"] = []

            for rule in rulemap:
                if rule["is_security_rule"]:
                    st.session_state["selected_rules"].append(rule["name"])

    with col2:
        if st.button("Select Policy Rules", use_container_width=True):
            st.session_state["selected_rules"] = []

            for rule in rulemap:
                if rule["is_policy_rule"]:
                    st.session_state["selected_rules"].append(rule["name"])

    with col3:
        if st.button("Select All Rules", use_container_width=True):
            st.session_state["selected_rules"] = []

            for rule in rulemap:
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
                                    f"?subject=ONS%20GitHub%20Usage%20Policy%20Compliance%20-%20{selected_repo['Repository']}"
                                    "&body=Hello%2C%0A%0A"
                                    f"We%20have%20identified%20some%20issues%20with%20your%20repository%20%22{selected_repo['Repository']}%22%20which%20is%20not%20currently%20compliant%20with%20ONS%27%20GitHub%20Usage%20Policy.%0A%0A"
                                    "Please%20check%20your%20repositories%20for%20the%20following%20issues%20and%20take%20the%20appropriate%20action%20to%20resolve%20them.%0A%0A"
                                    f"-%20{',%0A-%20'.join(failed_checks.index).replace('_', '%20').title().replace("Pirr", "PIRR")}%0A%0A"
                                    "If%20you%20have%20any%20questions%20or%20need%20further%20assistance%2C%20please%20get%20in%20touch.%0A%0A"
                                    "Many thanks%2C%0A%0A"
                                    "Name"
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

# Secret Scanning Analysis Section

with secret_tab:
    st.header(":blue-background[Secret Scanning Analysis]")
    st.write("Alerts open for more than 5 days.")

    col1, col2, col3 = st.columns([0.3, 0.3, 0.4])

    col1.metric("Total Alerts", total_secret_alerts)
    col2.metric("Oldest Alert", oldest_secret_alert)

    # Metric with repository with most alerts
    col3.metric("Repository with Most Alerts", df_secret_scanning["Name"].iloc[df_secret_scanning["Total Alerts"].idxmax()])

    # Pie chart showing the number of alerts by repository

    fig = px.pie(
        df_secret_scanning,
        values="Total Alerts",
        names="Name",
        title="Total Alerts by Repository",
    )

    st.plotly_chart(fig)

    st.dataframe(
        df_secret_scanning, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Link": st.column_config.LinkColumn()
        }
    )

# Dependabot Analysis Section

with dependabot_tab:
    st.header(":blue-background[Dependabot Analysis]")
    st.write("Alerts open for more than 5 days (Critical), 15 days (High), 60 days (Medium), 90 days (Low).")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Alerts", df_total_dependabot_alerts.iloc[0].sum(axis=0))
    col2.metric("Oldest Alert", oldest_dependabot_alert)
    col3.metric("Worst Severity", worst_severity_dependabot)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Critical Alerts", df_total_dependabot_alerts["critical"].sum())
    col2.metric("High Alerts", df_total_dependabot_alerts["high"].sum())
    col3.metric("Medium Alerts", df_total_dependabot_alerts["medium"].sum())
    col4.metric("Low Alerts", df_total_dependabot_alerts["low"].sum())

    # Pie chart showing the number of alerts by severity

    # Pivot data to become severity | count
    df_dependabot_alerts_pivot = df_total_dependabot_alerts.melt(var_name="Severity", value_name="Count")

    fig = px.pie(
        df_dependabot_alerts_pivot,
        values="Count",
        names="Severity",
        title="Total Alerts by Severity",
    )

    st.plotly_chart(fig)

    df_dependabot["Total Alerts"] = df_dependabot["Critical Alerts"] + df_dependabot["High Alerts"] + df_dependabot["Medium Alerts"] + df_dependabot["Low Alerts"]

    # Hide the columns that are not needed
    df_dependabot_filtered = df_dependabot.drop(columns=["Critical Alerts", "High Alerts", "Medium Alerts", "Low Alerts"])

    selected_repo = st.dataframe(
        df_dependabot_filtered,
        column_order=["Name", "Oldest Alert", "Worst Severity", "Total Alerts", "Link"],
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Link": st.column_config.LinkColumn()
        },
        selection_mode="single-row",
        on_select="rerun"
    )

    if len(selected_repo["selection"]["rows"]) > 0:

        with st.spinner("Loading Repository Information..."):

            selected_repo = selected_repo["selection"]["rows"][0]

            selected_repo = df_dependabot.iloc[selected_repo]

            col1, col2 = st.columns([0.8, 0.2])

            col1.subheader(
                f":blue-background[{selected_repo['Name']}]"
            )
            col2.write(f"[Go to Repository]({selected_repo['Link']})")

            col1, col2, col3 = st.columns(3)

            col1.metric("Oldest Alert", selected_repo["Oldest Alert"])
            col2.metric("Worst Severity", selected_repo["Worst Severity"])
            col3.metric("Total Alerts", selected_repo["Total Alerts"])

            col1, col2, col3, col4 = st.columns(4)

            col1.metric("Critical Alerts", selected_repo["Critical Alerts"])
            col2.metric("High Alerts", selected_repo["High Alerts"])
            col3.metric("Medium Alerts", selected_repo["Medium Alerts"])
            col4.metric("Low Alerts", selected_repo["Low Alerts"])

            df_alerts_pie = df_dependabot.loc[df_dependabot["Name"] == selected_repo["Name"]].drop(columns=["Name", "Oldest Alert", "Worst Severity", "Link", "Total Alerts"])

            fig = px.pie(
                df_alerts_pie,
                values=df_alerts_pie.values[0],
                names=df_alerts_pie.columns,
                title=f"Total Alerts by Severity for {selected_repo['Name']}",
            )

            st.plotly_chart(fig)
            
    else:
        st.caption("Select a repository for more information.")