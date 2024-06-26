import api_interface
import policy_checks

org = "ONS-Innovation"

with open("./github-audit-dashboard.pem", "r") as f:
    pem = f.read()

token = api_interface.get_access_token(org, pem, "Iv23lifHcR6yRDTxa7nk")

gh = api_interface.api_controller(token[0])


def get_repository_data(gh: api_interface.api_controller, org: str) -> list[dict] | str:
    repo_list = []

    repos_response = gh.get(f"/orgs/{org}/repos", {"per_page": 100})

    if repos_response.status_code == 200:
        try:
            last_page = int(repos_response.links["last"]["url"].split("=")[-1])
        except KeyError:
            # If Key Error, Last doesn't exist therefore 1 page
            last_page = 1

        for i in range(0, last_page):
            repos_response = gh.get(f"/orgs/{org}/repos", {"per_page": 100, "page": i+1})

            if repos_response.status_code == 200:
                repos = repos_response.json()

                for repo in repos:
                    repo_info = {
                        "name": repo["name"],
                        "type": repo["visibility"],
                        "url": repo["html_url"],
                        "checklist": {
                            "inactive": policy_checks.check_inactive(repo),
                            "branch_unprotected": policy_checks.check_branch_protection(repo["branches_url"].replace("{/branch}", ""), gh),
                            "unsigned_commits": policy_checks.check_signed_commits(repo["commits_url"].replace("{/sha}", ""), gh),
                            "readme_exists": policy_checks.check_file_exists(repo["contents_url"], gh, ["README.md", "readme.md"]),
                            "license_exists": policy_checks.check_file_exists(repo["contents_url"], gh, ["LICENSE.md", "LICENSE"]),
                            "pirr_exists": policy_checks.check_file_exists(repo["contents_url"], gh, ["PIRR.md"]),
                            "gitignore_exists": policy_checks.check_file_exists(repo["contents_url"], gh, [".gitignore"]),
                            "external_pr": policy_checks.check_external_pr(repo["pulls_url"].replace("{/number}", ""), repo["full_name"], gh),
                            "break_naming": policy_checks.check_breaks_naming(repo["name"])
                        }
                    }

                    # If repo type is public, then PIRR check does not apply, so set to False
                    # If repo type is private/internal, then License check does not apply, so set to False
                    if repo_info["type"] == "public":
                        repo_info["checklist"]["pirr_exists"] = False
                    else:
                        repo_info["checklist"]["license_exists"] = False

                    repo_list.append(repo_info)

            else:
                return f"Error {repos_response.status_code}: {repos_response.json()["message"]}"

        return repo_list
    else:
        return f"Error {repos_response.status_code}: {repos_response.json()["message"]}"
    

# This currently takes 77~ seconds to run for 34 repositories.
# This is roughly 2.26 seconds per repository.
# So to run for ONSDigital which has 2.1k repositories, it would take 79 minutes.
# This process needs to run somewhere else like AWS Lambda

print(len(get_repository_data(gh, org)))

# response = gh.get("/repos/ONS-Innovation/code-github-audit-dashboard", {})
# repo = response.json()

# print(f"Repo Name: {repo["name"]}")
# print(f"Repo Type: {repo["visibility"]}")

# checklist = {
#     "inactive": policy_checks.check_inactive(repo),
#     "branch_unprotected": policy_checks.check_branch_protection(repo["branches_url"].replace("{/branch}", ""), gh),
#     "unsigned_commits": policy_checks.check_signed_commits(repo["commits_url"].replace("{/sha}", ""), gh),
#     "readme_exists": policy_checks.check_file_exists(repo["contents_url"], gh, ["README.md", "readme.md"]),
#     "license_exists": policy_checks.check_file_exists(repo["contents_url"], gh, ["LICENSE.md", "LICENSE"]),
#     "pirr_exists": policy_checks.check_file_exists(repo["contents_url"], gh, ["PIRR.md"]),
#     "gitignore_exists": policy_checks.check_file_exists(repo["contents_url"], gh, [".gitignore"]),
#     "external_pr": policy_checks.check_external_pr(repo["pulls_url"].replace("{/number}", ""), repo["full_name"], gh),
#     "break_naming": policy_checks.check_breaks_naming(repo["name"])
# }  

# checks_failed = sum(checklist.values())
# total_checks = len(checklist)

# print(policy_checks.get_secret_scanning_alerts(gh, org, 5))

# print(len(policy_checks.get_dependabot_alerts_by_severity(gh, org, "critical", 0)))
# print(len(policy_checks.get_dependabot_alerts_by_severity(gh, org, "high", 0)))
# print(len(policy_checks.get_dependabot_alerts_by_severity(gh, org, "medium", 0)))
# print(len(policy_checks.get_dependabot_alerts_by_severity(gh, org, "low", 0)))

# print(len(policy_checks.get_all_dependabot_alerts(gh, org)))