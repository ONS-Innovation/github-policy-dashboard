# Threading

## Overview

The Data Logger uses a modified version of the `threading` library to perform operations in parallel, allowing it to collect data from the GitHub API quicker than if it were to run sequentially. This is a crucial aspect of the Data Logger's design, as without it, the Data Logger would take significantly longer than AWS Lambda's maximum execution time of 15 minutes.

Within this repository, the `threading` library has been tweaked so that threads can return the values of the operations they perform. Each thread has a `return_value` attribute that gets set to the output of the function it runs. Without this functionality, threads would not be able to return the data they collect, which is essential for the Data Logger to function correctly.

## How it works

In order to make good use of threading, the Data Logger gets given a defined number of threads to use when collecting data. This is set within the configuration file for the tool (see [Configuration](./configuration.md) for more details). The tool implements data parallelism to do the same tasks on many threads. The volume of data being assigned to each thread is determined differently depending on the type of data being collected.

### `repositories.json`

When collecting the repository data, each repository is ran through a series of checks, making use of multiple API endpoints. Each thread is assigned a batch of repositories to process, and each thread will return a list of dictionaries containing the data for each repository it processed. Once all processing is complete, the Data Logger will combine the results from all threads into a single list of dictionaries, which is then written to the `repositories.json` file.

This process uses the maximum number of threads specified in the configuration file. Before starting the threads, the Data Logger will collect the total number of repositories to process and divide them into batches based on the number of threads available. Each thread will then process its assigned batch of repositories concurrently.

Collecting repository data is the most time-consuming operation in the Data Logger, due to the number of API calls required for each repository. 

### `dependabot.json`

When collecting Dependabot data, the Data Logger will assign a single thread to each severity of Dependabot alert. This means that only 4 threads will be used for this operation, regardless of the number of threads specified in the configuration file. A thread will be created for each of the following severities: 

- Critical
- High
- Medium
- Low

Each thread will then collect the Dependabot alerts for its assigned severity and return a list of dictionaries containing the data for each alert. Once all threads have completed, the Data Logger will combine the results from all threads into a single list of dictionaries, which is then written to the `dependabot.json` file.

There is plenty of opportunity to improve the performance of this operation in the future, as it is currently limited to 4 threads. The performance of this operation is, for the time being, acceptable, as the time taken to collect Dependabot data is significantly less than the time taken to collect repository data.

A better approach to this operation would be to understand the proportion of each severity of Dependabot alert within the organisation and scale the number of threads used for each severity accordingly.
