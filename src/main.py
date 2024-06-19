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

# print(f"is inactive: {checklist["inactive"]}")
# print(f"are branches unprotected: {checklist["branch_unprotected"]}")
# print(f"are any of the last 15 commits unsigned: {checklist["unsigned_commits"]}")
# print(f"is README.md missing: {checklist["readme_exists"]}")
# print(f"is LICENSE.md missing: {checklist["license_exists"]}")
# print(f"is PIRR.md missing: {checklist["pirr_exists"]}")
# print(f"is .gitignore missing {checklist["gitignore_exists"]}")
# print(f"has external pull request: {checklist["external_pr"]}")
# print(f"does repository break naming convention: {checklist["break_naming"]}")

# print(f"{checks_failed} of {total_checks} checks failed \n")

print(policy_checks.get_secret_scanning_alerts(gh, org))