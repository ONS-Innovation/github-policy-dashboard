# GitHub Policy Dashboard

A dashboard which uses organisation data from the GitHub API to monitor how well policy is adhered to in ONS.

## Overview

This repository contains 2 main elements:

- A Streamlit Dashboard to visualise policy data from S3.
- An AWS Lambda Data Logger to collect information from GitHub to be used by the dashboard ([README](./data_logger/README.md)).

## Table of Contents

- [GitHub Policy Dashboard](#github-policy-dashboard)
  - [Overview](#overview)
  - [Table of Contents](#table-of-contents)
  - [Prerequisites](#prerequisites)
  - [Documentation](#documentation)
  - [Setup - Run outside of Docker](#setup---run-outside-of-docker)
  - [Setup - Running in a container](#setup---running-in-a-container)
  - [Storing the container on AWS Elastic Container Registry (ECR)](#storing-the-container-on-aws-elastic-container-registry-ecr)
  - [Deployment to AWS](#deployment-to-aws)
    - [Deployment Prerequisites](#deployment-prerequisites)
      - [Underlying AWS Infrastructure](#underlying-aws-infrastructure)
      - [Bootstrap IAM User Groups, Users and an ECSTaskExecutionRole](#bootstrap-iam-user-groups-users-and-an-ecstaskexecutionrole)
      - [Bootstrap for Terraform](#bootstrap-for-terraform)
      - [Running the Terraform](#running-the-terraform)
      - [Provision Users](#provision-users)
    - [Updating the running service using Terraform](#updating-the-running-service-using-terraform)
  - [Linting and Formatting](#linting-and-formatting)
    - [Markdown Linting](#markdown-linting)
      - [Usage](#usage)
      - [`.markdownlint.json` Configuration](#markdownlintjson-configuration)
      - [Markdownlint GitHub Action](#markdownlint-github-action)
  - [Future Development](#future-development)

## Prerequisites

This project uses poetry for package management and colima/docker for containerisation.

[Instructions to install Poetry](https://python-poetry.org/docs/)
[Instructions to install Colima](https://github.com/abiosoft/colima/blob/main/README.md)

## Documentation

This project uses MkDocs for documentation which gets deployed to GitHub Pages at a repository level.

For more information about MkDocs, see the below documentation.

[Getting Started with MkDocs](https://www.mkdocs.org/getting-started/)

There is a guide to getting started on this repository's GitHub Pages site.

## Setup - Run outside of Docker

Prior to running outside of Docker ensure you have the necessary environment variables setup locally where you are running the application. E.g in linux or OSX you can run the following, providing appropriate values for the variables:

```bash
export AWS_ACCESS_KEY_ID=<aws_access_key_id> 
export AWS_SECRET_ACCESS_KEY=<aws_secret_access_key_id> 
export AWS_DEFAULT_REGION=eu-west-2 
export AWS_SECRET_NAME=<aws_secret_name> 
export GITHUB_ORG=ONS-Innovation 
export GITHUB_APP_CLIENT_ID=<github_app_client_id>
export AWS_ACCOUNT_NAME=sdp-dev
```

1. Navigate into the project's folder and create a virtual environment using `python3 -m venv venv`
2. Activate the virtual environment using `source venv/bin/activate`
3. Install all project dependancies using `make install`
4. Run the project using `streamlit run src/app.py`

## Setup - Running in a container

1. Build a Docker Image

    ```bash
    docker build -t github-policy-dashboard .
    ```

2. Check the image exists

    ```bash
    docker images
    ```

    Example Output:

    ```bash
    REPOSITORY                                                                 TAG         IMAGE ID       CREATED          SIZE
    github-policy-dashboard                                                    latest      9a9cb9286a7f   51 seconds ago   906MB
    ```

3. Run the image locally mapping local port 8501 to container port 8501 and passing in AWS credentials to access a `.pem` file from AWS Secrets Manager while running container.
These credentials should also allow access to S3.

    ```bash
    docker run -p 8501:8501 \
    -e AWS_ACCESS_KEY_ID=<aws_access_key_id> \
    -e AWS_SECRET_ACCESS_KEY=<aws_secret_access_key_id> \
    -e AWS_DEFAULT_REGION=eu-west-2 \
    -e AWS_SECRET_NAME=<aws_secret_name> \
    -e GITHUB_ORG=ONS-Innovation \
    -e GITHUB_APP_CLIENT_ID=<github_app_client_id> \
    -e AWS_ACCOUNT_NAME=sdp-dev 
    github-policy-dashboard
    ```

4. Check the container is running

    ```bash
    docker ps
    ```

    Example Output:

    ```bash
    CONTAINER ID   IMAGE                    COMMAND                  CREATED         STATUS         PORTS                                       NAMES
    92e40251aa4c   github-policy-dashboard  "poetry run streamli…"   2 minutes ago   Up 2 minutes   0.0.0.0:8501->8501/tcp, :::8501->8501/tcp   strange_bhaskara
    ```

5. To view the running in a browser app navigate to

    ```bash
    You can now view your Streamlit app in your browser.

    URL: http://0.0.0.0:8501
    ```

6. To stop the container, use the container ID

    ```bash
    docker stop 92e40251aa4c
    ```

## Storing the container on AWS Elastic Container Registry (ECR)

When you make changes to the dashboard, a new container image must be pushed to ECR.

These instructions assume:

1. You have a repository set up in your AWS account named `github-audit-dashboard`.
2. You have created an AWS IAM user with permissions to read/write to ECR (e.g `AmazonEC2ContainerRegistryFullAccess` policy) and that you have created the necessary access keys for this user.  The credentials for this user are stored in `~/.aws/credentials` and can be used by accessing `--profile <aws-credentials-profile\>`, if these are the only credentials in your file then the profile name is _default_

You can find the AWS repo push commands under your repository in ECR by selecting the "View Push Commands" button.  This will display a guide to the following (replace <aws-credentials-profile\>, <aws-account-id\> and <version\> accordingly):

1. Get an authentication token and authenticate your docker client for pushing images to ECR:

    ```bash
    aws ecr --profile <aws-credentials-profile> get-login-password --region eu-west-2 | docker login --username AWS --password-stdin <aws-account-id>.dkr.ecr.eu-west-2.amazonaws.com
    ```

2. Tag your latest built docker image for ECR (assumes you have run `docker build -t github-audit-dashboard .` locally first)

    ```bash
    docker tag github-audit-dashboard:latest <aws-account-id>.dkr.ecr.eu-west-2.amazonaws.com/github-audit-dashboard:<version>
    ```

    **Note:** To find the <version\> to build look at the latest tagged version in ECR and increment appropriately

3. Push the version up to ECR

    ```bash
    docker push <aws-account-id>.dkr.ecr.eu-west-2.amazonaws.com/github-audit-dashboard:<version>
    ```

## Deployment to AWS

The deployment of the service is defined in Infrastructure as Code (IaC) using Terraform.  The service is deployed as a container on an AWS Fargate Service Cluster.

### Deployment Prerequisites

When first deploying the service to AWS the following prerequisites are expected to be in place or added.

#### Underlying AWS Infrastructure

The Terraform in this repository expects that underlying AWS infrastructure is present in AWS to deploy on top of, i.e:

- Route53 DNS Records
- Web Application Firewall and appropriate Rules and Rule Groups
- Virtual Private Cloud with Private and Public Subnets
- Security Groups
- Application Load Balancer
- ECS Service Cluster

That infrastructure is defined in the repository [sdp-infrastructure](https://github.com/ONS-Innovation/sdp-infrastructure)

#### Bootstrap IAM User Groups, Users and an ECSTaskExecutionRole

The following users must be provisioned in AWS IAM:

- `ecr-user`
  - Used for interaction with the Elastic Container Registry from AWS cli
- `ecs-app-user`
  - Used for Terraform staging of the resources required to deploy the service

The following groups and permissions must be defined and applied to the above users:

- `ecr-user-group`
  - EC2 Container Registry Access
- `ecs-application-user-group`
  - Dynamo DB Access
  - EC2 Access
  - ECS Access
  - ECS Task Execution Role Policy
  - Route53 Access
  - S3 Access
  - Cloudwatch Logs All Access (Custom Policy)
  - IAM Access
  - Secrets Manager Access

Further to the above an IAM Role must be defined to allow ECS tasks to be executed:

- `ecsTaskExecutionRole`
  - See the [AWS guide to create the task execution role policy](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html)

#### Bootstrap for Terraform

To store the state and implement a state locking mechanism for the service resources, a Terraform backend is deployed in AWS (an S3 object and DynamoDbTable).

#### Running the Terraform

There are associated README files in each of the Terraform modules in this repository.  

- `terraform/dashboard/main.tf`
  - This provisions the resources required to launch the service.
- `terraform/data_logger/main.tf`
  - This provisions the resources required to launch the Policy Dashboard's data collection Lambda script (data logger).
- `terraform/authentication/main.tf`
  - This provisions the Cognito authentication used by the service.

Depending upon which environment you are deploying to, you will want to run your Terraform by pointing at an appropriate environment `tfvars` file.  

Example dashboard tfvars file:
[dashboard/env/dev/example_tfvars.txt](./terraform/dashboard/env/dev/example_tfvars.txt)

Example data_logger tfvars file:
[data_logger/env/dev/example_tfvars.txt](./terraform/data_logger/env/dev/example_tfvars.txt)

Example authentication tfvars file:
[authentication/env/dev/example_tfvars.txt](./terraform/authentication/env/dev/example_tfvars.txt)

#### Provision Users

When the service is first deployed, an admin user must be created in the Cognito User Pool that was created when the authentication Terraform was applied.

New users are manually provisioned in the AWS Console:

- Navigate to Cognito->User Pools and select the pool created for the service
- Under the Users section select _Create User_ and choose the following:
  - _Send an email invitation_
  - Enter the _ONS email address_ for the user to be added
  - Select _Mark email address as verified_
  - Under _Temporary password_ choose:
    - Generate a password
  - Select _Create User_

An email invite will be sent to the selected email address along with a one-time password which is valid for 10 days.

### Updating the running service using Terraform

Terraform is used to update the running service.

The process is provided within the team's documentation repository: [keh-central-documentation/terraform/COMMANDS.md](https://github.com/ONS-Innovation/keh-central-documentation/blob/main/terraform/COMMANDS.md)

This covers how to:

- Update any of the running services using Terraform
- Destroy the running service using Terraform

## Linting and Formatting

To view all commands

```bash
make all
```

Linting tools must first be installed before they can be used

```bash
make install-dev
```

To clean residue files

```bash
make clean
```

To format your code

```bash
make format
```

To run all linting tools

```bash
make lint
```

To run a specific linter (black, ruff, pylint)

```bash
make black
make ruff
make pylint
```

To run mypy (static type checking)

```bash
make mypy
```

### Deployments with Concourse

#### Allowlisting your IP

To setup the deployment pipeline with concourse, you must first allowlist your IP address on the Concourse server. IP addresses are flushed everyday at 00:00 so this must be done at the beginning of every working day whenever the deployment pipeline needs to be used. 

Follow the instructions on the Confluence page (SDP Homepage > SDP Concourse > Concourse Login) to login. 

All our pipelines run on `sdp-pipeline-prod`, whereas `sdp-pipeline-dev` is the account used for changes to Concourse instance itself. Make sure to export all necessary environment variables from `sdp-pipeline-prod` (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN).

#### Setting up a pipeline

When setting up our pipelines, we use `ecs-infra-user` on `sdp-dev` to be able to interact with our infrastructure on AWS. The credentials for this are stored on
AWS Secrets Manager so you do not need to set up anything yourself. Since this repository has two services that need to be deployed, you can set up a separate
pipeline for each by either specifying the pipeline name as `github-policy-dashboard` or `github-policy-lambda`.

To set the pipeline, run the following script:

```bash
chmod u+x ./concourse/scripts/set_pipeline.sh
./concourse/scripts/set_pipeline.sh github-policy-dashboard # for policy dashboard
./concourse/scripts/set_pipeline.sh github-policy-lambda # for policy lambda

```

Note that you only have to run chmod the first time running the script in order to give permissions.
This script will set the branch and pipeline name to whatever branch you are currently on. It will also set the image tag on ECR to the current commit hash at the time of setting the pipeline.

The pipeline name itself will usually follow a pattern as follows: `<repo-name>-<branch-name>`
If you wish to set a pipeline for another branch without checking out, you can run the following:

```bash
./concourse/scripts/set_pipeline.sh github-policy-dashboard <branch_name> # For policy dashboard
./concourse/scripts/set_pipeline.sh github-policy-lambda <branch_name> # For policy lambda
```

If the branch you are deploying is `main`, it will trigger a deployment to the `sdp-prod` environment. To set the ECR image tag, you must draft a GitHub release pointing to the latest release of the `main` branch that has a tag in the form of `vX.Y.Z`. Drafting up a release will automatically deploy the latest version of the `main` branch with the associated release tag, but you can also manually trigger a build through the Concourse UI or the terminal prompt.

#### Triggering a pipeline

Once the pipeline has been set, you can manually trigger a build on the Concourse UI, or run the following command:

```bash
fly -t aws-sdp trigger-job -j github-policy-dashboard-<branch-name>/build-and-push # For policy dashboard
fly -t aws-sdp trigger-job -j github-policy-lambda-<branch-name>/build-and-push # For policy lambda
```

### Markdown Linting

To lint the markdown files in this repository, we use `markdownlint-cli`. This repository uses the Dockerised version of the linter, allowing it to be run without needing to install it locally.

The tool is available on GitHub at [markdownlint-cli](https://github.com/igorshubovych/markdownlint-cli)

#### Usage

To run the linter:

```bash
make md_lint
```

To automatically fix any issues found by the linter:

```bash
make md_fix
```

#### `.markdownlint.json` Configuration

The `.markdownlint.json` file in the root of the repository contains the configuration for markdownlint. This file is used to set the rules and settings for linting markdown files.

Currently, MD013 (line length) is disabled. This is because the default line length of 80 characters is too restrictive.

For a full list of rules, see [Markdownlint Rules / Aliases](https://github.com/DavidAnson/markdownlint?tab=readme-ov-file#rules--aliases)

#### Markdownlint GitHub Action

This repository uses GitHub Actions to run markdownlint on every push and pull request. The workflow file is located in the `.github/workflows` directory.

The workflow will run markdownlint on all markdown files in the repository. If any linting errors are found, the workflow will fail and provide a report of the errors.

## Future Development

- There are plans to migrate the dashboard to become part of the Digital Landscape. This would incur the Streamlit UI being removed from this repository and
  being rewritten in React.
- The data logger will remain in this repository but will undergo a rewrite to improve code quality and adhere to best practices - making use of linting tools
  and introducing robust testing coverage.
