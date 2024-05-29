# Github Audit Dashboard Requirements

The dashboard's main purpose is to identify repositories/users which violate ONS' [Github Usage Policy](https://officenationalstatistics.sharepoint.com/sites/ONS_DDaT_Communities/Software%20Engineering%20Policies/Forms/AllItems.aspx?id=%2Fsites%2FONS%5FDDaT%5FCommunities%2FSoftware%20Engineering%20Policies%2FSoftware%20Engineering%20Policies%2FApproved%2FPDF%2FGitHub%20Usage%20Policy%2Epdf&parent=%2Fsites%2FONS%5FDDaT%5FCommunities%2FSoftware%20Engineering%20Policies%2FSoftware%20Engineering%20Policies%2FApproved%2FPDF).
The dashboard should be able to identify repositories **created after** a given date.
The dashboard will then be used for manual action and you should be able to mark repositories/users as exempt for breaking a given policy (i.e if a repository is flagged for not having a .gitignore but it will never need one).

## Policy Tasks

| Policy Clause | Description | Already Available? | Implementation Needed? | Potential Limitations |
|:---------------|:-------------|:--------------------|:------------------------:|:--------------------|
| 2.1 | Check that organisational email address is attached to member profiles | N/A | Yes | Github API can only get user emails if they're provided in their public profile - most of the time this field is empty |
| 2.2 | Check that user profiles are filled out with information | N/A | No | N/A |
| 3. | Check that all users who are members of the org should be there | N/A | Yes | Will need another reference point to compare against Github |
| 4.1 | All repos should be made in ONSdigital | N/A | No | N/A |
| 4.2 | Check that repo names follow conventions (i.e hyphens/underscores, all lower case, etc.) | N/A | Yes | None |
| 4.3 | Check private/internal repos for a PIRR.md file. Should not be empty. | N/A | Yes | None |
| 4.4 | All repos should have a README.md | N/A | Yes | None |
| 4.5 | Check public repos for a license file. Should not be empty. | N/A | Yes | None |
| 4.6 | All repos should have a .gitignore | N/A | Yes | None |
| 4.7 | All repos should have good quality documentation | N/A | No | Might be something for SDP - Could check if /docs is present |
| 4.8 | Any repository with no updates for 1 year and is no longer used should be archived | N/A | Yes | None |
| 5.1 | Check Team/Organisation naming | N/A | No | None |
| 5.2 | Team Structure | N/A | No | None |
| 5.3 | Code of Conduct | N/A | No | None |
| 5.4 | Use PRs | N/A | No | None |
| 5.5 | Check for PR's outside of organisation | N/A | Yes | None |
| 5.6 | Branch Usage | N/A | No | None |
| 5.7 | Check Branch Protection Rules (Main Branch Only) are enforced | N/A | Yes | None |
| 5.8 | Check that commits are signed | N/A | Yes | None |
| 6.1 | Personal privacy settings | N/A | No | None |
| 6.2 | Check that dependabot and secret scanning, etc are enabled | Yes (organisation insights tab) | No | None |
| 6.2.1~4 | Check for any dependabot and security scanning alerts | No | Yes | None |
| 6.3 | Compliance | N/A | No | None |

All other policy clauses are not relevant to the project and require **no** implementation.

## Task Summary

- Highlight any users which do not have an ONS email added to their account
- Check that all org members should be there (Will require another reference)
- Highlight any repositories which break naming conventions (contains uppercase, special characters, etc.)
- Highlight any repos without:
    - README.md
    - License file (public only)
    - PIRR.md (private/internal only)
    - .gitignore
- Highlight any repos which haven't been updated for more than a year
- Highlight any repos with external pull requests
- Highlight any repos without branch protection rules on main branch
- Highlight any repos without signed commits
- Highlight any repos with Security Scanning/Dependabot alerts (When to highlight specified in policy 6.2.1 & 6.2.2)

Repositories to be highlighted should be filtered by creation date.
Any highlighted users/repos should be able to be marked as exempt for that alert.

## Tech Stack
This dashboard will probably be made using Python and Steamlit.