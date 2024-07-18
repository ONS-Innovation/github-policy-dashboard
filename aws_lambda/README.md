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

The credentials used in the below command are for a user in AWS that has permissions to retrieve secrets from AWS Secrets Manager and upload files to AWS S3.

```
docker run --platform linux/amd64 -p 9000:8080 \
-e AWS_ACCESS_KEY_ID=<aws_access_key_id> \
-e AWS_SECRET_ACCESS_KEY=<aws_secret_access_key_id> \
-e AWS_DEFAULT_REGION=eu-west-2 \
github-audit-dashboard-lambda
```

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

1. You have a repository set up in your AWS account named copilot-usage-lambda-script.
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

## AWS Lambda Setup

Once the container is pushed to ECR, we can run it as a Lambda function.

1. Create a Lambda Function, selecting the Container Image option.
2. Once the option is selected, we then need to name the function and select the ECR image which we want the Lambda function to use.
3. Once created, we then need to add some extra permissions to the IAM role which Lambda created for the function.

    1. Navigate to Configuration > Permissions
    2. Click on the **Role Name** to be redirected to IAM.
    3. Once redirected to IAM > Role > <role_name>, we need to add 2 permissions. Click on Add permissions > Create inline policy.
    4. Here we can select which permissions we want to give for which services. For this script, we need to have the following permissions:
        
        Secret Manager
        - GetSecretValue

        S3 
        - GetObject
        - PutObject

    5. Once these have been added, our Lambda function now has all the necessary permissions to execute the container on ECR.

4. Now that the Lambda function has the correct permissions, we can test it.

5. Once a Lambda function has been created, we can schedule it to run periodically using Amazon [EventBridge](https://aws.amazon.com/eventbridge/). The function should be run daily.