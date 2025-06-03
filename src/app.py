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

def get_last_modified(client: boto3.client, file_names: list[str]) -> dict:
    """
    This function retrieves and returns the `LastModified` value for the specified set of files
    in a given S3 bucket.

    Args:
        client (boto3.client): An initialized boto3 S3 client.
        file_names: A list of string values.

    Returns:
        dict: A dictionary containing formatted datetime values of the last modification date for each file.
              The keys are the base file names (without extension) and the values are the formatted datetime strings.
    
    Raises:
        Exception: Propagates any exceptions not caught by the individual file processing.
    """

    last_modified_timestamps = {}

    for file in file_names:
        try:
            response = client.head_object(Bucket=bucket_name, Key=file)
            last_modified = response["LastModified"]
            file_key = file.split(".")[0]
            last_modified_timestamps[file_key] = last_modified.strftime('%Y-%m-%d @ %H:%M')
        except Exception as e:
            # Handle the error for a specific file here.
            print(f"Error processing file {file}: {e}")

    return last_modified_timestamps

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

    # Update repository_type to be title case
    df_repositories["type"] = df_repositories["type"].str.title()

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

    df_secret_scanning = pd.json_normalize(json_data)

    # Rename the columns to be more readable
    df_secret_scanning.columns = [
        "Repository",
        "Creation Date",
        "URL",
    ]

    # Add Alert Age (Days) to the DataFrame
    df_secret_scanning["Alert Age (Days)"] = datetime.now() - pd.to_datetime(df_secret_scanning["Creation Date"]).dt.tz_localize(None)
    df_secret_scanning["Alert Age (Days)"] = df_secret_scanning["Alert Age (Days)"].dt.days
    df_secret_scanning["Alert Age (Days)"] = df_secret_scanning["Alert Age (Days)"].astype(int)

    return df_secret_scanning


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

    df_dependabot = pd.json_normalize(json_data)

    # Rename the columns to be more readable
    df_dependabot.columns = [
        "Repository",
        "URL",
        "Creation Date",
        "Severity",
    ]

    # Add Alert Age (Days) to the DataFrame
    df_dependabot["Alert Age (Days)"] = datetime.now() - pd.to_datetime(df_dependabot["Creation Date"]).dt.tz_localize(None)
    df_dependabot["Alert Age (Days)"] = df_dependabot["Alert Age (Days)"].dt.days
    df_dependabot["Alert Age (Days)"] = df_dependabot["Alert Age (Days)"].astype(int)

    # Title Case the Severity column
    df_dependabot["Severity"] = df_dependabot["Severity"].str.title()

    return df_dependabot

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

file_names = ["repositories.json", "secret_scanning.json", "dependabot.json"]
last_modified_values = get_last_modified(s3, file_names)

df_repositories = load_repositories(s3, loading_date)
df_secret_scanning = load_secret_scanning(s3, loading_date)
df_dependabot = load_dependabot(s3, loading_date)

# Add Repository Type to dependabot data using the repository data
for repository in df_dependabot["Repository"]:
    repository_type = df_repositories.loc[df_repositories["name"] == repository, "type"].values

    if len(repository_type) > 0:
        df_dependabot.loc[df_dependabot["Repository"] == repository, "Type"] = repository_type[0].title()
    else:
        # If the repository is not found in the repositories data, the alert is for an archived repository
        df_dependabot.loc[df_dependabot["Repository"] == repository, "Type"] = "Archived"

