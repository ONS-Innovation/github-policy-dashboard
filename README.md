# GitHub Audit Dashboard
A dashboard which uses organisation data from the GitHub API to monitor how well policy is adhered to in ONS.

## Prerequisites
This project uses poetry for package management and colima/docker for containerisation.

[Instructions to install Poetry](https://python-poetry.org/docs/)
[Instructions to install Colima](https://github.com/abiosoft/colima/blob/main/README.md)

## Setup - Run outside of Docker

Prior to running outside of Docker ensure you have the necessary environment variables setup locally where you are running the application. E.g in linux or OSX you can run the following, providing appropriate values for the variables:

```bash
export AWS_ACCOUNT_NAME=sdp-sandbox
```

1. Navigate into the project's folder and create a virtual environment using `python3 -m venv venv`
2. Activate the virtual environment using `source venv/bin/activate`
3. Install all project dependancies using `poetry install`
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