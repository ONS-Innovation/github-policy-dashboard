"""The Repositories Analysis Page for the GitHub Policy Dashboard."""

import streamlit as st
import boto3
import datetime
import pandas as pd
import plotly.express as px

import utilities as utils
import repositories.collection as collection
import repositories.formatting as fmt

env = utils.get_environment_variables()

session = boto3.Session()
s3 = session.client("s3")
secret_manager = session.client("secretsmanager", region_name=env["secret_region"])


last_modified = utils.get_last_modified(
    s3=s3,
    bucket=env["bucket_name"],
    filename="repositories.json"
)

df_repositories = collection.load_repositories(
    _s3=s3,
    bucket=env["bucket_name"],
)

rules, df_repositories = fmt.get_rules_from_repositories(
    df_repositories=df_repositories,
)

rulemap = collection.load_rulemap()


if last_modified is None:
    st.error("Last modified date not found. Please ensure the repositories.json file is present in the S3 bucket.")
    st.stop()

if df_repositories is None:
    st.error("Repository data not found. Please ensure the repositories.json file is present in the S3 bucket.")
    st.stop()

if not rules:
    st.error("No rules found in the repository data. Please ensure the repositories.json file contains valid data.")
    st.stop()

if not rulemap:
    st.error("Rule map not found. Please ensure the rulemap.json file is present in the project root.")
    st.stop()


st.logo("./src/branding/ONS_Logo_Digital_Colour_Landscape_Bilingual_RGB.svg")

col1, col2 = st.columns([0.6, 0.4], vertical_alignment="bottom")

with col1:
    st.title(":blue-background[GitHub Policy Dashboard]")
with col2:
    st.html(f"<p style='text-align: right; font-size: x-large;'><b>Last Updated:</b> {last_modified}</p>")
    
st.header(":blue-background[Repository Analysis 📦]")

st.write("Rule Presets:")

col1, col2, col3 = st.columns(3)

with col1:
    st.button(
        "All Rules",
        on_click=lambda: st.session_state.update({"selected_rules": rules}),
        use_container_width=True,
    )

with col2:
    st.button(
        "Policy Rules",
        on_click=lambda: st.session_state.update({"selected_rules": [rule['name'] for rule in rulemap if rule['is_policy_rule']]}),
        use_container_width=True,
    )

with col3:
    st.button(
        "Security Rules",
        on_click=lambda: st.session_state.update({"selected_rules": [rule['name'] for rule in rulemap if rule['is_security_rule']]}),
        use_container_width=True,
    )

with st.form("Repository Filters"):
    st.subheader(":blue-background[Repository Filters]")

    st.caption(
        "Use the filters below to select the repositories you want to analyse. "
        "You can filter by repository type, creation date, and the rules you want to check."
    )

    selected_rules = st.multiselect("Select Rules", rules, default=st.session_state.get("selected_rules", rules), key="repo_rule_select")

    repository_type = st.selectbox(
        "Select Repository Type",
        ["All"] + sorted(df_repositories["repository_type"].unique().tolist()),
        key="repo_repository_type_select"
    )

    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input("Start Date", pd.to_datetime(df_repositories["created_at"].min()), key="start_date_repo")
    with col2:
        end_date = st.date_input("End Date", (datetime.datetime.now() + datetime.timedelta(days=1)).date(), key="end_date_repo")

    st.caption(
        "**Please Note:** The above date range is used to filter the creation date of repositories."
    )

    st.form_submit_button("Apply Filters", use_container_width=True)

if end_date < start_date:
    st.error("End date cannot be before start date.")
    st.stop()

if len(selected_rules) == 0:
    st.error("Please select at least one rule to display.")
    st.stop()

rules_to_exclude = []

for rule in rules:
    if rule not in selected_rules:
        rules_to_exclude.append(rule)

df_repositories = fmt.filter_repositories(
    df_repositories=df_repositories,
    start_date=start_date,
    end_date=end_date,
    repository_type=repository_type,
    rules_to_exclude=rules_to_exclude,
)

df_repositories = fmt.add_repository_calculations(
    df_repositories=df_repositories,
    selected_rules=selected_rules,
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
else:
    st.write("No notes for the selected rules.")
    
st.divider()

col1, col2 = st.columns(2)

# Create a dataframe summarising the compliance of the repositories
df_compliance = fmt.get_compliance_summary(
    df_repositories=df_repositories,
)

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
        ql = utils.get_ql_interface(
            _secret_manager=secret_manager,
            secret_name=env["secret_name"],
            org=env["org"],
            client_id=env["client_id"]
        )

        points_of_contact_main = ql.get_repository_email_list(env["org"], selected_repo["Repository"], "main")
        points_of_contact_master = ql.get_repository_email_list(env["org"], selected_repo["Repository"], "master")

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

            if env["org"] == "ONS-Innovation":
                st.write("Points of contact are not available for ONS Innovation repositories.")

else:
    st.caption("Select a repository for more information.")
