# Configuration

## Overview

The Data Logger makes use of a `config.json` file to control various aspects of its operation. This file gets deployed within the container image, requiring redeployment should any run parameters need to be changed.

## Configuration for Local Development

To test the Data Logger locally, the following `features` should be set accordingly:

```json
{
    "features": {
        "repository_collection": true,
        "dependabot_collection": true,
        "secret_scanning_collection": true,
        "show_log_locally": true,
        "write_to_s3": false // This MUST be false or else the live data will be overwritten
    },
    "settings": {
        ... // Other settings as required
    }
}
```

The different collection features can be toggled on or off to control which data is collected. If only making changes to a single collection type, you can set the others to `false` to speed up the local testing process.

## Configuration Options

### Features

The features section allows developers to toggle various aspects of the Data Logger's operation to their needs.

```json
{
    "features": {
        "repository_collection": true,
        "dependabot_collection": true,
        "secret_scanning_collection": true,
        "show_log_locally": true,
        "write_to_s3": true
    },
    "settings": {
        ... // Other settings as required
    }
}
```

#### Repository, Dependabot, and Secret Scanning Collection

These features control whether the Data Logger collects data for the respective types. If set to `true`, the Data Logger will collect data for that key, otherwise it will skip the collection process for that type.

When deploying to AWS, all of these features should be set to `true` to ensure that the Data Logger collects all necessary data for the dashboard.

Setting these features to `false` can help speed up local testing and debugging, as it reduces the amount of data being collected and processed.

#### Show Log Locally

This feature controls whether the Data Logger outputs logs to a local text file. When set to `true`, the Data Logger will write logs to a file in the local directory, which can be useful for debugging and testing purposes, otherwise it will not write logs locally. This can help developers see the output of the Data Logger as if looking at the CloudWatch logs in AWS.

#### Write to S3

This feature controls whether the Data Logger writes the collected data to AWS S3. When set to `true`, the Data Logger will write the collected data to the specified S3 bucket in JSON format. If set to `false`, the Data Logger will instead write the data to a local file for developers to inspect. This is particularly useful for debugging and testing purposes, as it allows developers to see the data that would be written to S3 without actually modifying the live data.

When developing locally, this **must** be set to `false` to prevent overwriting the live data in S3. If for some reason you need to write to S3 while developing locally (i.e. to test the data with the dashboard), you should ensure that other team members are aware and that the data is not critical, as it will overwrite the existing data in S3.

### Settings

The settings section contains various parameters that control the behaviour of the Data Logger, including when checks are considered to be breaches of policy. It is highly unlikely that these settings will need to be changed - unless ONS' GitHub Usage Policy changes - but they are included here for completeness.

```json
{
    "features": {
        ... // Feature settings as above
    },
    "settings": {
        "thread_count": 20,
        "dependabot_thresholds": {
            "critical": 5,
            "high": 15,
            "medium": 60,
            "low": 90
        },
        "secret_scanning_threshold": 5,
        "inactivity_threshold": 1,
        "signed_commit_number": 15
    }
}
```

#### Thread Count

This setting controls the number of threads used by the Data Logger when collecting data from the GitHub API. Increasing this number can speed up data collection, especially for large organisations with many repositories. However, it also increases the load on the GitHub API, so it should be set to a reasonable value to avoid hitting rate limits.

For more information on how threading is used in the Data Logger, see the [Threading](./threading.md) page.

#### Dependabot Thresholds

These thresholds control how many days an alert must be open before it is considered to be a breach of policy. The thresholds are set for each severity level of Dependabot alerts and are derived from ONS' GitHub Usage Policy.

#### Secret Scanning Threshold

This threshold controls how many days a secret scanning alert must be open before it is considered to be a breach of policy. This is derived from ONS' GitHub Usage Policy.

#### Inactivity Threshold

This threshold controls how many years a repository can go without updates before it is considered inactive. This is derived from ONS' GitHub Usage Policy.

#### Signed Commit Number

This setting controls how many commits are checked when applying the signed commit policy check. This value has been agreed between stakeholders. 
