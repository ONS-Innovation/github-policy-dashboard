# Rule Mapping

##  Overview

In order to add more information about the rules applied to repositories, `rulemap.json` is used. This allows the tool to connect each check in `repositories.json` with additional information about the rule, such as a description and the preset it applies to.

## Where do the rules come from?

All rules on the dashboard are derived from ONS' GitHub Usage Policy. This is available on Sharepoint at [GitHub Usage Policy](https://officenationalstatistics.sharepoint.com/sites/ONS_DDaT_Communities/Software%20Engineering%20Policies/Forms/AllItems.aspx?id=%2Fsites%2FONS%5FDDaT%5FCommunities%2FSoftware%20Engineering%20Policies%2FSoftware%20Engineering%20Policies%2FApproved%2FPDF%2FGitHub%20Usage%20Policy%2Epdf&parent=%2Fsites%2FONS%5FDDaT%5FCommunities%2FSoftware%20Engineering%20Policies%2FSoftware%20Engineering%20Policies%2FApproved%2FPDF) (requires ONS network access).

##  Format

The `rulemap.json` file is a JSON object containing an array of rule objects. Each rule object has the following structure:

```json
[
    {
        "name": "String",
        "description": "String",
        "is_security_rule": bool,
        "is_policy_rule": bool,
        "note": "String"
    }
]
```

###  Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | String | The name of the rule. This should match the name used in `repositories.json`. |
| `description` | String | A detailed description of the rule, explaining what it checks and when it applies. |
| `is_security_rule` | bool | Indicates if the rule is a security rule. If true, the rule will be included in the Security Preset. |
| `is_policy_rule` | bool | Indicates if the rule is a policy rule. If true, the rule will be included in the Policy Preset. |
| `note` | String | Additional notes or comments about the rule. This is mainly used to explain what happens to repositories that the check doesn't run on (i.e. if a check is only for public repositories, this rule would explain that private/internal repositories automatically pass the check). |

###  Example

```json
[
    {
        "name": "codeowners_missing",
        "description": "The repository does not have a CODEOWNERS file.",
        "is_security_rule": false,
        "is_policy_rule": true,
        "note": ""
    },
    {
        "name": "point_of_contact_missing",
        "description": "A contact email address cannot be found from the CODEOWNERS file.",
        "is_security_rule": true,
        "is_policy_rule": true,
        "note": "This rule will only check if a point of contact email address can be found from the CODEOWNERS file. If the CODEOWNERS file is missing, this rule will not be triggered and be marked as compliant."
    }
]
```

More example can be found in the file itself, which is located in the root of the repository.

## Adding Rules

### Backend Changes

First you must create the new rule in the Data Logger. In `data_logger/src/main.py`, there is a function called `get_repository_batch()`. This function is where the final data structure of `repositories.json` is created. You can add your new rule to the `repository_data` dictionary in this function and put the logic in its own function (if possible in `policy_checks.py`).

Once this has been done, the new rule will be collected by the Data Logger and added to the `repositories.json` file when it runs.

### Frontend Changes

Once the backend changes have been made, you need to flesh out the rule in the `rulemap.json` file. You can do this by adding a new object to the array with the appropriate fields filled out. Make sure that the `name` field matches the name of the key used in `repositories.json`.

i.e.

In `repositories.json` you might have:

```python
repository_data = {
    "name": repository["name"],
    "type": repository["visibility"],
    "url": repository["url"],
    "created_at": repository["createdAt"],
    "checklist": {
        "example_check": do_check()
    }
}
```

Then in `rulemap.json`, you would add:

```json
{
    "name": "example_check", <!-- This MUST match the key in repositories.json -->
    "description": "This is an example check that does something.",
    "is_security_rule": false,
    "is_policy_rule": true,
    "note": ""
}
```

A new check should now appear in the Dashboard under the appropriate preset.

## Changing Rule Presets

To change which preset a rule belongs to, you can modify the `is_security_rule` and `is_policy_rule` fields in the `rulemap.json` file. If a rule is marked as a security rule, it will be included in the Security Preset. If it is marked as a policy rule, it will be included in the Policy Preset.
