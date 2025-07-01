set -euo pipefail

export STORAGE_DRIVER=vfs
export PODMAN_SYSTEMD_UNIT=concourse-task

aws ecr get-login-password --region eu-west-2 | podman --storage-driver=vfs login --username AWS --password-stdin ${aws_account_id}.dkr.ecr.eu-west-2.amazonaws.com

if [[ ${repo_name} == "github-policy-dashboard"]]; then
    echi "TEST 1"
    container_image=$(echo "$secrets" | jq -r .container_image)
    podman build -t ${container_image}:${tag} resource-repo

else 
    echo "TEST 2"
    container_image=$(echo "$secrets" | jq -r .container_image_lambda)
    podman build -t ${container_image}:${tag} resource-repo/data_logger/
fi

podman tag ${container_image}:${tag} ${aws_account_id}.dkr.ecr.eu-west-2.amazonaws.com/${container_image}:${tag}

podman push ${aws_account_id}.dkr.ecr.eu-west-2.amazonaws.com/${container_image}:${tag}
