# Policy Data Logger

An AWS Lambda script to scrape policy information from the GitHub API.

## Table of Contents

- [Policy Data Logger](#policy-data-logger)
  - [Table of Contents](#table-of-contents)

## Prerequisites

- A Docker Daemon (Colima is recommended)
  - [Colima](https://github.com/abiosoft/colima)
- Terraform (For deployment)
  - [Terraform](https://www.terraform.io/)
- Python >3.12
  - [Python](https://www.python.org/)
- Make
  - [GNU make](https://www.gnu.org/software/make/manual/make.html#Overview)

## Makefile

This repository makes use of a Makefile to execute common commands. To view all commands, execute `make all`.

```bash
make all
```

## `config.json`

The lambda function contains a configuration file ([`config.json`](./config/config.json)). This file is used to setup key values within the script.

`config.json` is divided into 2 high level keys: features and settings.

The features key is used to enable or disable specific features within the tool (for example if you didn't want to collect dependabot information).

The settings key is used to store key values used to collect and process data. This includes values such as how many threads to collect data with and how many years a repository must go without updates before it is considered inactive.

The table below describes each configuration parameter and its use.

### Features

| Parameter | Description | Default |
| --------- | ----------- | ------- |
| `repository_collection` | Whether to collect repository data or not. | true |
| `dependabot_collection` | Whether to collect dependabot data or not. | true |
| `secret_scanning_collection` | Whether to collection secret scanning data or not. | true |
| `show_log_locally` | This is for development purposes. This controls whether the log is stored locally as `debug.log`. This allows developers to see logging outputs when running the tool locally | true |
| `write_to_s3` | Whether the tool should write its outputs to S3 or store them locally. Local storage is useful when testing / developing the tool locally. Local outputs are kept within `./output/`. When deploying to AWS, this key should **always** be `true`. | true |

### Settings

| Parameter | Description | Default |
| --------- | ----------- | ------- |
| `thread_count` | The number of threads to collect and process data with. | 20 |
| `dependabot_thresholds` | This contains information about how many days a dependabot alert for a given severity is open before being considered a policy breach. | critical (5), high (15), medium (60), low (90) |
| `secret_scanning_threshold` | The number of days a secret scanning alert must be open for before being considered a policy breach. | 5 days |
| `inactivity_threshold` | The number of years a project goes without updates before being considered inactive. | 1 year |
| `signed_commit_number` | The number of repository commits to check within the signed commit check (for example, when set to 15, only the 15 most recent commits). | 15 |

## Development

To work on this project, you need to:

1. Navigate into `./data_logger`

    ```bash
    cd /data_logger
    ```

2. Create a virtual environment and activate it.

    Create:

    ```python
    python3 -m venv venv
    ```

    Activate:

    ```python
    source venv/bin/activate
    ```

3. Install dependencies

    ```bash
    poetry install
    ```

To run the project during development, we recommend you [run the project outside of a container](#outside-of-a-container-development-only)

## Running the Project

### Containerised (Recommended)

To run the project, a Docker Daemon is required to containerise and execute the project. We recommend using [Colima](https://github.com/abiosoft/colima).

Before the doing the following, make sure your Daemon is running. If using Colima, run `colima start` to check this.

1. Containerise the project.

    ```bash
    docker build -t policy-dashboard-lambda .
    ```

2. Check the image exists (Optional).

    ```bash
    docker images
    ```

    Example Output:

    ```bash
    REPOSITORY                                                                              TAG           IMAGE ID       CREATED         SIZE
    policy-dashboard-lambda                                                                 latest        f05e43330fae   6 seconds ago   709MB
    ```

3. Run the image.

    ```bash
    docker run --platform linux/amd64 -p 9000:8080 \
    -e AWS_ACCESS_KEY_ID=<access_key_id> \
    -e AWS_SECRET_ACCESS_KEY=<secret_access_key> \
    -e AWS_DEFAULT_REGION=<region> \
    -e AWS_SECRET_NAME=<secret_name> \
    -e GITHUB_ORG=<org> \
    -e GITHUB_APP_CLIENT_ID=<client_id> \
    -e AWS_ACCOUNT_NAME=<aws_account_name> \
    -e AWS_LAMBDA_FUNCTION_TIMEOUT=900
    policy-dashboard-lambda
    ```

    When running the container, you are required to pass some environment variable.

    | Variable                    | Description                                                                                     |
    |-----------------------------|-------------------------------------------------------------------------------------------------|
    | GITHUB_ORG                  | The organisation you would like to run the tool in.                                             |
    | GITHUB_APP_CLIENT_ID        | The Client ID for the GitHub App which the tool uses to authenticate with the GitHub API.       |
    | AWS_DEFAULT_REGION          | The AWS Region which the Secret Manager Secret is in.                                           |
    | AWS_SECRET_NAME             | The name of the AWS Secret Manager Secret to get.                                               |
    | AWS_ACCOUNT_NAME            | The name of the AWS Account (i.e. sdp-dev). This is used for bucket naming when writing to S3.  |
    | AWS_LAMBDA_FUNCTION_TIMEOUT | The timeout time in seconds. This should be set to 900s (Default: 300s / 5 minutes).            |

    Once the container is running, a local endpoint is created at `localhost:9000/2015-03-31/functions/function/invocations`.

4. Check the container is running (Optional).

    ```bash
    docker ps
    ```

    Example Output:

    ```bash
    CONTAINER ID   IMAGE                     COMMAND                  CREATED         STATUS         PORTS                                       NAMES
    5bb738f3e695   policy-dashboard-lambda   "/lambda-entrypoint.…"   9 seconds ago   Up 8 seconds   0.0.0.0:9000->8080/tcp, :::9000->8080/tcp   nice_bhabha
    ```

5. Post to the endpoint (`localhost:9000/2015-03-31/functions/function/invocations`).

    ```bash
    curl "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{}'
    ```

    This will run the Lambda function and, once complete, will return a success message.

6. After testing stop the container.

    ```bash
    docker stop <container_id>
    ```

### Outside of a Container (Development only)

To run the Lambda function outside of a container, we need to execute the `handler()` function.

1. Uncomment the following at the bottom of `main.py`.

    ```python
    ...
    # if __name__ == "__main__":
    #     handler(None, None)
    ...
    ```

    **Please Note:** If uncommenting the above in `main.py`, make sure you re-comment the code *before* pushing back to GitHub.

2. Export the required environment variables:

    ```bash
    export AWS_ACCESS_KEY_ID=<access_key_id>
    export AWS_SECRET_ACCESS_KEY=<secret_access_key>
    export AWS_DEFAULT_REGION=eu-west-2
    export AWS_SECRET_NAME=<secret_name>
    export GITHUB_ORG=<org>
    export GITHUB_APP_CLIENT_ID=<client_id>
    export AWS_ACCOUNT_NAME=<aws_account_name>
    ```

    An explanation of each variable is available within the [containerised instructions](#containerised-recommended).

3. Run the script.

    ```bash
    python3 src/main.py
    ```

## Deployment

### Overview

This repository is designed to be hosted on AWS Lambda using a container image as the Lambda's definition.

There are 2 parts to deployment:

1. Updating the ECR Image.
2. Updating the Lambda.

### Deployment Prerequisites

Before following the instructions below, we assume that:

- An ECR repository exists on AWS that aligns with the Lambda's naming convention, `{env_name}-{lambda_name}` (these can be set within the `.tfvars` file. See [example_tfvars.txt](../terraform/data_logger/env/sandbox/example_tfvars.txt)).
- The AWS account contains underlying infrastructure to deploy on top of. This infrastructure is defined within [sdp-infrastructure](https://github.com/ONS-Innovation/sdp-infrastructure) on GitHub.
- An AWS IAM user has been setup with appropriate permissions.

Additionally, we recommend that you keep the container versioning in sync with GitHub releases. Internal documentation for this is available on Confluence ([GitHub Releases and AWS ECR Versions](https://confluence.ons.gov.uk/display/KEH/GitHub+Releases+and+AWS+ECR+Versions)). We follow Semantic Versioning ([Learn More](https://semver.org/spec/v2.0.0.html)).

### Storing the Container on AWS Elastic Container Registry (ECR)

When changes are made to the repository's source code, the code must be containerised and pushed to AWS for the lambda to use.

The following instructions deploy to an ECR repository called `sdp-dev-policy-dashboard-lambda`. Please change this to `<env_name>-<lambda_name>` based on your AWS instance.

All of the commands (steps 2-5) are available for your environment within the AWS GUI. Navigate to ECR > {repository_name} > View push commands.

1. Export AWS credential into the environment. This makes it easier to ensure you are using the correct credentials.

    ```bash
    export AWS_ACCESS_KEY_ID="<aws_access_key_id>"
    export AWS_SECRET_ACCESS_KEY="<aws_secret_access_key>"
    ```

2. Login to AWS.

    ```bash
    aws ecr get-login-password --region eu-west-2 | docker login --username AWS --password-stdin <aws_account_id>.dkr.ecr.eu-west-2.amazonaws.com
    ```

3. Ensure `config.json` is set correctly.

    When running the data logger within AWS, it is essential that `write_to_s3` is set to `true`.

    If this is not set correctly, the lambda function will run *without* storing its output.

    For more information, see [`config.json`](#configjson).

4. Ensuring you're at the root of the repository, build a docker image of the project.

    ```bash
    docker build -t sdp-dev-policy-dashboard-lambda .
    ```

    **Please Note:** Change `sdp-dev-policy-dashboard-lambda` within the above command to `<env_name>-<lambda_name>`.

5. Tag the docker image to push to AWS, using the correct versioning mentioned in [prerequisites](#deployment-prerequisites).

    ```bash
    docker tag sdp-dev-policy-dashboard-lambda:latest <aws_account_id>.dkr.ecr.eu-west-2.amazonaws.com/sdp-dev-policy-dashboard-lambda:<semantic_version>
    ```

    **Please Note:** Change `sdp-dev-policy-dashboard-lambda` within the above command to `<env_name>-<lambda_name>`.

6. Push the image to ECR.

    ```bash
    docker push <aws_account_id>.dkr.ecr.eu-west-2.amazonaws.com/sdp-dev-policy-dashboard-lambda:<semantic_version>
    ```

Once pushed, you should be able to see your new image version within the ECR repository.

### Deploying the Lambda

#### Configuration

##### `lambda_memory`

Within your `.tfvars` for the respective environment, you can define the amount of memory assigned to the lambda function. The amount of memory given to a lambda also affects how much CPU resource is assigned to it. For more information on this see:

- [Configure Lambda function memory](https://docs.aws.amazon.com/lambda/latest/dg/configuration-memory.html)
- [Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)

Within our environments, this value will need to vary.

- For **sdp-dev**, `lambda_memory` should be set to 128. This is to reduce cost and, because of the decreased volume of information, reduces wasted resource.
- For **sdp-prod**, `lambda_memory` should be set to 1024. This is because of the larger volume of data needing to be processed within the lambda's runtime (15 minutes).

#### Instructions

Once AWS ECR has the new container image, we need to update the Lambda's configuration to use it. To do this, use the repository's provided [Terraform](./terraform/).

Within the terraform directory, there is a [service](../terraform/data_logger/) subdirectory which contains the terraform to setup the lambda on AWS.

1. Change directory to the service terraform.

    ```bash
    cd terraform/data_logger
    ```

2. Fill out the appropriate environment variables file
    - `env/dev/dev.tfvars` for sdp-dev.
    - `env/prod/prod.tfvars` for sdp-prod.

    These files can be created based on [`example_tfvars.txt`](../terraform/data_logger/env/sandbox/example_tfvars.txt).

    **It is crucial that the completed `.tfvars` file does not get committed to GitHub.**

    Ensure that you have read the [configuration guide](#configuration) **before** deployment.

3. Initialise the terraform using the appropriate `.tfbackend` file for the environment (`env/dev/backend-dev.tfbackend` or `env/prod/backend-prod.tfbackend`).

    ```bash
    terraform init -backend-config=env/dev/backend-dev.tfbackend -reconfigure
    ```

    **Please Note:** This step requires an AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY to be loaded into the environment if not already in place. This can be done using:

    ```bash
    export AWS_ACCESS_KEY_ID="<aws_access_key_id>"
    export AWS_SECRET_ACCESS_KEY="<aws_secret_access_key>"
    ```

4. Refresh the local state to ensure it is in sync with the backend, using the appropriate `.tfvars` file for the environment (`env/dev/dev.tfvars` or `env/prod/prod.tfvars`).

    ```bash
    terraform refresh -var-file=env/dev/dev.tfvars
    ```

5. Plan the changes, using the appropriate `.tfvars` file.

    i.e. for dev use

    ```bash
    terraform plan -var-file=env/dev/dev.tfvars
    ```

6. Apply the changes, using the appropriate `.tfvars` file.

    i.e. for dev use

    ```bash
    terraform apply -var-file=env/dev/dev.tfvars
    ```

Once applied successfully, the Lambda and EventBridge Schedule will be created.

### Destroying / Removing the Lambda

To delete the service resources, run the following:

```bash
cd terraform/service
terraform init -backend-config=env/dev/backend-dev.tfbackend -reconfigure
terraform refresh -var-file=env/dev/dev.tfvars
terraform destroy -var-file=env/dev/dev.tfvars
```

**Please Note:** Make sure to use the correct `.tfbackend` and `.tfvars` files for your environment.
