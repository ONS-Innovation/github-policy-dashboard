# GitHub Audit Dashboard
A dashboard which uses organisation data from the GitHub API to monitor how well policy is adhered to in ONS.

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
export AWS_ACCOUNT_NAME=sdp-sandbox
```

1. Navigate into the project's folder and create a virtual environment using `python3 -m venv venv`
2. Activate the virtual environment using `source venv/bin/activate`
3. Install all project dependancies using `make install`
4. When running the project locally, you need to edit `get_s3_client()` within `app.py`.

When creating an instance of `boto3.Session()`, you must pass which AWS credential profile to use, as found in `~/.aws/credentials`.

When running locally:

```
session = boto3.Session(profile_name="<profile_name>")
s3 = session.client("s3")
```

When running from a container:

```
session = boto3.Session()
s3 = session.client("s3")
```

5. Run the project using `streamlit run src/app.py`

## Setup - Running in a container
1. Build a Docker Image

```
    docker build -t github-audit-dashboard .
```

2. Check the image exists

```
    docker images
```

Example Output:

```
REPOSITORY                                                                 TAG         IMAGE ID       CREATED          SIZE
github-audit-dashboard                                                     latest      9a9cb9286a7f   51 seconds ago   906MB
```

3. Run the image locally mapping local port 8501 to container port 8501 and passing in AWS credentials to access a .pem file from AWS Secrets Manager while running container.
These credentials should also allow access to S3.

```
docker run -p 8501:8501 \
-e AWS_ACCESS_KEY_ID=<aws_access_key_id> \
-e AWS_SECRET_ACCESS_KEY=<aws_secret_access_key_id> \
-e AWS_DEFAULT_REGION=eu-west-2 \
-e AWS_ACCOUNT_NAME=sdp-sandbox
github-audit-dashboard
```

4. Check the container is running

```
docker ps
```

Example Output:

```
CONTAINER ID   IMAGE                    COMMAND                  CREATED         STATUS         PORTS                                       NAMES
92e40251aa4c   github-audit-dashboard   "poetry run streamli…"   2 minutes ago   Up 2 minutes   0.0.0.0:8501->8501/tcp, :::8501->8501/tcp   strange_bhaskara
```

5. To view the running in a browser app navigate to

```
You can now view your Streamlit app in your browser.

URL: http://0.0.0.0:8501
```

6. To stop the container, use the container ID

```
docker stop 92e40251aa4c
```

## Storing the container on AWS Elastic Container Registry (ECR)

When you make changes to the dashboard, a new container image must be pushed to ECR.

These instructions assume:

1. You have a repository set up in your AWS account named github-audit-dashboard.
2. You have created an AWS IAM user with permissions to read/write to ECR (e.g AmazonEC2ContainerRegistryFullAccess policy) and that you have created the necessary access keys for this user.  The credentials for this user are stored in ~/.aws/credentials and can be used by accessing --profile <aws-credentials-profile\>, if these are the only credentials in your file then the profile name is _default_

You can find the AWS repo push commands under your repository in ECR by selecting the "View Push Commands" button.  This will display a guide to the following (replace <aws-credentials-profile\>, <aws-account-id\> and <version\> accordingly):

1. Get an authentication token and authenticate your docker client for pushing images to ECR:

    ```bash
    aws ecr --profile <aws-credentials-profile> get-login-password --region eu-west-2 | docker login --username AWS --password-stdin <aws-account-id>.dkr.ecr.eu-west-2.amazonaws.com
    ```

2. Tag your latest built docker image for ECR (assumes you have run _docker build -t github-audit-dashboard ._ locally first)

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

- ecr-user
  - Used for interaction with the Elastic Container Registry from AWS cli
- ecs-app-user
  - Used for terraform staging of the resources required to deploy the service

The following groups and permissions must be defined and applied to the above users:

- ecr-user-group
  - EC2 Container Registry Access
- ecs-application-user-group
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

- ecsTaskExecutionRole
  - See the [AWS guide to create the task execution role policy](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html)

#### Bootstrap for Terraform

To store the state and implement a state locking mechanism for the service resources a Terraform backend is deployed in AWS (an S3 object and DynamoDbTable).

#### Running the Terraform

There are associated README files in each of the Terraform modules in this repository.  

- terraform/service/main.tf
  - This provisions the resources required to launch the service.

Depending upon which environment you are deploying to you will want to run your terraform by pointing at an appropriate environment tfvars file.  

Example service tfvars file:
[service/env/sandbox/example_tfvars.txt](https://github.com/ONS-Innovation/github-policy-dashboard/terraform/service/env/sandbox/example_tfvars.txt)

### Updating the running service using Terraform

If the application has been modified then the following can be performed to update the running service:

- Build a new version of the container image and upload to ECR as per the instructions earlier in this guide.
- Change directory to the **service terraform**

  ```bash
  cd terraform/service
  ```

- In the appropriate environment variable file env/sandbox/sandbox.tfvars, env/dev/dev.tfvars or env/prod/prod.tfvars
  - Change the _container_ver_ variable to the new version of your container.
  - Change the _force_deployment_ variable to _true_.

- Initialise terraform for the appropriate environment config file _backend-dev.tfbackend_ or _backend-prod.tfbackend_ run:

  ```bash
  terraform init -backend-config=env/dev/backend-dev.tfbackend -reconfigure
  ```

  The reconfigure options ensures that the backend state is reconfigured to point to the appropriate S3 bucket.

  **_Please Note:_** This step requires an **AWS_ACCESS_KEY_ID** and **AWS_SECRET_ACCESS_KEY** to be loaded into the environment if not already in place.
  This can be done using:

  ```bash
  export AWS_ACCESS_KEY_ID="<aws_access_key_id>"
  export AWS_SECRET_ACCESS_KEY="<aws_secret_access_key>"
  ```

- Refresh the local state to ensure it is in sync with the backend

  ```bash
  terraform refresh -var-file=env/dev/dev.tfvars
  ```

- Plan the changes, ensuring you use the correct environment config (depending upon which env you are configuring):

  E.g. for the dev environment run

  ```bash
  terraform plan -var-file=env/dev/dev.tfvars
  ```

- Apply the changes, ensuring you use the correct environment config (depending upon which env you are configuring):

  E.g. for the dev environment run

  ```bash
  terraform apply -var-file=env/dev/dev.tfvars
  ```

- When the terraform has applied successfully the running task will have been replaced by a task running the container version you specified in the tfvars file

### Destroy the Main Service Resources

Delete the service resources by running the following ensuring your reference the correct environment files for the backend-config and var files:

  ```bash
  cd terraform/service

  terraform init -backend-config=env/dev/backend-dev.tfbackend -reconfigure

  terraform refresh -var-file=env/dev/dev.tfvars

  terraform destroy -var-file=env/dev/dev.tfvars
  ```

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