import api_interface
import policy_checks

org = "ONS-Innovation"

with open("./github-audit-dashboard.pem", "r") as f:
    pem = f.read()

token = api_interface.get_access_token(org, pem, "Iv23lifHcR6yRDTxa7nk")

gh = api_interface.api_controller(token[0])

response = gh.get("/repos/ONS-Innovation/code-github-audit-dashboard", {})
repo = response.json()

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

print(len(policy_checks.get_all_dependabot_alerts(gh, org)))