# Data Logger

##  Overview

The Data Logger is a Python script that collects data from the GitHub API and stores it in an S3 Bucket as JSON. It is designed to be run periodically, currently weekly, to ensure that the data is up-to-date. Since the scope of the dashboard is only to be used for snapshots and regular audits, the update frequency is not critical.

## Data Collection Process

The Data Logger interacts with the GitHub API to gather data for a specific organinsation. Once collected from the API, the data is stored within an S3 bucket in JSON format. Whether the data is stored into S3 or not is controlled within the `config.json` file, allowing the tool to be debugged locally. For more information on the configuration, see the [Configuration](./configuration.md) page.

Once the data has been written to S3, the Dashboard can access it freely.

### Diagram of Data Flow

The below diagram shows the collection process for a single type of data, such as `repositories.json`. For a more detailed view of each data type, see the respective pages:

- **`repositories.json`**: [Data Collection > Repositories](./repositories.md)
- **`secret_scanning.json`**: [Data Collection > Secret Scanning](./secret_scanning.md)
- **`dependabot.json`**: [Data Collection > Dependabot](./dependabot.md)

``` mermaid
graph TD
    A{Is the collection<br> for this type<br> enabled?}
    A -->|Yes| B[Collect Data from<br> the GitHub API]
    B -->|API Response| C[Get Response Data<br> as a Dictionary]
    C -->|Dictionary| D[Write to S3 Bucket<br> as JSON]
    D -->|Data Available for Dashboard| E[Dashboard];
    A -->|No| F[Skip Collection]
```

### Collection Frequency

The Data Logger is currently set to run weekly. This frequency is sufficient for the dashboard's purpose of providing snapshots and regular audits. The frequency can be adjusted using Terraform.

The Lambda is triggered by a CloudWatch Event Rule (EventBridge Trigger) which follows a cron expression. This cron expression gets passed within the `.tfvars` file during the deployment of the Data Logger. Simply change the cron expression to adjust the frequency of the data collection.

When adjusting the frequency, consider the following:

- **API Rate Limits**: The Data Logger must run at a time where no other tools are using the GitHub API to avoid hitting rate limits (providing they share the same GitHub App).
- **Cost**: Only run the Data Logger as frequently as necessary to keep costs down. Once a week is typically sufficient for most use cases.
- **Data Freshness**: Ensure that the data remains relevant and up-to-date for the dashboard's needs. Weekly updates are generally adequate for snapshot and audit purposes.
- **Outside of Working Hours**: If the Data Logger is run during working hours, the data being collected may change while the Data Logger is running. This can lead to inconsistencies in the data collected - especially with `repositories.json` - where multiple repositories within the organisation get updated per second.

## Hardware / Deployment Requirements

The Data Logger is designed to run as an AWS Lambda function. This means that the process must be completed in less than 15 minutes, which is the maximum execution time for a Lambda function. A few performance considerations have been considered to ensure that the Data Logger runs efficiently within this time limit:

- **Threading**: The Data Logger uses Python's threading capabilities to run multiple API calls in parallel. This allows for faster data collection, especially when dealing with large organisations with many repositories. More on the use of threading can be found in the [Threading](./threading.md) page.
- **Allocated Memory**: Depending on the size of the organisation, the Lambda function may require more memory to run efficiently. AWS Lambda scales the CPU power allocated to the function based on the amount of memory allocated. Therefore, increasing the memory allocation can lead to faster execution times.
    - If working with ONSdigital, more memory is required than if working with ONS-Innovation. This is due to the larger volume of data being collected from the ONSdigital organisation. The current recommended memory allocation for each environment is noted in the README file for the Data Logger.
- **Timeout Settings**: The Lambda function is set to a timeout of 15 minutes, which is the maximum allowed. This ensures that the Data Logger has enough time to complete its tasks without being prematurely terminated.
