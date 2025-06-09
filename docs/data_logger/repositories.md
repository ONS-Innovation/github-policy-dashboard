#  Repositories

## Overview

This dataset contains information about repositories within the organisation. It's primary purpose is to monitor repository compliance with the GitHub Usage Policy. This dataset does *not* contain any archived repositories as these are not active and considered out of scope.

## Structure

```json
[
    {
        "name": "{repo}",
        "type": "PUBLIC | PRIVATE | INTERNAL",
        "url": "https://github.com/{org}/{repo}",
        "created_at": "2023-12-04T14:33:57Z",
        "checklist": {
            "inactive": true | false,
            "unprotected_branches": true | false,
            "unsigned_commits": true | false,
            "readme_missing": true | false,
            "license_missing": true | false,
            "pirr_missing": true | false,
            "gitignore_missing": true | false,
            "external_pr": true | false,
            "breaks_naming_convention": true | false,
            "secret_scanning_disabled": true | false,
            "push_protection_disabled": true | false,
            "dependabot_disabled": true | false,
            "codeowners_missing": true | false,
            "point_of_contact_missing": true | false
        }
    },
]
```
