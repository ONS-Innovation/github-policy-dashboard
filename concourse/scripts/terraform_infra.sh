set -euo pipefail

aws_account_id=$(echo "$secrets" | jq -r .aws_account_id)
aws_access_key_id=$(echo "$secrets" | jq -r .aws_access_key_id)

aws_secret_access_key=$(echo "$secrets" | jq -r .aws_secret_access_key)
domain=$(echo "$secrets" | jq -r .domain)

github_app_client_id=$(echo "$secrets" | jq -r .github_app_client_id)
aws_secret_name=$(echo "$secrets" | jq -r .aws_secret_name)

github_org=$(echo "$secrets" | jq -r .github_org)
container_image=$(echo "$secrets" | jq -r .container_image)

service_subdomain=$(echo "$secrets" | jq -r .service_subdomain)
force_deployment=$(echo "$secrets" | jq -r .force_deployment)

container_port=$(echo "$secrets" | jq -r .container_port)
from_port=$(echo "$secrets" | jq -r .from_port)

lambda_name=$(echo "$secrets" | jq -r .lambda_name)
lambda_arch=$(echo "$secrets" | jq -r .lambda_arch)
lambda_timeout=$(echo "$secrets" | jq -r .lambda_timeout)
lambda_memory=$(echo "$secrets" | jq -r .lambda_memory)
schedule=$(echo "$secrets" | jq -r .schedule)

export AWS_ACCESS_KEY_ID=$aws_access_key_id
export AWS_SECRET_ACCESS_KEY=$aws_secret_access_key

git config --global url."https://x-access-token:$github_access_token@github.com/".insteadOf "https://github.com/"

if [[ ${env} != "prod" ]]; then
    env="dev"
fi

echo ${env}



if [[ ${repo_name} == "github-policy-dashboard" ]]; then

cd resource-repo/terraform/dashboard

terraform init -backend-config=env/${env}/backend-${env}.tfbackend -reconfigure

terraform apply \
-var "aws_account_id=$aws_account_id" \
-var "aws_access_key_id=$aws_access_key_id" \
-var "aws_secret_access_key=$aws_secret_access_key" \
-var "domain=$domain" \
-var "container_ver=${tag}" \
-var "github_app_client_id=$github_app_client_id" \
-var "aws_secret_name=$aws_secret_name" \
-var "github_org=$github_org" \
-var "container_image=$container_image" \
-var "service_subdomain=$service_subdomain" \
-var "force_deployment=$force_deployment" \
-var "container_port=$container_port" \
-var "from_port=$from_port" \
-auto-approve

    
else 

cd resource-repo/terraform/data_logger

terraform init -backend-config=env/${env}/backend-${env}.tfbackend -reconfigure

terraform apply \
-var "aws_account_id=$aws_account_id" \
-var "aws_access_key_id=$aws_access_key_id" \
-var "aws_secret_access_key=$aws_secret_access_key" \
-var "env_name=$domain" \
-var "aws_secret_name=$aws_secret_name" \
-var "github_org=$github_org" \
-var "github_app_client_id=$github_app_client_id" \
-var "lambda_name=$lambda_name" \
-var "lambda_arch=$lambda_arch" \
-var "lambda_timeout=$lambda_timeout" \
-var "lambda_memory=$lambda_memory" \
-var "lambda_version=${tag}" \
-var "schedule=$schedule" \
-auto-approve


fi