# Add Repository Type to secret scanning data using the repository data
for repository in df_secret_scanning["Repository"]:
    repository_type = df_repositories.loc[df_repositories["name"] == repository, "type"].values

    if len(repository_type) > 0:
        df_secret_scanning.loc[df_secret_scanning["Repository"] == repository, "Type"] = repository_type[0].title()
    else:
        # If the repository is not found in the repositories data, the alert is for an archived repository
        df_secret_scanning.loc[df_secret_scanning["Repository"] == repository, "Type"] = "Archived"


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
    rep_last_modified = last_modified_values["repositories"]
    col1, col2 =st.columns([3,1])

    with col1:
        st.header(":blue-background[Repository Analysis]")
    
    with col2:
        st.write(f"#### Last Updated: {rep_last_modified}")


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
        ["All", "Public", "Private", "Internal"],
        key="repos_repo_type",
    )

    # Date input for filtering repositories
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", pd.to_datetime(df_repositories["created_at"].min()), key="start_date_repo")
    with col2:
        end_date = st.date_input("End Date", (datetime.now() + timedelta(days=1)).date(), key="end_date_repo")

    st.caption(
        "**Please Note:** The above date range is used to filter the creation date of repositories."
    )

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
        if repository_type != "All":
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
                rule_name = selected_rules[i].replace("_", " ").title()

                if i % 2 == 0:
                    col1a.write(f"- {rule_name}")
                else:
                    col1b.write(f"- {rule_name}")

        with st.expander("See Rule Descriptions"):
            st.subheader("Rule Descriptions")
            for rule in rulemap:
                rule_name = rule['name'].replace('_', ' ').title()

                st.write(f"- **{rule_name}:** {rule['description']}")

            st.caption(
                "**Note:** All rules are interpreted from ONS' [GitHub Usage Policy](https://officenationalstatistics.sharepoint.com/sites/ONS%5FDDaT%5FCommunities/Software%20Engineering%20Policies/Forms/AllItems.aspx?id=%2Fsites%2FONS%5FDDaT%5FCommunities%2FSoftware%20Engineering%20Policies%2FSoftware%20Engineering%20Policies%2FApproved%2FPDF%2FGitHub%20Usage%20Policy%2Epdf&parent=%2Fsites%2FONS%5FDDaT%5FCommunities%2FSoftware%20Engineering%20Policies%2FSoftware%20Engineering%20Policies%2FApproved%2FPDF)."
            )

        st.divider()

        st.subheader(":blue-background[Rule Notes]")

        notes_list = []

        for i in range(0, len(selected_rules)):
            # Get the rule from the rulemap
            rule = next((
                item for item in rulemap if item["name"] == selected_rules[i]
            ), None)

            if rule["note"]:
                rule_name = rule["name"].replace('_', ' ').title()

                notes_list.append(
                    f"- **{rule_name}:** {rule["note"]}"
                )

        if len(notes_list) > 0:
            col1a, col1b = st.columns(2)
            
            for i in range(0, len(notes_list)):
                if i % 2 == 0:
                    col1a.write(notes_list[i])
                else:
                    col1b.write(notes_list[i])
                

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
    col1, col2 =st.columns([3,1])
    secrets_tab = last_modified_values["secret_scanning"]

    with col1:
         st.header(":blue-background[Secret Scanning Analysis]")
    
    with col2:
        st.write(f"#### Last Updated: {secrets_tab}")

    st.write("Alerts open for more than 5 days.")

    if len(df_secret_scanning) == 0:
        st.write("No secret scanning alerts breaking the policy.")
    else:
        # Data filters
        col1, col2, col3 = st.columns([0.4, 0.4, 0.2])

        ## Date Range Filter
        start_date = col1.date_input("Start Date", pd.to_datetime(df_secret_scanning["Creation Date"].min()), key="start_date_secrets")
        end_date = col2.date_input("End Date", (datetime.now() + timedelta(days=1)).date(), key="end_date_secrets")

        st.caption(
            "**Please Note:** The above date range is used to filter the creation date of secret scanning alerts."
        )

        if end_date < start_date:
            st.error("End date cannot be before start date.")
            st.stop()

        df_secret_scanning["Creation Date"] = pd.to_datetime(df_secret_scanning["Creation Date"], errors="coerce").dt.tz_localize(None)
        df_secret_scanning = df_secret_scanning.loc[
            (df_secret_scanning["Creation Date"] >= pd.to_datetime(start_date))
            & (df_secret_scanning["Creation Date"] <= pd.to_datetime(end_date))
        ]

        ## Repository Type Filter
        type_list = ["All", "All (Except Archived)", "Public", "Private", "Internal", "Archived"]
        selected_type = col3.selectbox("Select Repository Type", type_list)

        if selected_type == "All (Except Archived)":
            df_secret_scanning = df_secret_scanning.loc[df_secret_scanning["Type"] != "Archived"]
        elif selected_type != "All":
            df_secret_scanning = df_secret_scanning.loc[df_secret_scanning["Type"] == selected_type]

        if len(df_secret_scanning) == 0:
            st.write("No secret scanning alerts for the selected parameters.")
        else:
            total_secret_alerts = df_secret_scanning["Alert Age (Days)"].count()
            oldest_alert = df_secret_scanning["Alert Age (Days)"].max()
            total_repositories = df_secret_scanning["Repository"].nunique()
            alerts_per_repository = total_secret_alerts / total_repositories

            col1, col2, col3, col4 = st.columns(4)

            col1.metric("Total Alerts", total_secret_alerts, border=True)
            col2.metric("Oldest Alert", oldest_alert, border=True)
            col3.metric("Number of Repositories", total_repositories, border=True)
            col4.metric("Average Alerts per Repository", round(alerts_per_repository, 2), border=True)

            df_grouped_secrets = df_secret_scanning[["Repository", "Creation Date"]].groupby("Repository").count()
            df_grouped_secrets.columns = ["Total Alerts"]

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

# Dependabot Analysis Section


