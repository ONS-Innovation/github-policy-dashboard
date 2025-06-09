#  Dependabot

## Overview

This dataset contains information about the Dependabot alerts within the organisation. The dataset does *not* contain any sensitive information such as the content of the alerts, only that there is an alert and the repository it is associated with. Dependabot alerts must be past a threshold to be included in this dataset. The thresholds for each alert severity are defined in the Data Logger's configuration file (See [Configuration](./configuration.md) for more).

This dataset includes all open alerts within the thresholds, regardless of whether the repository is archived or not. You can filter alerts by this in the frontend. Information about whether an alert's associated repository is archived and its visibility is collected in the frontend rather than here (See [Repository Data Collection](../dashboard/repository_information.md) for more).

## Structure

```json
[
    {
        "repository": "{repo}",
        "repository_url": "https://github.com/{org}/{repo}",
        "created_at": "2024-12-11T23:54:00Z",
        "severity": "critical | high | medium | low",
    },
]
```
