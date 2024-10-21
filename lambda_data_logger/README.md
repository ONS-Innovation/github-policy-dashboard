# GitHub Audit Dashboard Lambda Function
A script designed to run in AWS Lambda to gather data for the GitHub Audit Dashboard.

This script gets:
- Repositories which have broken policy rules
- Open Secret Scanning alerts
- Dependabot Alerts

This script is designed to run daily and should be scheduled using AWS Event Bridge.

## Prerequisites
This section requires colima/docker for containerisation.

[Instructions to install Colima](https://github.com/abiosoft/colima/blob/main/README.md)

## GitHub API
### GitHub App
A .pem file is used to allow the project to make authorised Github API requests through the means of Github App authentication.
The project uses authentication as a Github App installation ([documentation](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation)).

In order to get a .pem file, a Github App must be created an installed into the organisation of which the app will be interacting with.
This app should have the following permissions:

- Repository Permissions
    - Pull Requests (Read)
    - Contents (Read)
    - Secret Scanning (Read)
    - Dependabot (Read)

- Organisation Permissions
    - Members (Read)

Once created and installed, you need to generate a Private Key for that Github App. This will download a .pem file to your pc.
This file needs to be uploaded to AWS ([documentation](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps)).

If you do not have access to organisation settings, you need to request a .pem file for the app.

### AWS
The Lambda Script requires access to an associated Github App secret, this secret is created when the Github App is installed in the appropriate Github Organisation. The contents of the generated pem file is stored in the AWS Secret Manager and retrieved by this service to interact with Github securely.

AWS Secret Manager must be set up with a secret:

/sdp/tools/repoarchive/repo-archive-github.pem
A plaintext secret, containing the contents of the .pem file created when a Github App was installed.

## Setup - Running in a container
1. Build a Docker Image

```
docker build -t github-audit-dashboard-lambda .
```

2. Check the image exists

```
docker images
```

Example Output:

```
REPOSITORY                                                                 TAG         IMAGE ID       CREATED         SIZE
github-audit-dashboard-lambda                                              latest      285d22eb6678   9 seconds ago   553MB
```

3. Run the image locally mapping local host port (9000) to container port (8080) and passing in AWS credentials to download a .pem file from the AWS Secrets Manager to the running container. These credentials will also be used to upload files to S3.

When running the container, environment variables for the GitHub Organisation, GitHub App Client ID, AWS Secret Location for the .pem file and AWS Account Name will need to be passed in also.

The credentials used in the below command are for a user in AWS that has permissions to retrieve secrets from AWS Secrets Manager and upload files to AWS S3.

```
docker run --platform linux/amd64 -p 9000:8080 \
-e AWS_ACCESS_KEY_ID=<aws_access_key_id> \
-e AWS_SECRET_ACCESS_KEY=<aws_secret_access_key_id> \
-e AWS_DEFAULT_REGION=eu-west-2 \
-e AWS_SECRET_NAME=<aws_secret_name> \
-e GITHUB_ORG=ONS-Innovation \
-e GITHUB_APP_CLIENT_ID=<github_app_client_id> \
-e AWS_ACCOUNT_NAME=sdp-sandbox \
-e AWS_LAMBDA_FUNCTION_TIMEOUT=600
github-audit-dashboard-lambda
```

**Please Note:** `AWS_LAMBDA_FUNCTION_TIMEOUT` is required to extend the timeout value for the function. The default is 300 seconds which isn't long enough for ONS-Innovation or ONSDigital. If you encounter a timeout error, increase this value.

Once the container is running, a local endpoint is created at `localhost:9000/2015-03-31/functions/function/invocations`.

4. Post to the endpoint to trigger the function

```
curl "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{}'
```

5. Once testing is finished, stop the running container

To check the container is running

```
docker ps
```

Example output

```
CONTAINER ID   IMAGE                           COMMAND                  CREATED         STATUS         PORTS                                       NAMES
1aee9747c318   github-audit-dashboard-lambda   "/lambda-entrypoint.…"   6 minutes ago   Up 6 minutes   0.0.0.0:9000->8080/tcp, :::9000->8080/tcp   nice_robinson
```

Stop the container

```
docker stop 1aee9747c318
```

## Storing the container on AWS Elastic Container Registry (ECR)

When you make changes to the Lambda Script, a new container image must be pushed to ECR.

These instructions assume:

1. You have a repository set up in your AWS account named github-audit-dashboard-lambda.
2. You have created an AWS IAM user with permissions to read/write to ECR (e.g AmazonEC2ContainerRegistryFullAccess policy) and that you have created the necessary access keys for this user.  The credentials for this user are stored in ~/.aws/credentials and can be used by accessing --profile <aws-credentials-profile\>, if these are the only credentials in your file then the profile name is _default_

You can find the AWS repo push commands under your repository in ECR by selecting the "View Push Commands" button.  This will display a guide to the following (replace <aws-credentials-profile\>, <aws-account-id\> and <version\> accordingly):

1. Get an authentication token and authenticate your docker client for pushing images to ECR:

    ```bash
    aws ecr --profile <aws-credentials-profile> get-login-password --region eu-west-2 | docker login --username AWS --password-stdin <aws-account-id>.dkr.ecr.eu-west-2.amazonaws.com
    ```

2. Tag your latest built docker image for ECR (assumes you have run _docker build -t github-audit-dashboard-lambda ._ locally first)

    ```bash
    docker tag github-audit-dashboard-lambda:latest <aws-account-id>.dkr.ecr.eu-west-2.amazonaws.com/github-audit-dashboard-lambda:<version>
    ```

    **Note:** To find the <version\> to build look at the latest tagged version in ECR and increment appropriately

3. Push the version up to ECR

    ```bash
    docker push <aws-account-id>.dkr.ecr.eu-west-2.amazonaws.com/github-audit-dashboard-lambda:<version>
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
- terraform-user
  - Used for terraform staging of the resources required to deploy the service

The following groups and permissions must be defined and applied to the above users:

- ecr-user-group
  - EC2 Container Registry Access
- terraform-user-group
  - Dynamo DB Access
  - EC2 Access
  - ECS Access
  - ECS Task Execution Role Policy
  - Route53 Access
  - S3 Access
  - Cloudwatch Logs All Access (Custom Policy)
  - IAM Access
  - Secrets Manager Access

**The Lambda Script Terraform requires some additional permissions to those above:**

- AmazonEC2ContainerRegistryFullAccess
- AmazonEventBridgeFullAccess
- AWSLambda_FullAccess

Further to the above an IAM Role must be defined to allow ECS tasks to be executed:

- ecsTaskExecutionRole
  - See the [AWS guide to create the task execution role policy](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html)

#### Bootstrap for Terraform

To store the state and implement a state locking mechanism for the service resources a Terraform backend is deployed in AWS (an S3 object and DynamoDbTable).

#### Running the Terraform

There are associated README files in each of the Terraform modules in this repository.  

- terraform/dashboard/main.tf
  - This provisions the resources required to launch the Policy Dashboard iteself.
- terraform/data_logger/main.tf
  - This provisions the resources required to launch the Policy Dashboard's data collection Lambda script (data logger).

Depending upon which environment you are deploying to you will want to run your terraform by pointing at an appropriate environment tfvars file.  

Example service tfvars file:
[/env/sandbox/example_tfvars.txt](../terraform/dashboard/env/sandbox/example_tfvars.txt)

### Updating the running service using Terraform (data_logger)

If the application has been modified then the following can be performed to update the running service:

- Build a new version of the container image and upload to ECR as per the instructions earlier in this guide.
- Change directory to the **terraform/data_logger**

  ```bash
  cd terraform/data_logger
  ```

- In the appropriate environment variable file env/sandbox/sandbox.tfvars, env/dev/dev.tfvars or env/prod/prod.tfvars
  - Fill out the appropriate variables

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

- When the terraform has applied successfully the Lambda and EventBridge Schedule will be created.

### Destroy the Main Service Resources

Delete the service resources by running the following ensuring your reference the correct environment files for the backend-config and var files:

  ```bash
  cd terraform/data_logger

  terraform init -backend-config=env/dev/backend-dev.tfbackend -reconfigure

  terraform refresh -var-file=env/dev/dev.tfvars

  terraform destroy -var-file=env/dev/dev.tfvars
  ```