with dependabot_tab:
    col1, col2 =st.columns([3,1])
    dependabot = last_modified_values["dependabot"]

    with col1:
        st.header(":blue-background[Dependabot Analysis]")

    with col2:
        st.write(f"#### Last Updated: {dependabot}")

    st.write("Alerts open for more than 5 days (Critical), 15 days (High), 60 days (Medium), 90 days (Low).")

    if len(df_dependabot) == 0:
        st.write("No dependabot alerts breaking the policy.")
    else:

        # Data filters

        col1, col2 = st.columns(2)

        ## Date Range Filter

        start_date = col1.date_input("Start Date", pd.to_datetime(df_dependabot["Creation Date"].min()), key="start_date_dependabot")
        end_date = col2.date_input("End Date", (datetime.now() + timedelta(days=1)).date(), key="end_date_dependabot")
        st.caption(
            "**Please Note:** The above date range is used to filter the creation date of dependabot alerts."
        )
        if end_date < start_date:
            st.error("End date cannot be before start date.")
            st.stop()

        df_dependabot["Creation Date"] = pd.to_datetime(df_dependabot["Creation Date"], errors="coerce").dt.tz_localize(None)
        df_dependabot = df_dependabot.loc[
            (df_dependabot["Creation Date"] >= pd.to_datetime(start_date))
            & (df_dependabot["Creation Date"] <= pd.to_datetime(end_date))
        ]

        col1, col2 = st.columns([0.7, 0.3])

        ## Severity Filter

        severity_list = ["Critical", "High", "Medium", "Low"]

        selected_severities = col1.multiselect("Select Severities", severity_list, severity_list)

        if len(selected_severities) == 0:
            st.info("Please select at least one severity to see metrics.")
            st.stop()

        severities_to_exclude = []

        for severity in severity_list:
            if severity not in selected_severities:
                severities_to_exclude.append(severity)

        # Filter the DataFrame by the selected severities
        for severity in severities_to_exclude:
            df_dependabot = df_dependabot.drop(df_dependabot[df_dependabot["Severity"] == severity].index)

        ## Repository Type Filter

        type_list = ["All", "Public", "Private", "Internal", "Archived"]

        selected_type = col2.selectbox("Select Repository Type", type_list, key="dependabot_repo_type")

        if selected_type != "All":
            df_dependabot = df_dependabot.loc[df_dependabot["Type"] == selected_type]

        if len(df_dependabot) == 0:
            st.write("No dependabot alerts for the selected parameters.")
        else:

            total_dependabot_alerts = df_dependabot["Creation Date"].count()
            oldest_dependabot_alert = (datetime.now() - df_dependabot["Creation Date"].min()).days

            # Map the severity to a numeric value for sorting
            severity_map = {
                "Critical": 4,
                "High": 3,
                "Medium": 2,
                "Low": 1,
            }

            df_dependabot["Severity Numeric"] = df_dependabot["Severity"].map(severity_map)

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

            # Pie chart showing the number of alerts by severity

            # Pivot data to become severity | count
            df_dependabot_grouped_severity = df_dependabot[["Repository", "Severity"]].groupby("Severity").count()
            df_dependabot_grouped_severity.columns = ["Count"]

            fig = px.pie(
                df_dependabot_grouped_severity.reset_index(),
                values="Count",
                names="Severity",
                title="Total Alerts by Severity",
            )

            st.plotly_chart(fig)

            # Group information by repository
            df_dependabot_grouped_repository = df_dependabot[["Repository", "Type", "URL", "Severity"]].groupby(["Repository", "Type", "URL"]).count()
            df_dependabot_grouped_repository.columns = ["Total Alerts"]

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

                    col1, col2 = st.columns([0.8, 0.2])

                    col1.subheader(
                        f":blue-background[{selected_repo['Repository']} ({selected_repo['Type'].title()})]"
                    )
                    col2.write(f"[Go to Repository]({selected_repo['URL']})")

                    col1, col2, col3 = st.columns(3)

                    df_selected_dependabot = df_dependabot.loc[df_dependabot["Repository"] == selected_repo["Repository"]]

                    oldest_alert = (datetime.now() - df_dependabot.loc[df_dependabot["Repository"] == selected_repo["Repository"], "Creation Date"].min()).days
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

                    df_alerts_pie = df_selected_dependabot[["Severity", "Creation Date"]].groupby("Severity").count()
                    df_alerts_pie.columns = ["Total Alerts"]

                    fig = px.pie(
                        df_alerts_pie.reset_index(),
                        values="Total Alerts",
                        names="Severity",
                        title=f"Total Alerts by Severity for {selected_repo['Repository']}",
                    )

                    st.plotly_chart(fig)
                    
            else:
                st.caption("Select a repository for more information.")