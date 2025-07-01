if [[ "${repo_name}" == "github-policy-dashboard" || ${repo_name} == "github-policy-lambda" ]]; then
    echo "${repo_name}"
else
    echo "Unknown repository name: ${repo_name}"
    exit 1
fi