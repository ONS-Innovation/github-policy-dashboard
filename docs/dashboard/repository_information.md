# Repository Data Collection

## Overview

Dependabot and Secret Scanning alerts are collected from their respective GitHub API Endpoints.

- **Secret Scanning**: [`GET /orgs/{org}/secret-scanning/alerts`](https://docs.github.com/en/rest/secret-scanning/secret-scanning?apiVersion=2022-11-28#list-secret-scanning-alerts-for-an-organization)
- **Dependabot**: [`GET /orgs/{org}/dependabot/alerts`](https://docs.github.com/en/rest/dependabot/alerts?apiVersion=2022-11-28#list-dependabot-alerts-for-an-organization)

These endpoints list all alerts for the organization. The endpoint contains the name of the repository they belong to, but, unfortunately, does not contain the repository's visibility (public/private/internal) or if the repository is archived or not.

This information is important to allow users to filter alerts appropriately, for example, any public Secret Scanning alerts are much more of a risk than private ones. We want users to be able to highlight these sorts of issues.

We must, therefore, collect the repository information from the GitHub API separately to allow us to provide this functionality.

## How is the data collected?

The additional repository information is collected by the dashboard at runtime. Although this is not ideal due to performance, it must be collected in the frontend due to the already stretched rate limits of the GitHub API in the Data Logger.

In order to make this process as efficient and performant as possible, the function changes how it collects the data based on which alerts the data is being collected for.

The function is available within `./src/utilities` as `get_github_repository_information()`. See below for the function's docstring.

---

::: src.utilities.get_github_repository_information

---

The function works by collecting the repository information of either all repositories in the organisation or only those that have been passed to the function within `repository_list`. The option is provided because in some cases, it requires less API calls to collect all repositories in the organisation, rather than just those that have alerts.

For Secret Scanning alerts, there are likely to be less than 30 repositories with alerts, so it is more efficient to collect only those repositories. For Dependabot alerts, there are likely to be more than 30 repositories with alerts, so it is more efficient to collect all repositories in the organisation.

It works out cheaper on the API to collect all repositories in the organisation because we can collect up to 100 repositories per API call. At the time of writing, the organisation has around 3000 repositories, meaning 30 API calls to collect all repositories. If there are more than 30 repositories to collect, we may as well collect all repositories in the organisation, as it will only require 30 API calls.

The endpoints used to collect the repository information are:

- **List Repositories for an Organisation**: [`GET /orgs/{org}/repos`](https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#list-organization-repositories)
- **Get a Repository**: [`GET /repos/{owner}/{repo}`](https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#get-a-repository)

## How is the data used?

Once we have the repository information, we can map it to a new column within the DataFrame containing the respective alerts - providing the extra data we need.
